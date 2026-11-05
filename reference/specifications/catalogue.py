"""Pure immutable snapshot binding and catalogue consistency checks."""
from .canonical import canonical_bytes, require
from . import schemas as s
from .predicates import validate_predicate
from .values import validate_value_definition, validate_conversion_units


def record_ref(record):
    c = record['content']
    return {'uuid': c['assertion_uuid'] if record['kind'] == 'specification_assertion' else c['meta']['revision_uuid'], 'content_hash': c['content_hash']}


def record_key(record):
    return record['kind'], record_ref(record)['uuid']


def resolve(reference, kind, records):
    record = records.get((kind, reference['uuid']))
    require(record is not None and record_ref(record) == reference, f'Missing/mismatched exact {kind} reference')
    return record


def no_cycles(graph):
    done, visiting = set(), set()
    for root in graph:
        stack = [(root, False)]
        while stack:
            key, leaving = stack.pop()
            if leaving:
                visiting.remove(key)
                done.add(key)
                continue
            require(key not in visiting, 'Dependency cycle')
            if key in done:
                continue
            visiting.add(key)
            stack.append((key, True))
            stack.extend((child, False) for child in graph.get(key, ()))


def validate_snapshot(catalogue, records, units, *, predecessor=None, feature_states=None):
    """Validate exact complete membership, not a persistence/latest-member lookup."""
    s.catalogue(catalogue)
    member_keys = {s.member_key(m) for m in catalogue['members']}
    require(member_keys == set(records), 'Snapshot membership differs from supplied records')
    require(sum(k[0] == 'compatibility_rule' for k in records) <= 1000, 'Catalogue exceeds 1000 rules')
    for m in catalogue['members']:
        resolve(m['revision'], m['kind'], records)
    for record in records.values():
        s.member(record)
    baseline = catalogue['target_uuid']
    offerings, graph = {}, {}
    for key, record in records.items():
        kind, c = record['kind'], record['content']
        require('target_uuid' not in c or c['target_uuid'] == baseline, 'Foreign baseline member')
        graph[key] = set()
        if kind in ('transmission_offering', 'equipment_offering'):
            require(key[1] not in offerings, 'Offering UUID reused across kinds')
            offerings[key[1]] = record.copy()
        if kind == 'definition':
            for rule in c['qualifier_rules']:
                if rule['categorical_definition'] is not None:
                    categorical = resolve(rule['categorical_definition'], 'definition', records)['content']
                    require(categorical['value_kind'] == 'category', 'Qualifier reference must be categorical definition')
                    graph[key].add(('definition', rule['categorical_definition']['uuid']))
        elif kind == 'specification_assertion':
            definition = resolve({'uuid': c['definition_revision_uuid'], 'content_hash': c['definition_revision_hash']}, 'definition', records)['content']
            graph[key].add(('definition', c['definition_revision_uuid']))
            require(c['review']['finding'] != 'established' or definition['meta']['finding'] == 'established', 'Established assertion uses unresolved definition')
            validate_value_definition(c['value'], definition, units)
            if c['normalization']['conversion'] is not None:
                validate_conversion_units(c['normalization']['conversion'], units)
            rules = {q['key']: q for q in definition['qualifier_rules']}
            provided = {q['key'] for q in c['qualifiers']}
            require(provided <= set(rules) and all(not q['required'] or q['key'] in provided for q in rules.values()), 'Qualifier definition mismatch')
            for q in c['qualifiers']:
                rule = rules[q['key']]
                categorical = resolve(rule['categorical_definition'], 'definition', records)['content'] if rule['categorical_definition'] is not None else None
                validate_value_definition(q['value'], categorical or {'value_kind': rule['value_kind'], 'dimensional_family': rule['dimensional_family'], 'categorical_terms': [], 'sequence_rule': None}, units)
            require((definition['component_rule'] != 'none') or c['component'] is None, 'Unexpected component')
        elif kind == 'transmission_offering':
            description = resolve(c['description'], 'transmission_description', records)['content']
            require(c['meta']['finding'] != 'established' or description['meta']['finding'] == 'established', 'Established offering uses unresolved transmission')
            graph[key].add(('transmission_description', c['description']['uuid']))
        elif kind == 'transmission_description':
            for r in c['engineering_assertions']:
                resolve(r, 'specification_assertion', records)
                graph[key].add(('specification_assertion', r['uuid']))
        elif kind == 'equipment_offering':
            item = resolve(c['item'], 'equipment_item', records)['content']
            offerings[key[1]]['item_kind'] = item['kind']
            offerings[key[1]]['item_content'] = item
            graph[key].add(('equipment_item', c['item']['uuid']))
            p = c['policy']
            if item['kind'] == 'accessory':
                require(p['brochure_listed'] and p['finding'] == 'eligible' and c['assignment'] == 'accessory_catalogue_only', 'Excluded/accessory effect offering')
            else:
                require(c['assignment'] != 'accessory_catalogue_only', 'Nonaccessory classified catalogue-only')
            if c['assignment'] in ('optional', 'standard', 'accessory_catalogue_only') and c['meta']['finding'] == 'established':
                require(p['finding'] == 'eligible', 'Unreviewed equipment policy')
                if c['assignment'] != 'standard':
                    require(p['brochure_listed'] or p['exception_authorization'] is not None, 'Missing brochure/authorized exception')
                if item['kind'] == 'factory_package':
                    require(p['manufacturer_identifies_package'], 'Package not manufacturer identified')
        elif kind == 'equipment_item':
            for child in c['contents']:
                child_item = resolve(child['item'], 'equipment_item', records)['content']
                require(child_item['kind'] != 'accessory', 'Accessory factory package constituent')
                graph[key].add(('equipment_item', child['item']['uuid']))
                for r in child['replaces']:
                    replacement = resolve(r, 'equipment_item', records)['content']
                    require(replacement['kind'] != 'accessory', 'Accessory factory package replacement target')
        elif kind == 'physical_feature_mapping':
            require(feature_states is not None and feature_states.get(c['state_uuid']) == c['feature_uuid'], 'Missing feature/state binding')
    no_cycles(graph)
    requirements = {}
    for key, record in records.items():
        c, kind = record['content'], record['kind']
        predicates = []
        if kind == 'specification_assertion':
            predicates.append(c['applicability']['predicate'])
        if 'qualified' in c:
            predicates.append(c['qualified']['applicability']['predicate'])
        if kind == 'equipment_item':
            predicates.extend(v['condition']['predicate'] for v in c['contents'])
        for p in predicates:
            validate_predicate(p, offerings, feature_states if feature_states is not None else {})
        if kind == 'compatibility_rule':
            rule = c['rule']
            for field in ('trigger', 'operands', 'offerings', 'universe'):
                if field not in rule:
                    continue
                operands = rule[field] if type(rule[field]) is list else [rule[field]]
                for operand in operands:
                    r = resolve(operand['revision'], operand['kind'], records)
                    require(operand['kind'] in ('transmission_offering', 'equipment_offering') and offerings[operand['revision']['uuid']].get('item_kind') != 'accessory', 'Accessory/wrong rule operand')
            if rule['kind'] == 'includes' and rule['trigger']['kind'] == 'equipment_offering':
                trigger = resolve(rule['trigger']['revision'], 'equipment_offering', records)['content']
                graph[('equipment_item', trigger['item']['uuid'])].update(('equipment_item', r['uuid']) for r in rule['items'])
            for field in ('items', 'added_items', 'removed_items'):
                for r in rule.get(field, []):
                    item = resolve(r, 'equipment_item', records)['content']
                    require(item['kind'] != 'accessory', 'Accessory compatibility target')
            if rule['kind'] in ('requires_all', 'requires_any'):
                trigger = rule['trigger']['revision']['uuid']
                requirements.setdefault(trigger, set()).update(o['revision']['uuid'] for o in rule['operands'])
    no_cycles(requirements)
    no_cycles(graph)
    if predecessor is not None:
        s.catalogue(predecessor)
        require(catalogue['logical_uuid'] == predecessor['logical_uuid'] and catalogue['target_uuid'] == predecessor['target_uuid'], 'Catalogue lineage target mismatch')
        require(catalogue['revision_number'] == predecessor['revision_number'] + 1 and catalogue['supersedes'] == {'uuid': predecessor['revision_uuid'], 'content_hash': predecessor['content_hash']}, 'Catalogue predecessor mismatch')
        old = {s.member_key(m): m for m in predecessor['members']}
        new = {s.member_key(m): m for m in catalogue['members']}
        require(all(old[k] == new[k] for k in old.keys() & new.keys()), 'Immutable member revision changed')
        removals = {s.member_key(r['member']): r['member'] for r in catalogue['removals']}
        require(removals == {k: v for k, v in old.items() if k not in new}, 'Unaccounted catalogue removals')
    elif catalogue['revision_number'] != 1:
        require(False, 'Successor validation requires exact predecessor snapshot')
    return offerings
