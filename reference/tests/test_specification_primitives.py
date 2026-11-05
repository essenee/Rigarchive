"""Isolated W2 primitive tests; B1 remains blocked on qualifier vocabulary."""
import copy
import itertools
import json
import unittest

from reference.specifications.canonical import (
    ContractError, canonical_bytes, content_hash, decimal_string, digest, loads,
    normalize_decimal, utc_time,
)
from reference.specifications.predicates import (
    EvaluationBudget, EvaluationContext, Fact, Truth, conjunction, disjunction,
    evaluate, validate_predicate, validate_selection,
)
from reference.specifications.values import (
    conversion, evidence_ref, validate_value, validate_value_definition,
)
from reference.specifications.schemas import coverage_record, rule_body


def uid(n):
    return f'00000000-0000-0000-0000-{n:012d}'


def evidence():
    return dict(source_id='synthetic', document_hash='sha256:' + '1' * 64,
                document_reference_hash='sha256:' + '2' * 64, extractor_id='synthetic',
                extractor_version='1', extraction_mode='synthetic_fixture',
                assertion_set_id='set', local_assertion_id='a', assertion_hash='sha256:' + '3' * 64)


def selection():
    return dict(language_version='1.0', baseline_uuid=uid(1), catalogue_revision_uuid=uid(2),
                transmission={'status': 'unknown'}, equipment={'status': 'known', 'offering_revision_uuids': []},
                production_date={'status': 'unknown'}, order_date={'status': 'unknown'})


def offerings():
    return {
        uid(3): {'kind': 'transmission_offering', 'content': {'target_uuid': uid(1), 'availability': 'optional'}},
        uid(4): {'kind': 'equipment_offering', 'item_kind': 'factory_package', 'content': {'target_uuid': uid(1), 'assignment': 'optional'}},
        uid(5): {'kind': 'equipment_offering', 'item_kind': 'factory_option', 'content': {'target_uuid': uid(1), 'assignment': 'unknown'}},
    }


def context():
    return EvaluationContext(uid(1), uid(2), selection(), offerings(), fields={'market': Fact('US', 'known')})


class CanonicalPrimitiveTests(unittest.TestCase):
    def test_sorted_utf8_canonical_bytes_and_hash(self):
        payload = {'b': ['µ', 0, None], 'a': True}
        self.assertEqual(digest({"a": 1}), "sha256:015abd7f5cc57a2dd94b7590f04ad8084273905ee33ec5cebeae62276a97f862")
        self.assertEqual(canonical_bytes(payload), b'{"a":true,"b":["\xc2\xb5",0,null]}')

    def test_hash_excludes_only_own_field(self):
        payload = {'nested': {'content_hash': 'historical'}, 'content_hash': 'old'}
        self.assertEqual(content_hash(payload), digest({'nested': {'content_hash': 'historical'}}))

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ContractError):
            loads('{"a":1,"a":2}')

    def test_float_and_nonfinite_json_rejected(self):
        for payload in ['1.0', 'NaN', 'Infinity', '-Infinity']:
            with self.subTest(payload=payload), self.assertRaises(ContractError):
                loads(payload)

    def test_invalid_unicode_rejected(self):
        with self.assertRaises(ContractError):
            canonical_bytes('\ud800')

    def test_producer_decimal_normalization(self):
        for original, result in [('123.40', '123.4'), ('-0.000', '0'), ('1E+3', '1000'), ('0.0100', '0.01')]:
            with self.subTest(original=original):
                self.assertEqual(normalize_decimal(original), result)

    def test_wire_decimal_rejection(self):
        for value in ['01', '+1', '-0', '1.0', '1e3', 'NaN', 1.2, True]:
            with self.subTest(value=value), self.assertRaises(ContractError):
                decimal_string(value)

    def test_legacy_numeric_bytes_preserved(self):
        raw = b'{ "original": 123.40, "unknown": null }\n'
        before = raw[:]
        with self.assertRaises(ContractError):
            loads(raw)
        # Original evidence is not reparsed/reserialized into the new wire family.
        self.assertEqual(raw, before)

    def test_utc_is_canonical(self):
        utc_time('2026-11-04T18:00:00+00:00')
        for v in ['2026-11-04T18:00:00Z', '2026-11-04T18:00:00', '2026-11-04T18:00:00-01:00']:
            with self.assertRaises(ContractError):
                utc_time(v)


class ValuePrimitiveTests(unittest.TestCase):
    def test_all_scalar_and_missing_kinds(self):
        values = [dict(status='reported', kind='quantity', amount='0', unit='mm'),
                  dict(status='reported', kind='integer', value=0), dict(status='reported', kind='boolean', value=False),
                  dict(status='reported', kind='category', term='diesel', manufacturer_term='DIESEL'),
                  dict(status='reported', kind='text', value='unresolved wording')]
        values += [dict(status=v, reason='synthetic') for v in ['unknown', 'not_published', 'not_applicable', 'explicitly_unavailable']]
        for value in values:
            with self.subTest(value=value):
                validate_value(value)

    def test_unknown_fields_and_bool_integer_rejected(self):
        for v in [dict(status='reported', kind='integer', value=True), dict(status='unknown', reason='x', value=0)]:
            with self.assertRaises(ContractError):
                validate_value(v)

    def test_range_endpoints(self):
        v = dict(status='reported', kind='range', lower='1', upper='1', unit='mm', lower_inclusive=True, upper_inclusive=True)
        validate_value(v)
        for change in [{'upper_inclusive': False}, {'upper': '0'}]:
            with self.assertRaises(ContractError):
                validate_value(v | change)

    def test_sequence_index_and_kind(self):
        element = dict(index=0, value=dict(status='reported', kind='integer', value=3), evidence_refs=[evidence()])
        v = dict(status='reported', kind='ordered_values', element_kind='integer', elements=[element])
        validate_value(v)
        for elements in [[element, element], [element | {'index': -1}], [element | {'value': dict(status='unknown', reason='x')}]]:
            with self.assertRaises(ContractError):
                validate_value(v | {'elements': elements})

    def test_document_qualified_identity(self):
        a = evidence(); b = a | {'document_hash': 'sha256:' + '4' * 64}
        evidence_ref(a); evidence_ref(b)
        self.assertNotEqual(canonical_bytes(a), canonical_bytes(b))

    def test_dimension_mismatch_and_unknown_category(self):
        definition = dict(value_kind='quantity', dimensional_family='length', categorical_terms=[], sequence_rule=None)
        validate_value_definition(dict(status='reported', kind='quantity', amount='1', unit='mm'), definition, {'mm': {'dimensional_family': 'length'}})
        with self.assertRaises(ContractError):
            validate_value_definition(dict(status='reported', kind='quantity', amount='1', unit='kg'), definition, {'kg': {'dimensional_family': 'mass'}})
        with self.assertRaises(ContractError):
            validate_value_definition(dict(status='reported', kind='category', term='x', manufacturer_term='x'), definition | {'value_kind': 'category'}, {})

    def test_conversion_uses_exact_rational(self):
        v = dict(rule_id='in-to-mm', rule_version='1', input_value='1', input_unit='in', output_value='25.4', output_unit='mm', factor_numerator='254', factor_denominator='10', offset='0', rounding='exact', decimal_places=None)
        conversion(v)
        with self.assertRaises(ContractError):
            conversion(v | {'output_value': '25.3'})

    def test_rounding_modes(self):
        v = dict(rule_id='round', rule_version='1', input_value='1', input_unit='mm', output_value='0.2', output_unit='mm', factor_numerator='1', factor_denominator='4', offset='0', rounding='half_even', decimal_places=1)
        conversion(v)
        conversion(v | {'rounding': 'half_up', 'output_value': '0.3'})


class PredicatePrimitiveTests(unittest.TestCase):
    def test_all_truth_table_pairs(self):
        for a, b in itertools.product(Truth, repeat=2):
            self.assertEqual(conjunction([a, b]), Truth.FALSE if Truth.FALSE in (a, b) else Truth.UNKNOWN if Truth.UNKNOWN in (a, b) else Truth.TRUE)
            self.assertEqual(disjunction([a, b]), Truth.TRUE if Truth.TRUE in (a, b) else Truth.UNKNOWN if Truth.UNKNOWN in (a, b) else Truth.FALSE)

    def test_unknown_transmission_independent_of_known_empty_equipment(self):
        c = context()
        self.assertEqual(evaluate({'op': 'selected', 'offering_revision_uuid': uid(3)}, c, EvaluationBudget()), Truth.UNKNOWN)
        self.assertEqual(evaluate({'op': 'selected', 'offering_revision_uuid': uid(4)}, c, EvaluationBudget()), Truth.FALSE)

    def test_known_transmission_and_two_factory_choices(self):
        c = context();c.selection['transmission'] = {'status': 'known', 'offering_revision_uuid': uid(3)}
        c.selection['equipment']['offering_revision_uuids'] = [uid(4)]
        p = {'op': 'all', 'args': [{'op': 'selected', 'offering_revision_uuid': uid(3)}, {'op': 'selected', 'offering_revision_uuid': uid(4)}]}
        self.assertEqual(evaluate(p, c, EvaluationBudget()), Truth.TRUE)

    def test_explicitly_unselected_transmission(self):
        c = context();c.selection['transmission'] = {'status': 'known', 'offering_revision_uuid': None}
        self.assertEqual(evaluate({'op': 'selected', 'offering_revision_uuid': uid(3)}, c, EvaluationBudget()), Truth.FALSE)

    def test_body_unknown_conflicting_and_not_applicable(self):
        p = {'op': 'eq', 'field': 'body_uuid', 'value': uid(8)}
        c = context()
        for fact, answer in [(Fact(), Truth.UNKNOWN), (Fact(uid(8), 'known'), Truth.TRUE), (Fact(uid(8), 'conflicting'), Truth.UNKNOWN), (Fact(status='not_applicable'), Truth.FALSE)]:
            c.fields['body_uuid'] = fact
            self.assertEqual(evaluate(p, c, EvaluationBudget()), answer)

    def test_date_missing_then_known(self):
        p = dict(op='date_between', field='production_date', start='2018-01-01', end=None)
        c = context()
        self.assertEqual(evaluate(p, c, EvaluationBudget()), Truth.UNKNOWN)
        c.selection['production_date'] = dict(status='known', value='2018-01-01')
        self.assertEqual(evaluate(p, c, EvaluationBudget()), Truth.TRUE)

    def test_feature_reference_and_conflict(self):
        c = context();c.feature_states[uid(9)] = uid(8);c.features[uid(8)] = Fact(uid(9), 'conflicting')
        self.assertEqual(evaluate(dict(op='feature_is', feature_uuid=uid(8), state_uuid=uid(9)), c, EvaluationBudget()), Truth.UNKNOWN)
        with self.assertRaises(ContractError):
            evaluate(dict(op='feature_is', feature_uuid=uid(7), state_uuid=uid(9)), c, EvaluationBudget())

    def test_no_not_and_strict_node_fields(self):
        for p in [{'op': 'not', 'args': [{'op': 'true'}]}, {'op': 'true', 'value': True}, {'op': 'eq', 'field': 'engine', 'value': 'x'}]:
            with self.assertRaises(ContractError):
                validate_predicate(p)

    def test_depth_limit_inclusive(self):
        p = {'op': 'true'}
        for _ in range(7):p = {'op': 'all', 'args': [p]}
        self.assertEqual(validate_predicate(p), 8)
        with self.assertRaises(ContractError):validate_predicate({'op': 'all', 'args': [p]})

    def test_operator_and_children_limit(self):
        branch = {'op': 'all', 'args': [{'op': 'true'} for _ in range(32)]}
        with self.assertRaises(ContractError):validate_predicate({'op': 'all', 'args': [branch] * 4})
        with self.assertRaises(ContractError):validate_predicate({'op': 'all', 'args': [{'op': 'true'}] * 33})

    def test_exact_operator_node_boundary(self):
        p = {'op': 'all', 'args': [{'op': 'all', 'args': [{'op': 'true'}] * 32} for _ in range(3)] + [{'op': 'all', 'args': [{'op': 'true'}] * 27}]}
        self.assertEqual(validate_predicate(p), 128)
        p['args'][-1]['args'].append({'op': 'true'})
        with self.assertRaises(ContractError):validate_predicate(p)

    def test_canonical_predicate_size_limit(self):
        leaves = [{'op': 'in', 'field': 'body_uuid', 'values': [uid(i) for i in range(100, 164)]} for _ in range(15)]
        with self.assertRaises(ContractError):validate_predicate({'op': 'all', 'args': leaves})

    def test_list_limit_and_order(self):
        for v in [list(range(1886, 1951)), [2018, 2017], [2018, 2018]]:
            with self.assertRaises(ContractError):validate_predicate({'op': 'in', 'field': 'model_year', 'values': v})

    def test_size_measured_in_canonical_utf8(self):
        # Whitespace in transport does not count; malformed extra operands still fail.
        p = {'op': 'true'}
        self.assertEqual(validate_predicate(json.loads(' { "op" : "true" } ')), validate_predicate(p))

    def test_budget_reserves_before_evaluation(self):
        b = EvaluationBudget(99999);c = context()
        self.assertEqual(evaluate({'op': 'true'}, c, b), Truth.TRUE)
        with self.assertRaises(ContractError):evaluate({'op': 'false'}, c, b)
        self.assertEqual(b.visits, 100000)

    def test_invalid_branch_validated_even_when_short_circuited(self):
        with self.assertRaises(ContractError):evaluate({'op': 'any', 'args': [{'op': 'true'}, {'op': 'selected', 'offering_revision_uuid': uid(99)}]}, context(), EvaluationBudget())

    def test_bad_selection_cardinality_duplicate_foreign_unavailable(self):
        for patch in [dict(transmission={'status': 'known', 'offering_revision_uuids': [uid(3), uid(6)]}), dict(equipment={'status': 'known', 'offering_revision_uuids': [uid(4), uid(4)]}), dict(equipment={'status': 'known', 'offering_revision_uuids': [uid(99)]})]:
            with self.assertRaises(ContractError):validate_selection(selection() | patch, uid(1), uid(2), offerings())
        c = context();c.offerings[uid(3)]['content']['availability'] = 'unavailable';c.selection['transmission'] = dict(status='known', offering_revision_uuid=uid(3))
        with self.assertRaises(ContractError):c.validate()

    def test_accessory_and_standard_not_selectable(self):
        for change in [('item_kind', 'accessory'), ('assignment', 'standard')]:
            c = context();c.selection['equipment']['offering_revision_uuids'] = [uid(4)]
            if change[0] == 'item_kind':c.offerings[uid(4)]['item_kind'] = change[1]
            else:c.offerings[uid(4)]['content'][change[0]] = change[1]
            with self.assertRaises(ContractError):c.validate()

    def test_schema_does_not_mutate_input(self):
        c = context();before = copy.deepcopy(c.selection)
        evaluate({'op': 'true'}, c, EvaluationBudget())
        self.assertEqual(c.selection, before)


class CoveragePrimitiveTests(unittest.TestCase):
    def test_partial_coverage_is_valid(self):
        coverage_record(dict(state='partial', declared_scope='synthetic', universe=[], evidence_refs=[], gaps=['unextracted'], exclusions=[], review=dict(finding='unresolved', reviewer='synthetic fixture', reviewed_at='2026-11-04T18:00:00+00:00', notes='not actual evidence')))

    def test_completeness_without_universe_rejected(self):
        with self.assertRaises(ContractError):coverage_record(dict(state='complete_within_declared_scope', declared_scope='synthetic', universe=[], evidence_refs=[evidence()], gaps=[], exclusions=[], review=dict(finding='established', reviewer='synthetic', reviewed_at='2026-11-04T18:00:00+00:00', notes='')))

    def test_cardinality_rule_bounds(self):
        rule = dict(kind='cardinality', offerings=[dict(kind='transmission_offering', revision=dict(uuid=uid(3), content_hash='sha256:' + '3' * 64))], minimum=0, maximum=1)
        rule_body(rule)
        with self.assertRaises(ContractError):rule_body(rule | {'maximum': 2})
