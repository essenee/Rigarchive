"""Bounded predicate language 1.0 and factory selection evaluation."""
from dataclasses import dataclass, field
from enum import Enum

from .canonical import (
    MARKET, array, canonical_bytes, enum, iso_date, nullable, obj, require, uuid, year,
)


class Truth(Enum):
    TRUE = 'true'
    FALSE = 'false'
    UNKNOWN = 'unknown'


def conjunction(values):
    return Truth.FALSE if Truth.FALSE in values else Truth.UNKNOWN if Truth.UNKNOWN in values else Truth.TRUE


def disjunction(values):
    return Truth.TRUE if Truth.TRUE in values else Truth.UNKNOWN if Truth.UNKNOWN in values else Truth.FALSE


FIELDS = {'baseline_uuid': uuid, 'body_uuid': uuid, 'series_uuid': uuid, 'market': MARKET,
          'model_year': year, 'production_date': iso_date, 'order_date': iso_date}


def validate_predicate(predicate, offerings=None, feature_states=None):
    count = 0
    def visit(node, depth):
        nonlocal count
        require(depth <= 8, 'Predicate depth exceeds 8')
        count += 1
        require(count <= 128, 'Predicate operator nodes exceed 128')
        require(type(node) is dict, 'Predicate object required')
        op = node.get('op')
        if op in ('true', 'false'):
            obj(node, {'op': enum(op)})
        elif op in ('all', 'any'):
            obj(node, {'op': enum(op), 'args': array(lambda n: visit(n, depth + 1), 1, 32)})
        elif op in ('eq', 'in'):
            field_name = node.get('field')
            require(type(field_name) is str and field_name in FIELDS, 'Unsupported predicate field')
            check = FIELDS[field_name]
            shape = {'value': check} if op == 'eq' else {'values': array(check, 1, 64, key=canonical_bytes, ordered=True)}
            obj(node, {'op': enum(op), 'field': enum(*FIELDS)} | shape)
        elif op == 'date_between':
            obj(node, {'op': enum(op), 'field': enum('production_date', 'order_date'), 'start': nullable(iso_date), 'end': nullable(iso_date)})
            require(node['start'] is not None or node['end'] is not None, 'Date interval has no bounds')
            require(not(node['start'] and node['end']) or node['start'] <= node['end'], 'Reversed date interval')
        elif op == 'selected':
            obj(node, {'op': enum(op), 'offering_revision_uuid': uuid})
            if offerings is not None:
                require(node['offering_revision_uuid'] in offerings, 'Foreign offering predicate')
                require(selectable(offerings[node['offering_revision_uuid']]), 'Invalid/accessory offering predicate')
        elif op == 'feature_is':
            obj(node, {'op': enum(op), 'feature_uuid': uuid, 'state_uuid': uuid})
            if feature_states is not None:
                require(feature_states.get(node['state_uuid']) == node['feature_uuid'], 'Feature/state mismatch')
        else:
            require(False, 'Unsupported predicate operator')
    visit(predicate, 1)
    require(len(canonical_bytes(predicate)) <= 32768, 'Predicate exceeds 32 KiB')
    return count


def applicability(value):
    obj(value, {'language_version': enum('1.0'), 'predicate': validate_predicate})


def known_date(value):
    require(type(value) is dict, 'Date knowledge object required')
    if value.get('status') == 'unknown':
        obj(value, {'status': enum('unknown')})
    else:
        obj(value, {'status': enum('known'), 'value': iso_date})


def selectable(offering):
    if offering['kind'] == 'transmission_offering':
        return True
    return offering['kind'] == 'equipment_offering' and offering['content']['assignment'] in ('optional', 'unknown', 'unavailable') and offering.get('item_kind') in ('equipment_item', 'factory_option', 'factory_package')


def validate_selection(selection, baseline_uuid, catalogue_uuid, offerings):
    def transmission(v):
        require(type(v) is dict, 'Transmission knowledge object required')
        obj(v, {'status': enum('unknown')} if v.get('status') == 'unknown' else {'status': enum('known'), 'offering_revision_uuid': nullable(uuid)})
    def equipment(v):
        require(type(v) is dict, 'Equipment knowledge object required')
        obj(v, {'status': enum('unknown')} if v.get('status') == 'unknown' else {'status': enum('known'), 'offering_revision_uuids': array(uuid, key=lambda x: x, ordered=True)})
    obj(selection, {'language_version': enum('1.0'), 'baseline_uuid': uuid, 'catalogue_revision_uuid': uuid,
                    'transmission': transmission, 'equipment': equipment, 'production_date': known_date, 'order_date': known_date})
    require(selection['baseline_uuid'] == baseline_uuid and selection['catalogue_revision_uuid'] == catalogue_uuid, 'Selection target/catalogue mismatch')
    chosen = []
    if selection['transmission']['status'] == 'known' and selection['transmission']['offering_revision_uuid'] is not None:
        chosen.append((selection['transmission']['offering_revision_uuid'], 'transmission_offering'))
    if selection['equipment']['status'] == 'known':
        chosen.extend((u, 'equipment_offering') for u in selection['equipment']['offering_revision_uuids'])
    for uid, kind in chosen:
        member = offerings.get(uid)
        require(member is not None and member['kind'] == kind and selectable(member), 'Foreign/wrong-kind selection')
        content = member['content']
        require(content['target_uuid'] == baseline_uuid, 'Offering belongs to another baseline')
        require(content.get('availability', content.get('assignment')) != 'unavailable', 'Unavailable offering selected')
    return frozenset(uid for uid, _ in chosen)


@dataclass(frozen=True)
class Fact:
    """Internal evaluation input, not a new serialized evidence contract."""
    value: object = None
    status: str = 'unknown'  # known, unknown, conflicting, not_applicable

    def __post_init__(self):
        require(self.status in ('known', 'unknown', 'conflicting', 'not_applicable'), 'Invalid fact status')


@dataclass
class EvaluationBudget:
    visits: int = 0

    def reserve(self, count):
        require(type(self.visits) is int and self.visits >= 0, 'Invalid evaluation accounting')
        require(self.visits + count <= 100000, 'Aggregate evaluation budget exceeded')
        self.visits += count


@dataclass
class EvaluationContext:
    baseline_uuid: str
    catalogue_uuid: str
    selection: dict
    offerings: dict
    fields: dict = field(default_factory=dict)
    features: dict = field(default_factory=dict)
    feature_states: dict = field(default_factory=dict)

    def validate(self):
        uuid(self.baseline_uuid)
        uuid(self.catalogue_uuid)
        validate_selection(self.selection, self.baseline_uuid, self.catalogue_uuid, self.offerings)
        require(set(self.fields) <= set(FIELDS), 'Unknown evaluation field')
        for name, fact in self.fields.items():
            require(isinstance(fact, Fact), 'Explicit fact knowledge required')
            if fact.status == 'known':
                FIELDS[name](fact.value)
        if 'baseline_uuid' in self.fields:
            require(self.fields['baseline_uuid'] == Fact(self.baseline_uuid, 'known'), 'Baseline context override')
        for feature, fact in self.features.items():
            uuid(feature)
            require(isinstance(fact, Fact), 'Feature knowledge required')
            if fact.status == 'known':
                require(self.feature_states.get(fact.value) == feature, 'Feature context state mismatch')


def evaluate(predicate, context, budget):
    """Caller shares one budget for the complete request; no hidden resets."""
    context.validate()
    budget.reserve(validate_predicate(predicate, context.offerings, context.feature_states))
    def visit(node):
        op = node['op']
        if op in ('true', 'false'):
            return Truth.TRUE if op == 'true' else Truth.FALSE
        if op in ('all', 'any'):
            values = [visit(child) for child in node['args']]
            return conjunction(values) if op == 'all' else disjunction(values)
        if op == 'selected':
            uid = node['offering_revision_uuid']
            member = context.offerings[uid]
            group = context.selection['transmission' if member['kind'] == 'transmission_offering' else 'equipment']
            if group['status'] == 'unknown':
                return Truth.UNKNOWN
            selected = [group['offering_revision_uuid']] if member['kind'] == 'transmission_offering' else group['offering_revision_uuids']
            return Truth.TRUE if uid in selected else Truth.FALSE
        if op == 'feature_is':
            fact = context.features.get(node['feature_uuid'], Fact())
            return Truth.UNKNOWN if fact.status in ('unknown', 'conflicting') else Truth.TRUE if fact.value == node['state_uuid'] else Truth.FALSE
        name = node['field']
        if name == 'baseline_uuid':
            fact = Fact(context.baseline_uuid, 'known')
        elif name in ('production_date', 'order_date'):
            group = context.selection[name]
            fact = Fact(group.get('value'), group['status'])
        else:
            fact = context.fields.get(name, Fact())
        if fact.status in ('unknown', 'conflicting'):
            return Truth.UNKNOWN
        if fact.status == 'not_applicable':
            return Truth.FALSE
        if op == 'eq':
            result = fact.value == node['value']
        elif op == 'in':
            result = fact.value in node['values']
        else:
            result = (node['start'] is None or fact.value >= node['start']) and (node['end'] is None or fact.value <= node['end'])
        return Truth.TRUE if result else Truth.FALSE
    return visit(predicate)
