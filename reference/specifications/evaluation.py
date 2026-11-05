"""Whole-selection compatibility and assertion applicability; no build generation."""
from enum import Enum

from .canonical import require
from .predicates import Truth, conjunction, disjunction, evaluate


class Compatibility(Enum):
    SUPPORTED = 'supported'
    INCOMPATIBLE = 'incompatible'
    UNVERIFIED = 'unverified'


class Applicability(Enum):
    APPLICABLE = 'applicable'
    INAPPLICABLE = 'inapplicable'
    UNESTABLISHED = 'unestablished'


def effective_truth(effective, context):
    if effective['status'] != 'established':
        return Truth.UNKNOWN
    results = []
    for group in ('production', 'order'):
        start, end = effective[group + '_start'], effective[group + '_end']
        if start is None and end is None:
            continue
        fact = context.selection[group + '_date']
        if fact['status'] == 'unknown':
            results.append(Truth.UNKNOWN)
        else:
            good = (start is None or fact['value'] >= start) and (end is None or fact['value'] <= end)
            results.append(Truth.TRUE if good else Truth.FALSE)
    return conjunction(results)


def qualified_truth(content, context, budget):
    qualified = content['qualified']
    return conjunction([evaluate(qualified['applicability']['predicate'], context, budget), effective_truth(qualified['effective'], context)])


def compatibility(context, rules, budget):
    """Requires exact validated catalogue rule records and one shared budget."""
    context.validate()
    require(len(rules) <= 1000, 'Catalogue rule limit exceeded')
    selected = set(context.selection['equipment'].get('offering_revision_uuids', []))
    tx = context.selection['transmission'].get('offering_revision_uuid')
    if tx is not None:
        selected.add(tx)
    uncertain = bool(any(o['kind'] == 'transmission_offering' for o in context.offerings.values()) and tx is None)
    uncertain |= any(context.selection[g]['status'] == 'unknown' for g in ('transmission', 'equipment'))
    uncertain |= any(f.status == 'conflicting' for f in context.fields.values())
    violated, proof, conflicting = False, False, False
    for uid in selected:
        c = context.offerings[uid]['content']
        availability = c.get('availability', c.get('assignment'))
        if availability == 'unknown' or c['meta']['finding'] != 'established':
            uncertain = True
        applicable = qualified_truth(c, context, budget)
        if applicable == Truth.FALSE and c['meta']['finding'] == 'established':
            violated = True
        elif applicable == Truth.UNKNOWN or c['meta']['finding'] != 'established':
            uncertain = True
    # Each effect carries fixed scope/trigger knowledge and, for a standard
    # trigger, an equipment premise resolved against ALL effects together.
    effects = []
    def reviewed_truth(content):
        scope = qualified_truth(content, context, budget)
        return conjunction([scope, Truth.TRUE if content['meta']['finding'] == 'established' else Truth.UNKNOWN])

    for uid in selected:
        offering = context.offerings[uid]
        item = offering.get('item_content')
        if item is not None and item['kind'] == 'factory_package':
            base = reviewed_truth(offering['content'])
            for part in item['contents']:
                status = conjunction([base, evaluate(part['condition']['predicate'], context, budget)])
                effects.append(([part['item']['uuid']], [r['uuid'] for r in part['replaces']], status, None))
    for member in rules:
        from .schemas import member as validate_member
        validate_member(member)
        require(member['kind'] == 'compatibility_rule', 'Wrong compatibility member kind')
        c = member['content']
        require(c['target_uuid'] == context.baseline_uuid, 'Foreign compatibility rule')
        rule = c['rule']
        if rule['kind'] not in ('includes', 'replaces'):
            continue
        trigger = context.offerings.get(rule['trigger']['revision']['uuid'])
        require(trigger is not None and trigger['kind'] == rule['trigger']['kind'] and trigger['content']['content_hash'] == rule['trigger']['revision']['content_hash'], 'Unbound effect trigger')
        standard_item = None
        if trigger['kind'] == 'equipment_offering' and trigger['content']['assignment'] == 'standard':
            standard_item = trigger['content']['item']['uuid']
            trigger_status = reviewed_truth(trigger['content'])
        else:
            trigger_status = conjunction([
                evaluate({'op': 'selected', 'offering_revision_uuid': rule['trigger']['revision']['uuid']}, context, budget),
                reviewed_truth(trigger['content']),
            ])
        premise = conjunction([trigger_status, reviewed_truth(c)])
        items = rule['items'] if rule['kind'] == 'includes' else rule['added_items']
        replacements = rule.get('removed_items', [])
        effects.append(([r['uuid'] for r in items], [r['uuid'] for r in replacements], premise, standard_item))

    def equipment_effects(statuses):
        removed, added, maybe_removed, maybe_added = set(), set(), set(), set()
        for (items, replacements, _, _), status in zip(effects, statuses):
            if status == Truth.TRUE:
                added.update(items)
                removed.update(replacements)
            elif status == Truth.UNKNOWN:
                maybe_added.update(items)
                maybe_removed.update(replacements)
        return removed, added, maybe_removed, maybe_added

    def remaining(item, state):
        removed, added, maybe_removed, maybe_added = state
        if item in removed:
            return Truth.UNKNOWN if item in added or item in maybe_added else Truth.FALSE
        return Truth.UNKNOWN if item in maybe_removed else Truth.TRUE

    # Start dependent effects unknown, then refine synchronously. Each effect
    # can gain knowledge only once; unresolved dependency cycles stay unknown.
    # Predicates are invoked and charged above, never hidden inside iteration.
    statuses = [conjunction([premise, Truth.UNKNOWN]) if item is not None else premise
                for _, _, premise, item in effects]
    for _ in range(len(effects) + 1):
        state = equipment_effects(statuses)
        resolved = [conjunction([premise, remaining(item, state)]) if item is not None else premise
                    for _, _, premise, item in effects]
        if resolved == statuses:
            break
        statuses = resolved
    else:
        require(False, 'Equipment effects did not resolve within their bound')
    removed, added, maybe_removed, maybe_added = equipment_effects(statuses)
    uncertain |= Truth.UNKNOWN in statuses
    def selected_truth(operand):
        offering = context.offerings.get(operand['revision']['uuid'])
        require(offering is not None and offering['kind'] == operand['kind'] and offering['content']['content_hash'] == operand['revision']['content_hash'], 'Unbound rule operand')
        if offering['kind'] == 'equipment_offering' and offering['content']['assignment'] == 'standard':
            c = offering['content']
            item_uuid = c['item']['uuid']
            presence = remaining(item_uuid, (removed, added, maybe_removed, maybe_added))
            if presence != Truth.TRUE:
                return presence
            return Truth.UNKNOWN if c['meta']['finding'] != 'established' else qualified_truth(c, context, budget)
        return evaluate({'op': 'selected', 'offering_revision_uuid': operand['revision']['uuid']}, context, budget)
    for member in rules:
        from .schemas import member as validate_member
        validate_member(member)
        require(member['kind'] == 'compatibility_rule', 'Wrong compatibility member kind')
        c = member['content']
        require(c['target_uuid'] == context.baseline_uuid, 'Foreign compatibility rule')
        if c['rule']['kind'] in ('includes', 'replaces'):
            # Fully accounted for by the simultaneous effect resolution above.
            continue
        scope = qualified_truth(c, context, budget)
        if scope == Truth.FALSE:
            continue
        if scope == Truth.UNKNOWN:
            uncertain = True
            continue
        rule = c['rule']
        if c['meta']['finding'] != 'established':
            conflicting = True
            continue
        kind = rule['kind']
        if kind in ('requires_all', 'requires_any', 'excludes'):
            trigger = selected_truth(rule['trigger'])
            if trigger == Truth.FALSE:
                continue
            if trigger == Truth.UNKNOWN:
                uncertain = True
                continue
            operands = [selected_truth(v) for v in rule['operands']]
            if kind == 'requires_all':
                result = conjunction(operands)
                violated |= result == Truth.FALSE
            elif kind == 'requires_any':
                result = disjunction(operands)
                violated |= result == Truth.FALSE
            else:
                result = disjunction(operands)
                violated |= result == Truth.TRUE
            uncertain |= result == Truth.UNKNOWN
        elif kind == 'cardinality':
            choices = [selected_truth(v) for v in rule['offerings']]
            known = choices.count(Truth.TRUE)
            possible = known + choices.count(Truth.UNKNOWN)
            if known > rule['maximum'] or possible < rule['minimum']:
                violated = True
            elif choices.count(Truth.UNKNOWN):
                uncertain = True
        elif kind == 'supports_combination':
            def standard(operand):
                offering = context.offerings.get(operand['revision']['uuid'])
                return offering is not None and offering['kind'] == 'equipment_offering' and offering['content']['assignment'] == 'standard'
            standard_states = [selected_truth(o) for o in rule['offerings'] if standard(o)]
            declared = {v['revision']['uuid'] for v in rule['offerings'] if not standard(v)}
            universe = {v['revision']['uuid'] for v in rule['universe'] if not standard(v)}
            for operand in (*rule['offerings'], *rule['universe']):
                selected_truth(operand)
            if any(v != Truth.TRUE for v in standard_states):
                uncertain = True
                continue
            # A scoped complete universe must cover the whole selected set;
            # pairwise proofs never cover a higher-order selection by union.
            proof |= selected <= universe if rule['scope_complete'] else selected == declared
    if conflicting:
        return Compatibility.UNVERIFIED
    if violated:
        return Compatibility.INCOMPATIBLE
    return Compatibility.SUPPORTED if proof and not uncertain else Compatibility.UNVERIFIED


def assertion_applicability(assertion, context, budget, selection_support):
    result = evaluate(assertion['applicability']['predicate'], context, budget)
    if result == Truth.FALSE:
        return Applicability.INAPPLICABLE
    if result == Truth.UNKNOWN or assertion['review']['finding'] != 'established':
        return Applicability.UNESTABLISHED
    unconditional = assertion['applicability']['predicate'] == {'op': 'true'}
    return Applicability.APPLICABLE if unconditional or selection_support == Compatibility.SUPPORTED else Applicability.UNESTABLISHED
