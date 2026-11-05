"""Closed, explicitly enumerated W2 wire objects; no ORM or executable rules."""
from decimal import Decimal
from pathlib import PurePosixPath

from .canonical import (
    DRIVETRAIN, MARKET, array, boolean, canonical_bytes, enum, hash_string, integer,
    iso_date, nullable, obj, positive, require, string, text, token, utc_time, uuid,
    verify_hash, year,
)
from .predicates import applicability
from .values import (
    EVIDENCE_FIELDS, decimal_string, evidence_links, evidence_ref, evidence_refs,
    normalization, ref, refs, review, validate_assertion, validate_value,
)

KINDS = ('definition', 'specification_assertion', 'transmission_description', 'transmission_offering',
         'equipment_item', 'equipment_offering', 'compatibility_rule', 'physical_feature_mapping')
FINDING = enum('established', 'unresolved', 'withdrawn')


def artifact_ref(value):
    obj(value, {'reference': text, 'content_hash': hash_string})
    require('..' not in PurePosixPath(value['reference']).parts and '\\' not in value['reference'], 'Unsafe artifact reference')


def effective(value):
    obj(value, {'status': enum('established', 'unknown'), 'production_start': nullable(iso_date),
                'production_end': nullable(iso_date), 'order_start': nullable(iso_date),
                'order_end': nullable(iso_date), 'notes': string})
    for prefix in ('production', 'order'):
        a, b = value[prefix + '_start'], value[prefix + '_end']
        require(a is None or b is None or a <= b, 'Reversed effective dates')


def scope(value):
    obj(value, {'market': nullable(MARKET), 'model_year_start': nullable(year), 'model_year_end': nullable(year), 'effective': effective, 'notes': string})
    a, b = value['model_year_start'], value['model_year_end']
    require(a is None or b is None or a <= b, 'Reversed year scope')


def document(value):
    obj(value, {'uuid': uuid, 'source_id': text, 'raw_artifact': artifact_ref, 'source_locator': text,
                'acquired_at': utc_time, 'acquisition_method': text, 'media_type': text, 'byte_size': integer,
                'publisher': text, 'publication_kind': text, 'revision_status': enum('established', 'unknown'),
                'publication_revision': nullable(text), 'publication_date': nullable(iso_date),
                'original_filename': nullable(text), 'native_publication_id': nullable(text),
                'source_scope': scope, 'content_hash': hash_string})
    require(value['byte_size'] >= 0, 'Negative byte size')
    require((value['revision_status'] == 'established') == (value['publication_revision'] is not None), 'Publication revision status mismatch')
    verify_hash(value)


def location(value):
    def box(v):
        obj(v, {'coordinate_system': text, 'x': decimal_string, 'y': decimal_string, 'width': decimal_string, 'height': decimal_string})
        require(Decimal(v['width']) > 0 and Decimal(v['height']) > 0, 'Invalid bounding box')
    obj(value, {'page': nullable(positive), 'section': nullable(text), 'table': nullable(text), 'row': nullable(text),
                'column': nullable(text), 'paragraph': nullable(text), 'bounding_box': nullable(box), 'description': string})
    require(any(value.values()), 'Evidence location required')


def evidence_assertion(value):
    obj(value, {'uuid': uuid, 'reference': lambda v: obj(v, {k: c for k, c in EVIDENCE_FIELDS.items() if k != 'assertion_hash'}),
                'attribute_key': text, 'original_value_text': string, 'location': location,
                'retained_assertion_artifact': artifact_ref, 'content_hash': hash_string})
    verify_hash(value)


def interpretation(value):
    obj(value, {'interpretation_id': text, 'target_attribute_key': text, 'evidence_refs': evidence_refs,
                'value': validate_value, 'normalization': normalization, 'applicability': applicability, 'review': review})


def coverage_record(value):
    def exclusion(v):
        obj(v, {'subject': text, 'reason': text, 'evidence_refs': evidence_refs})
    obj(value, {'state': enum('unverified', 'partial', 'complete_within_declared_scope', 'not_applicable'),
                'declared_scope': text, 'universe': array(text, key=lambda v: v, ordered=True),
                'evidence_refs': lambda v: evidence_refs(v, 0), 'gaps': array(text, key=lambda v: v, ordered=True),
                'exclusions': array(exclusion, key=lambda v: (v['subject'], v['reason']), ordered=True), 'review': review})
    if value['state'] in ('complete_within_declared_scope', 'not_applicable'):
        require(value['evidence_refs'] and value['review']['finding'] == 'established', 'Coverage lacks evidence/review')
    if value['state'] == 'complete_within_declared_scope':
        require(value['universe'] and not value['gaps'], 'Complete coverage has missing universe/gaps')


def coverage(value):
    obj(value, {k: coverage_record for k in ('technical_specifications', 'transmission_offerings', 'equipment_offerings', 'compatibility')})


def corpus(value):
    def node(v):
        obj(v, {'node_id': text, 'parent_id': nullable(text), 'document': ref, 'location': location,
                'disposition': enum('extracted', 'retained_pending_representation', 'excluded', 'unresolved'),
                'assertion_refs': lambda a: evidence_refs(a, 0), 'interpretation_ids': array(text, key=lambda x: x, ordered=True), 'reason': string})
        require(v['disposition'] == 'extracted' or bool(v['reason']), 'Inventory reason required')
        if v['disposition'] == 'extracted':
            require(v['assertion_refs'], 'Extracted inventory lacks assertions')
            require(v['interpretation_ids'] or v['reason'], 'Missing normalization accounting')
    obj(value, {'documents': refs, 'expected_missing_sources': array(text, key=lambda v: v, ordered=True),
                'nodes': array(node, key=lambda v: v['node_id'], ordered=True), 'review': review})
    nodes = {n['node_id']: n for n in value['nodes']}
    for n in nodes.values():
        visited = {n['node_id']}
        p = n['parent_id']
        while p is not None:
            require(p in nodes and p not in visited, 'Missing/cyclic inventory parent')
            require(nodes[p]['document'] == n['document'], 'Cross-document inventory parent')
            visited.add(p)
            p = nodes[p]['parent_id']
    # Explicit duplicate leaves cannot double-count the same region.
    parents = {n['parent_id'] for n in nodes.values()}
    leaves = [n for n in nodes.values() if n['node_id'] not in parents]
    def region_key(node):
        loc = node['location']
        if any(v is not None for k, v in loc.items() if k != 'description'):
            loc = {k: v for k, v in loc.items() if k != 'description'}
        return canonical_bytes({'document': node['document'], 'location': loc})
    keys = [region_key(n) for n in leaves]
    require(len(keys) == len(set(keys)), 'Duplicate inventory region')
    for i, a in enumerate(leaves):
        for b in leaves[i + 1:]:
            x, y = a['location']['bounding_box'], b['location']['bounding_box']
            if a['document'] == b['document'] and a['location']['page'] == b['location']['page'] and x is not None and y is not None and x['coordinate_system'] == y['coordinate_system']:
                overlap_x = max(Decimal(x['x']), Decimal(y['x'])) < min(Decimal(x['x']) + Decimal(x['width']), Decimal(y['x']) + Decimal(y['width']))
                overlap_y = max(Decimal(x['y']), Decimal(y['y'])) < min(Decimal(x['y']) + Decimal(x['height']), Decimal(y['y']) + Decimal(y['height']))
                require(not (overlap_x and overlap_y), 'Overlapping inventory regions')


def body_binding(value):
    require(type(value) is dict, 'Body binding object required')
    if value.get('status') == 'legacy_unassessed':
        obj(value, {'status': enum('legacy_unassessed')})
    else:
        obj(value, {'status': enum('established'), 'identity': ref, 'semantic_digest': hash_string,
                    'profile_id': enum('van'), 'profile_version': enum('1.0'), 'evidence_binding': ref})


def series_binding(value):
    require(type(value) is dict, 'Series binding object required')
    if value.get('status') in ('legacy_unassessed', 'not_separate'):
        obj(value, {'status': enum('legacy_unassessed', 'not_separate')})
    else:
        obj(value, {'status': enum('established'), 'identity': ref, 'semantic_digest': hash_string, 'evidence_binding': ref})


def identity(value):
    obj(value, {'manufacturer_uuid': uuid, 'vehicle_model_uuid': uuid, 'generation_uuid': uuid,
                'model_year': year, 'trim_name': string, 'engine_name': string, 'drivetrain': DRIVETRAIN,
                'market': MARKET, 'body': body_binding, 'series': series_binding})


def target(value):
    obj(value, {'vehicle_definition_uuid': uuid, 'vehicle_definition_pk': positive, 'identity': identity, 'slug': text, 'parent_snapshot_hash': hash_string})
    require(len(value['slug']) <= 180, 'Target slug exceeds model limit')


def parents(value):
    obj(value, {
        'manufacturer': lambda v: obj(v, {'uuid': uuid, 'pk': positive, 'name': text, 'is_active': boolean}),
        'vehicle_model': lambda v: obj(v, {'uuid': uuid, 'pk': positive, 'manufacturer_uuid': uuid, 'name': text, 'is_active': boolean}),
        'generation': lambda v: obj(v, {'uuid': uuid, 'pk': positive, 'vehicle_model_uuid': uuid, 'start_year': year, 'end_year': nullable(year), 'is_active': boolean}),
    })
    require(value['vehicle_model']['manufacturer_uuid'] == value['manufacturer']['uuid'] and value['generation']['vehicle_model_uuid'] == value['vehicle_model']['uuid'], 'Parent relationship mismatch')
    require(all(p['is_active'] for p in value.values()), 'Inactive parent')
    g = value['generation']
    require(g['end_year'] is None or g['end_year'] >= g['start_year'], 'Invalid Generation range')


def expected(value):
    require(type(value) is dict, 'Expected state required')
    obj(value, {'state': enum('absent')} if value.get('state') == 'absent' else {'state': enum('current'), 'catalogue': ref, 'logical_uuid': uuid, 'revision_number': positive})


def dependency(value):
    kinds = (*KINDS[:1], *KINDS[2:], 'evidence_document', 'evidence_assertion', 'body_identity', 'series_identity', 'body_binding', 'series_binding', 'generation_correspondence', 'unit_registry')
    obj(value, {'kind': enum(*kinds), 'revision': ref, 'expected_leaf': nullable(ref), 'finding': FINDING})
    if value['kind'] in ('body_binding', 'series_binding', 'generation_correspondence'):
        require(value['expected_leaf'] is not None, 'Live revisioned dependency requires expected leaf')


def member_ref(value):
    obj(value, {'kind': enum(*KINDS), 'revision': ref})


def member_key(value):
    return value['kind'], value['revision']['uuid']


def catalogue(value):
    def removal(v):
        obj(v, {'member': member_ref, 'reason': text, 'evidence_refs': evidence_refs})
    obj(value, {'logical_uuid': uuid, 'revision_uuid': uuid, 'revision_number': positive, 'supersedes': nullable(ref),
                'target_uuid': uuid, 'finding': FINDING, 'members': array(member_ref, key=member_key, ordered=True),
                'coverage': coverage, 'corpus_hash': hash_string, 'evidence_refs': lambda v: evidence_refs(v, 0),
                'effective': effective, 'review': review,
                'removals': array(removal, key=lambda v: member_key(v['member']), ordered=True), 'content_hash': hash_string})
    require((value['revision_number'] == 1) == (value['supersedes'] is None), 'Catalogue predecessor mismatch')
    if value['revision_number'] == 1:
        require(not value['removals'], 'Initial catalogue cannot remove members')
    require(value['supersedes'] is None or value['supersedes']['uuid'] != value['revision_uuid'], 'Self-superseding catalogue')
    verify_hash(value)


def revision_meta(value):
    obj(value, {'logical_uuid': uuid, 'revision_uuid': uuid, 'revision_number': positive,
                'supersedes': nullable(ref), 'finding': FINDING, 'review': review})
    require((value['revision_number'] == 1) == (value['supersedes'] is None), 'Revision predecessor mismatch')
    require(value['supersedes'] is None or value['supersedes']['uuid'] != value['revision_uuid'], 'Self-superseding revision')


def qualified(value):
    obj(value, {'applicability': applicability, 'effective': effective, 'evidence_links': evidence_links})


def qualifier_rule(value):
    obj(value, {'key': token, 'value_kind': enum('quantity', 'range', 'integer', 'boolean', 'category', 'text'), 'dimensional_family': nullable(token), 'required': boolean, 'categorical_definition': nullable(ref)})
    require((value['value_kind'] == 'category') == (value['categorical_definition'] is not None), 'Categorical qualifier definition binding mismatch')
    if value['value_kind'] in ('quantity', 'range'):
        require(value['dimensional_family'] is not None, 'Quantity qualifier requires dimension')


def sequence_rule(value):
    obj(value, {'element_kind': enum('quantity', 'range', 'integer', 'boolean', 'category', 'text'), 'contiguous_indices': boolean})


def item_content(value):
    obj(value, {'item': ref, 'quantity': nullable(positive), 'condition': applicability, 'replaces': refs})


def equipment_policy(value):
    obj(value, {'brochure_document': nullable(ref), 'brochure_listed': boolean, 'manufacturer_identifies_package': boolean,
                'exception_authorization': nullable(artifact_ref), 'evidence_refs': evidence_refs,
                'finding': enum('eligible', 'review_required', 'excluded'), 'reason': text})
    require(not value['brochure_listed'] or value['brochure_document'] is not None, 'Missing applicable brochure')


def operand(value):
    obj(value, {'kind': enum('transmission_offering', 'equipment_offering'), 'revision': ref})


def operands(value, minimum=1):
    array(operand, minimum, key=member_key, ordered=True)(value)


def rule_body(value):
    require(type(value) is dict, 'Rule body object required')
    kind = value.get('kind')
    fields = {
        'requires_all': {'trigger': operand, 'operands': operands},
        'requires_any': {'trigger': operand, 'operands': operands},
        'excludes': {'trigger': operand, 'operands': operands},
        'includes': {'trigger': operand, 'items': lambda v: refs(v, 1)},
        'replaces': {'trigger': operand, 'removed_items': lambda v: refs(v, 1), 'added_items': lambda v: refs(v, 1)},
        'cardinality': {'offerings': operands, 'minimum': integer, 'maximum': integer},
        'supports_combination': {'offerings': lambda v: operands(v, 0), 'scope_complete': boolean, 'universe': lambda v: operands(v, 0)},
    }
    require(type(kind) is str and kind in fields, 'Unknown compatibility rule')
    obj(value, {'kind': enum(kind)} | fields[kind])
    if kind == 'cardinality':
        require(0 <= value['minimum'] <= value['maximum'] <= len(value['offerings']), 'Invalid cardinality')
    if kind == 'supports_combination':
        require(bool(value['universe']) == value['scope_complete'], 'Combination universe mismatch')
        if value['scope_complete']:
            require({member_key(v) for v in value['offerings']} <= {member_key(v) for v in value['universe']}, 'Combination outside universe')


def member(value):
    require(type(value) is dict and set(value) == {'kind', 'content'}, 'Closed member record required')
    enum(*KINDS)(value['kind'])
    kind, c = value['kind'], value['content']
    if kind == 'specification_assertion':
        validate_assertion(c)
        return
    fields = {
        'definition': {'key': token, 'name': text, 'category': token, 'description': text,
                       'value_kind': enum('quantity', 'range', 'integer', 'boolean', 'category', 'text', 'ordered_values'),
                       'dimensional_family': nullable(token), 'categorical_terms': array(token, key=lambda v: v),
                       'qualifier_rules': array(qualifier_rule, key=lambda v: v['key'], ordered=True),
                       'component_rule': enum('none', 'text', 'indexed'), 'method_semantics': text,
                       'sequence_rule': nullable(sequence_rule), 'evidence_refs': evidence_refs},
        'transmission_description': {'manufacturer_uuid': uuid, 'namespace': text, 'source_native_identity': text,
                                     'code': nullable(text), 'designation': text, 'type_status': enum('established', 'unknown'),
                                     'type': nullable(token), 'speed_count_status': enum('established', 'unknown'),
                                     'forward_speeds': nullable(positive), 'engineering_assertions': refs, 'qualified': qualified},
        'transmission_offering': {'target_uuid': uuid, 'description': ref, 'availability': enum('standard', 'optional', 'unavailable', 'unknown'), 'qualified': qualified},
        'equipment_item': {'manufacturer_uuid': uuid, 'namespace': text, 'source_native_identity': text, 'code': nullable(text),
                           'name': text, 'description': string, 'kind': enum('equipment_item', 'factory_package', 'factory_option', 'accessory'),
                           'installation_channel': enum('factory', 'manufacturer_accessory', 'unresolved'),
                           'contents': array(item_content, key=lambda v: v['item']['uuid']), 'qualified': qualified},
        'equipment_offering': {'target_uuid': uuid, 'item': ref, 'assignment': enum('standard', 'optional', 'unavailable', 'unknown', 'accessory_catalogue_only'), 'policy': equipment_policy, 'qualified': qualified},
        'compatibility_rule': {'target_uuid': uuid, 'rule': rule_body, 'qualified': qualified},
        'physical_feature_mapping': {'target_uuid': uuid, 'feature_uuid': uuid, 'state_uuid': uuid, 'qualified': qualified},
    }
    obj(c, {'meta': revision_meta, 'content_hash': hash_string} | fields[kind])
    verify_hash(c)
    if kind == 'definition':
        k = c['value_kind']
        require((k == 'ordered_values') == (c['sequence_rule'] is not None), 'Sequence rule mismatch')
        element = c['sequence_rule']['element_kind'] if k == 'ordered_values' else k
        if element in ('quantity', 'range'):
            require(c['dimensional_family'] is not None, 'Quantity definition requires dimension')
        require(bool(c['categorical_terms']) == (element == 'category'), 'Category terms mismatch')
    elif kind == 'transmission_description':
        require((c['type_status'] == 'established') == (c['type'] is not None), 'Transmission type status mismatch')
        require((c['speed_count_status'] == 'established') == (c['forward_speeds'] is not None), 'Transmission speed status mismatch')
    elif kind == 'equipment_item':
        require(bool(c['contents']) == (c['kind'] == 'factory_package'), 'Package contents mismatch')
