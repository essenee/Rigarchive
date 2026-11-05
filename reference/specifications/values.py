"""Closed W2 values, assertion provenance and dimension validation."""
from decimal import Decimal
from fractions import Fraction

from .canonical import (
    array, boolean, canonical_bytes, decimal_string, digest, enum, hash_string,
    integer, nullable, obj, positive, require, string, text, token, utc_time, uuid,
    verify_hash,
)

SCALAR_KINDS = ('quantity', 'range', 'integer', 'boolean', 'category', 'text')
MISSING = ('unknown', 'not_published', 'not_applicable', 'explicitly_unavailable')
EVIDENCE_FIELDS = {
    'source_id': text, 'document_hash': hash_string, 'document_reference_hash': hash_string,
    'extractor_id': text, 'extractor_version': text, 'extraction_mode': text,
    'assertion_set_id': text, 'local_assertion_id': text, 'assertion_hash': hash_string,
}


def evidence_ref(value):
    obj(value, EVIDENCE_FIELDS)


def evidence_refs(value, minimum=1):
    array(evidence_ref, minimum, key=canonical_bytes)(value)


def evidence_link(value):
    obj(value, {'role': enum('supports', 'contradicts', 'qualifies', 'excludes'), 'reference': evidence_ref})


def evidence_links(value, established=True):
    array(evidence_link, 1, key=canonical_bytes)(value)
    if established:
        require(any(v['role'] == 'supports' for v in value), 'Supporting evidence required')


def review(value):
    obj(value, {'finding': enum('established', 'unresolved', 'withdrawn'), 'reviewer': text, 'reviewed_at': utc_time, 'notes': string})


def ref(value):
    obj(value, {'uuid': uuid, 'content_hash': hash_string})


def refs(value, minimum=0):
    array(ref, minimum, key=lambda v: v['uuid'], ordered=True)(value)


def validate_value(value, scalar=False):
    require(type(value) is dict, 'Value must be object')
    if value.get('status') in MISSING:
        require(not scalar, 'Sequence/qualifier requires reported scalar')
        obj(value, {'status': enum(*MISSING), 'reason': text})
        return
    kind = value.get('kind')
    fields = {'status': enum('reported'), 'kind': enum(*(SCALAR_KINDS if scalar else (*SCALAR_KINDS, 'ordered_values')))}
    shapes = {
        'quantity': {'amount': decimal_string, 'unit': token},
        'range': {'lower': decimal_string, 'upper': decimal_string, 'unit': token, 'lower_inclusive': boolean, 'upper_inclusive': boolean},
        'integer': {'value': integer}, 'boolean': {'value': boolean},
        'category': {'term': token, 'manufacturer_term': text}, 'text': {'value': text},
        'ordered_values': {'element_kind': enum(*SCALAR_KINDS), 'elements': lambda v: array(sequence_element, 1, 64, key=lambda x: x['index'], ordered=True)(v)},
    }
    require(type(kind) is str and kind in shapes and (not scalar or kind != 'ordered_values'), 'Unsupported value kind')
    obj(value, fields | shapes[kind])
    if kind == 'range':
        low, high = Decimal(value['lower']), Decimal(value['upper'])
        require(low < high or (low == high and value['lower_inclusive'] and value['upper_inclusive']), 'Invalid range')
    if kind == 'ordered_values':
        require(all(v['value']['kind'] == value['element_kind'] for v in value['elements']), 'Heterogeneous sequence')


def sequence_element(value):
    obj(value, {'index': integer, 'value': lambda v: validate_value(v, scalar=True), 'evidence_refs': evidence_refs})
    require(value['index'] >= 0, 'Negative sequence index')


def original(value):
    obj(value, {'label': text, 'value': string, 'unit': nullable(string)})


def qualifier(value):
    obj(value, {'key': token, 'value': lambda v: validate_value(v, scalar=True), 'evidence_refs': evidence_refs})


def method(value):
    require(type(value) is dict, 'Method object required')
    if value.get('status') == 'unknown':
        obj(value, {'status': enum('unknown'), 'reason': text})
    else:
        obj(value, {'status': enum('established'), 'identifier': text, 'version': nullable(string), 'evidence_refs': evidence_refs})


def conversion(value):
    obj(value, {
        'rule_id': text, 'rule_version': text, 'input_value': decimal_string, 'input_unit': token,
        'output_value': decimal_string, 'output_unit': token, 'factor_numerator': decimal_string,
        'factor_denominator': decimal_string, 'offset': decimal_string,
        'rounding': enum('exact', 'half_even', 'half_up'), 'decimal_places': nullable(integer),
    })
    require(Decimal(value['factor_denominator']) != 0, 'Zero conversion denominator')
    expected = Fraction(value['input_value']) * Fraction(value['factor_numerator']) / Fraction(value['factor_denominator']) + Fraction(value['offset'])
    if value['rounding'] == 'exact':
        require(value['decimal_places'] is None and expected == Fraction(value['output_value']), 'Inexact conversion')
    else:
        places = value['decimal_places']
        require(type(places) is int and places >= 0, 'Invalid rounding places')
        # Rational arithmetic avoids ambient Decimal precision changing results.
        scaled = expected * 10 ** places
        sign = -1 if scaled < 0 else 1
        whole, rem = divmod(abs(scaled.numerator), scaled.denominator)
        comparison = 2 * rem - scaled.denominator
        if comparison > 0 or (comparison == 0 and (value['rounding'] == 'half_up' or whole % 2)):
            whole += 1
        require(Fraction(value['output_value']) == Fraction(sign * whole, 10 ** places), 'Incorrect rounded conversion')


def normalization(value):
    obj(value, {'method': enum('direct_copy', 'exact_mapping', 'parsed', 'converted', 'interpreted', 'unmapped'), 'rule_id': text, 'rule_version': text, 'conversion': nullable(conversion), 'notes': string})
    require((value['method'] == 'converted') == (value['conversion'] is not None), 'Conversion/method mismatch')


def validate_unit_registry(value):
    def unit(v):
        obj(v, {'token': token, 'dimensional_family': token, 'name': text, 'reference_unit': nullable(token), 'factor_numerator': decimal_string, 'factor_denominator': decimal_string, 'offset': decimal_string})
        require(Decimal(v['factor_denominator']) != 0, 'Zero unit denominator')
    obj(value, {'registry_version': text, 'units': array(unit, key=lambda u: u['token'], ordered=True), 'review': review, 'content_hash': hash_string})
    verify_hash(value)
    units = {u['token']: u for u in value['units']}
    roots = [u['dimensional_family'] for u in units.values() if u['reference_unit'] is None]
    require(len(set(roots)) == len(roots), 'Multiple roots in one dimensional family')
    for u in units.values():
        if u['reference_unit'] is None:
            require(u['factor_numerator'] == '1' and u['factor_denominator'] == '1' and u['offset'] == '0', 'Invalid root unit')
        else:
            root = units.get(u['reference_unit'])
            require(root is not None and root['reference_unit'] is None and root['dimensional_family'] == u['dimensional_family'], 'Invalid unit root/family')
    return units


def validate_value_definition(value, definition, units):
    validate_value(value)
    if value['status'] != 'reported':
        return
    require(value['kind'] == definition['value_kind'], 'Property value kind mismatch')
    if value['kind'] == 'ordered_values':
        rule = definition['sequence_rule']
        require(rule is not None and value['element_kind'] == rule['element_kind'], 'Sequence definition mismatch')
        indices = [v['index'] for v in value['elements']]
        if rule['contiguous_indices']:
            require(indices == list(range(indices[0], indices[0] + len(indices))), 'Noncontiguous sequence')
        for element in value['elements']:
            validate_value_definition(element['value'], definition | {'value_kind': rule['element_kind'], 'sequence_rule': None}, units)
    elif value['kind'] in ('quantity', 'range'):
        unit = units.get(value['unit'])
        require(unit is not None and unit['dimensional_family'] == definition['dimensional_family'], 'Unknown/incompatible unit')
    elif value['kind'] == 'category':
        require(value['term'] in definition['categorical_terms'], 'Unknown controlled category')


def validate_assertion(value):
    from .predicates import applicability
    obj(value, {
        'artifact_type': enum('rigarchive.specification_assertion.v1'), 'schema_version': enum('1.0.0'),
        'assertion_uuid': uuid, 'definition_revision_uuid': uuid, 'definition_revision_hash': hash_string,
        'value': validate_value, 'original': original, 'qualifiers': array(qualifier, key=lambda q: q['key']),
        'method': method, 'component': nullable(text), 'applicability': applicability,
        'evidence_links': evidence_links, 'normalization': normalization,
        'reconciliation': enum('single_source', 'corroborated', 'conflicting', 'ambiguous', 'incomplete'),
        'review': review, 'supersedes_assertion_uuid': nullable(uuid), 'content_hash': hash_string,
    })
    verify_hash(value)
    require(value['assertion_uuid'] != value['supersedes_assertion_uuid'], 'Self-superseding assertion')
    if value['reconciliation'] == 'conflicting':
        require(value['review']['finding'] == 'unresolved', 'Conflicting assertion requires unresolved review')
    conv = value['normalization']['conversion']
    if conv:
        require(value['value'].get('kind') == 'quantity' and conv['output_value'] == value['value']['amount'] and conv['output_unit'] == value['value']['unit'], 'Conversion output differs from assertion')


def validate_conversion_units(value, units):
    """Check declared arithmetic against the exact pinned unit registry."""
    conversion(value)
    a, b = units.get(value['input_unit']), units.get(value['output_unit'])
    require(a is not None and b is not None and a['dimensional_family'] == b['dimensional_family'], 'Incompatible conversion units')
    factor_a = Fraction(a['factor_numerator']) / Fraction(a['factor_denominator'])
    factor_b = Fraction(b['factor_numerator']) / Fraction(b['factor_denominator'])
    require(factor_b != 0, 'Zero output unit factor')
    require(Fraction(value['factor_numerator']) / Fraction(value['factor_denominator']) == factor_a / factor_b and Fraction(value['offset']) == (Fraction(a['offset']) - Fraction(b['offset'])) / factor_b, 'Conversion differs from pinned registry')
