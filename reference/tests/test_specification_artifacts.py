"""Pure synthetic W2 artifact, snapshot, replay and compatibility regressions."""
import copy
import unittest
from dataclasses import replace
from itertools import permutations

from reference.specifications.canonical import ContractError, canonical_bytes, digest, loads
from reference.specifications.artifacts import validate_enrichment, validate_manifest, publication_disposition, PublicationState, byte_hash
from reference.specifications.catalogue import validate_snapshot, record_key, record_ref
from reference.specifications.serialization import serialize_artifact, deserialize_artifact
from reference.specifications.predicates import EvaluationContext, EvaluationBudget, Truth
from reference.specifications.evaluation import Compatibility, Applicability, compatibility, assertion_applicability
from reference.specifications.values import validate_unit_registry
from reference.tests.specification_fixtures import fixture, manifest, seal, update_members, uid, meta, review, transmission, equipment, rule, operand


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.d, self.a, self.r = fixture()

    def validate(self):
        return validate_enrichment(self.d, artifacts=self.a)

    def test_valid_draft_and_manifest(self):
        self.validate();validate_manifest(manifest(self.d), artifacts=self.a)

    def test_immutable_roundtrip(self):
        m = manifest(self.d);raw = serialize_artifact(m, artifacts=self.a)
        frozen = deserialize_artifact(raw, artifacts=self.a)
        detached = frozen.to_dict();detached['draft']['catalogue']['members'].clear()
        self.assertEqual(frozen.to_bytes(), raw)
        self.assertEqual(serialize_artifact(frozen.to_dict(), artifacts=self.a), raw)

    def test_unknown_keys_each_nested_boundary(self):
        for path in [[], ['target'], ['parents'], ['catalogue'], ['catalogue', 'coverage'], ['proposed_members', 0], ['evidence_documents', 0], ['assertion_references', 0]]:
            d = copy.deepcopy(self.d);v = d
            for key in path:v = v[key]
            v['surprise'] = 'invalid'
            with self.subTest(path=path), self.assertRaises(ContractError):validate_enrichment(d, artifacts=self.a)

    def test_every_draft_field_required(self):
        for key in self.d:
            d = copy.deepcopy(self.d);del d[key]
            with self.subTest(key=key), self.assertRaises(ContractError):validate_enrichment(d, artifacts=self.a)

    def test_manifest_tampering_and_version(self):
        for key, value in [('draft_hash', 'sha256:' + '0' * 64), ('schema_version', '2.0.0'), ('operation_type', 'vehicle_definition_import'), ('replay_policy', 'latest')]:
            m = manifest(self.d);m[key] = value;seal(m, 'manifest_hash')
            with self.subTest(key=key), self.assertRaises(ContractError):validate_manifest(m, artifacts=self.a)

    def test_parent_binding_and_year(self):
        for field, val in [('parent_snapshot_hash', 'sha256:' + '0' * 64), ('vehicle_definition_uuid', uid(99))]:
            d = copy.deepcopy(self.d);d['target'][field] = val;seal(d)
            with self.assertRaises(ContractError):validate_enrichment(d, artifacts=self.a)
        self.d['target']['identity']['model_year'] = 1999;seal(self.d)
        with self.assertRaises(ContractError):self.validate()

    def test_source_bytes_and_size(self):
        self.a['fixture/source.bin'] += b'changed'
        with self.assertRaises(ContractError):self.validate()

    def test_established_claim_cannot_ignore_explicit_source_market_or_year(self):
        for change in [dict(market='CA'), dict(model_year_start=2017, model_year_end=2017)]:
            d,a,records=fixture();doc=d['evidence_documents'][0];oldhash=doc['content_hash']
            doc['source_scope'].update(change);seal(doc)
            assertion=d['assertion_references'][0];oldassertionhash=assertion['content_hash'];assertion['reference']['document_reference_hash']=doc['content_hash'];seal(assertion)
            def rebind(v):
                if isinstance(v,dict):
                    if v.get('document_reference_hash')==oldhash:v['document_reference_hash']=doc['content_hash']
                    if v.get('assertion_hash')==oldassertionhash:v['assertion_hash']=assertion['content_hash']
                    if v.get('uuid')==doc['uuid'] and v.get('content_hash')==oldhash:v['content_hash']=doc['content_hash']
                    for x in v.values():rebind(x)
                elif isinstance(v,list):
                    for x in v:rebind(x)
            rebind(d);rebind(records)
            for r in records:seal(r['content'])
            records[1]['content']['definition_revision_hash']=records[0]['content']['content_hash'];seal(records[1]['content'])
            d['catalogue']['corpus_hash']=digest(d['corpus_inventory']);update_members(d,records)
            with self.assertRaises(ContractError):validate_enrichment(d,artifacts=a)

    def test_original_numeric_lexeme_preserved(self):
        source = self.a['fixture/assertions.json'].replace(b'"raw_value":"123.40"', b'"raw_value":123.40')
        self.a['fixture/assertions.json'] = source
        assertion = self.d['assertion_references'][0]
        old = assertion['content_hash'];assertion['retained_assertion_artifact']['content_hash'] = byte_hash(source);seal(assertion)
        def rebind(v):
            if isinstance(v, dict):
                if v.get('assertion_hash') == old:v['assertion_hash'] = assertion['content_hash']
                for child in v.values():rebind(child)
            elif isinstance(v, list):
                for child in v:rebind(child)
        rebind(self.d)
        records = [p['payload'] for p in self.d['proposed_members']]
        for record in records:seal(record['content'])
        records[1]['content']['definition_revision_hash'] = records[0]['content']['content_hash'];seal(records[1]['content'])
        self.d['catalogue']['corpus_hash'] = digest(self.d['corpus_inventory']);update_members(self.d, records)
        self.validate();self.assertEqual(self.a['fixture/assertions.json'], source)

    def test_extraction_identity_and_original_value_mismatch(self):
        for field, val in [('original_value_text', 'fabricated'), ('attribute_key', 'wrong')]:
            assertion = self.d['assertion_references'][0];before = copy.deepcopy(assertion)
            assertion[field] = val;seal(assertion);seal(self.d)
            with self.assertRaises(ContractError):self.validate()
            self.d['assertion_references'][0] = before

    def test_membership_no_latest_or_missing_revision(self):
        self.d['proposed_members'][0]['state'] = 'latest';seal(self.d)
        with self.assertRaises(ContractError):self.validate()
        self.d, self.a, self.r = fixture();self.d['catalogue']['members'].pop();seal(self.d['catalogue']);seal(self.d)
        with self.assertRaises(ContractError):self.validate()

    def test_partial_coverage_preserved_not_upgraded(self):
        self.validate()
        self.assertEqual({v['state'] for v in self.d['catalogue']['coverage'].values()}, {'partial'})

    def test_missing_corpus_interpretation(self):
        self.d['corpus_inventory']['nodes'][0]['interpretation_ids'] = ['missing']
        self.d['catalogue']['corpus_hash'] = digest(self.d['corpus_inventory']);seal(self.d['catalogue']);seal(self.d)
        with self.assertRaises(ContractError):self.validate()

    def test_incremental_snapshot_carries_state_and_accounts_removals(self):
        old = copy.deepcopy(self.d['catalogue']);new = copy.deepcopy(old)
        new.update(revision_uuid=uid(102), revision_number=2, supersedes={'uuid': old['revision_uuid'], 'content_hash': old['content_hash']})
        seal(new)
        units = validate_unit_registry(loads(self.a['fixture/units.json']))
        records = {record_key(r): r for r in self.r}
        validate_snapshot(new, records, units, predecessor=old)
        new['members'].pop();seal(new)
        with self.assertRaises(ContractError):validate_snapshot(new, records, units, predecessor=old)

    def test_same_uuid_changed_member_hash(self):
        self.d['proposed_members'][0]['payload']['content']['name'] = 'tampered'
        with self.assertRaises(ContractError):self.validate()

    def test_existing_member_exact_resolution(self):
        for p in self.d['proposed_members']:p['state'] = 'existing';del p['payload']
        seal(self.d)
        with self.assertRaises(ContractError):self.validate()
        self.d['dependencies'] = [dict(kind='definition', revision=record_ref(self.r[0]), expected_leaf=record_ref(self.r[0]), finding='established')]
        seal(self.d)
        validate_enrichment(self.d, artifacts=self.a, existing_members={record_key(r): r for r in self.r})

    def test_categorical_qualifier_pins_own_definition(self):
        parent, spec = copy.deepcopy(self.r)
        cat = copy.deepcopy(parent);c = cat['content'];c.update(meta=meta(22), key='qualifier.synthetic', value_kind='category', dimensional_family=None, categorical_terms=['maximum'], qualifier_rules=[]);seal(c)
        parent['content']['qualifier_rules'] = [dict(key='bound', value_kind='category', dimensional_family=None, required=True, categorical_definition=record_ref(cat))];seal(parent['content'])
        spec['content']['definition_revision_hash'] = parent['content']['content_hash']
        spec['content']['qualifiers'] = [dict(key='bound', value=dict(status='reported', kind='category', term='maximum', manufacturer_term='MAX'), evidence_refs=self.d['catalogue']['evidence_refs'])];seal(spec['content'])
        update_members(self.d, [parent, cat, spec]);self.validate()
        spec['content']['qualifiers'][0]['value']['term'] = 'minimum';seal(spec['content']);update_members(self.d, [parent, cat, spec])
        with self.assertRaises(ContractError):self.validate()

    def test_categorical_qualifier_wrong_kind_and_missing_ref(self):
        for r in [None, record_ref(self.r[0])]:
            parent = copy.deepcopy(self.r[0]);parent['content']['qualifier_rules'] = [dict(key='bound', value_kind='category', dimensional_family=None, required=False, categorical_definition=r)];seal(parent['content'])
            update_members(self.d, [parent])
            with self.assertRaises(ContractError):self.validate()

    def test_transmissions_share_baseline_and_accessories_do_not_select(self):
        records = self.r + transmission(self.d) + transmission(self.d, 32) + equipment(self.d, kind='accessory')
        update_members(self.d, records);self.validate()
        self.assertEqual(self.d['target']['vehicle_definition_uuid'], uid(4))


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.d, self.a, _ = fixture();self.m = manifest(self.d)
        self.state = PublicationState(copy.deepcopy(self.d['target']), copy.deepcopy(self.d['parents']), None, tuple(self.d['dependencies']), frozenset(), True)

    def disposition(self, state=None, auth=None):
        return publication_disposition(self.m, state or self.state, authorized_manifest_hash=auth or self.m['manifest_hash'], artifacts=self.a)

    def test_initial_publication(self):self.assertEqual(self.disposition(), 'publish')

    def test_exact_current_replay(self):
        state = replace(self.state, current_catalogue=copy.deepcopy(self.d['catalogue']), successful_manifest_hashes=frozenset([self.m['manifest_hash']]))
        self.assertEqual(self.disposition(state), 'no_op_exact_match')

    def test_changed_authorization_or_bindings(self):
        with self.assertRaises(ContractError):self.disposition(auth='sha256:' + '0' * 64)
        with self.assertRaises(ContractError):self.disposition(replace(self.state, relevant_bindings_unchanged=False))

    def test_changed_target_and_dependency(self):
        target = copy.deepcopy(self.state.target);target['slug'] = 'changed'
        with self.assertRaises(ContractError):self.disposition(replace(self.state, target=target))
        with self.assertRaises(ContractError):self.disposition(replace(self.state, dependencies=({},)))

    def test_superseded_or_withdrawn_replay(self):
        for changes in [dict(revision_uuid=uid(102)), dict(finding='withdrawn')]:
            current = copy.deepcopy(self.d['catalogue']);current.update(changes);seal(current)
            with self.assertRaises(ContractError):self.disposition(replace(self.state, current_catalogue=current, successful_manifest_hashes=frozenset([self.m['manifest_hash']])))

    def test_no_success_receipt_is_not_proven_replay(self):
        with self.assertRaises(ContractError):self.disposition(replace(self.state, current_catalogue=self.d['catalogue']))


class SelectionCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.d, self.a, records = fixture()
        self.tx = transmission(self.d);self.opt = equipment(self.d);self.extra = equipment(self.d, n=42)
        self.records = records + self.tx + self.opt + self.extra
        self.selection = dict(language_version='1.0', baseline_uuid=uid(4), catalogue_revision_uuid=uid(101), transmission=dict(status='known', offering_revision_uuid=uid(31)), equipment=dict(status='known', offering_revision_uuids=[uid(41)]), production_date=dict(status='unknown'), order_date=dict(status='unknown'))

    def evaluate(self, rules):
        records = self.records + rules
        update_members(self.d, records)
        validate_enrichment(self.d, artifacts=self.a)
        catalogue_records = {record_key(r): r for r in records}
        units = validate_unit_registry(loads(self.a['fixture/units.json']))
        offerings = validate_snapshot(self.d['catalogue'], catalogue_records, units)
        context = EvaluationContext(uid(4), uid(101), self.selection, offerings)
        return compatibility(context, rules, EvaluationBudget()), context

    def proof(self, choices=None, n=60):
        return rule(self.d, dict(kind='supports_combination', offerings=choices or [operand(self.opt[-1]), operand(self.tx[-1])], scope_complete=False, universe=[]), n)

    def test_independent_availability_is_unverified(self):
        self.assertEqual(self.evaluate([])[0], Compatibility.UNVERIFIED)

    def test_exact_supported_combination(self):
        self.assertEqual(self.evaluate([self.proof()])[0], Compatibility.SUPPORTED)

    def test_two_pairwise_proofs_do_not_support_triple(self):
        self.selection['equipment']['offering_revision_uuids'] = [uid(41), uid(43)]
        a = self.proof(n=60)
        b = self.proof(sorted([operand(self.extra[-1]), operand(self.tx[-1])], key=lambda v: (v['kind'],v['revision']['uuid'])), n=61)
        self.assertEqual(self.evaluate([a, b])[0], Compatibility.UNVERIFIED)

    def test_exclusion_is_incompatible(self):
        exclusion = rule(self.d, dict(kind='excludes', trigger=operand(self.tx[-1]), operands=[operand(self.opt[-1])]), 61)
        self.assertEqual(self.evaluate([self.proof(), exclusion])[0], Compatibility.INCOMPATIBLE)

    def test_requirements_and_cardinality(self):
        missing = rule(self.d, dict(kind='requires_all', trigger=operand(self.opt[-1]), operands=[operand(self.extra[-1])]), 61)
        self.assertEqual(self.evaluate([self.proof(), missing])[0], Compatibility.INCOMPATIBLE)
        cardinality = rule(self.d, dict(kind='cardinality', offerings=sorted([operand(self.opt[-1]),operand(self.tx[-1])],key=lambda v:(v['kind'],v['revision']['uuid'])), minimum=0, maximum=1), 62)
        self.assertEqual(self.evaluate([self.proof(), cardinality])[0], Compatibility.INCOMPATIBLE)

    def test_unknown_selection_and_conflict_are_not_supported(self):
        self.selection['equipment'] = dict(status='unknown')
        self.assertEqual(self.evaluate([self.proof()])[0], Compatibility.UNVERIFIED)
        self.selection['equipment'] = dict(status='known', offering_revision_uuids=[uid(41)])
        proof = self.proof();proof['content']['meta']['finding'] = 'unresolved';seal(proof['content'])
        self.assertEqual(self.evaluate([proof])[0], Compatibility.UNVERIFIED)

    def test_unresolved_offering_does_not_establish_prohibition(self):
        self.opt[-1]['content']['meta']['finding'] = 'unresolved'
        self.opt[-1]['content']['qualified']['applicability']['predicate'] = {'op': 'false'}
        seal(self.opt[-1]['content'])
        self.assertEqual(self.evaluate([self.proof()])[0], Compatibility.UNVERIFIED)

    def test_unknown_availability_and_effective_dates(self):
        self.opt[-1]['content']['assignment'] = 'unknown';seal(self.opt[-1]['content'])
        self.assertEqual(self.evaluate([self.proof()])[0], Compatibility.UNVERIFIED)
        self.opt[-1]['content']['assignment'] = 'optional'
        self.opt[-1]['content']['qualified']['effective']['production_start'] = '2018-01-01';seal(self.opt[-1]['content'])
        self.assertEqual(self.evaluate([self.proof()])[0], Compatibility.UNVERIFIED)

    def test_assertion_applicability_requires_supported_combination(self):
        support, context = self.evaluate([])
        assertion = copy.deepcopy(self.records[1]['content'])
        assertion['applicability']['predicate'] = dict(op='selected', offering_revision_uuid=uid(31))
        self.assertEqual(assertion_applicability(assertion, context, EvaluationBudget(), support), Applicability.UNESTABLISHED)
        support, context = self.evaluate([self.proof()])
        self.assertEqual(assertion_applicability(assertion, context, EvaluationBudget(), support), Applicability.APPLICABLE)

    def test_cycles_and_foreign_references_block(self):
        a = rule(self.d, dict(kind='requires_all', trigger=operand(self.opt[-1]), operands=[operand(self.extra[-1])]), 61)
        b = rule(self.d, dict(kind='requires_all', trigger=operand(self.extra[-1]), operands=[operand(self.opt[-1])]), 62)
        with self.assertRaises(ContractError):self.evaluate([a,b])
        a['content']['rule']['operands'][0]['revision']['uuid'] = uid(99);seal(a['content'])
        with self.assertRaises(ContractError):self.evaluate([a])

    def test_requires_any_missing_alternatives(self):
        a = rule(self.d, dict(kind='requires_any', trigger=operand(self.opt[-1]), operands=[operand(self.extra[-1])]), 61)
        self.assertEqual(self.evaluate([a])[0], Compatibility.INCOMPATIBLE)

    def test_rule_limit_rejected(self):
        with self.assertRaises(ContractError):compatibility(EvaluationContext(uid(4), uid(101), self.selection, {}), [self.proof()] * 1001, EvaluationBudget())


class EquipmentEffectCorrectionTests(unittest.TestCase):
    def setUp(self):
        self.d, self.a, records = fixture()
        self.tx = transmission(self.d)
        self.option = equipment(self.d)
        self.standard = equipment(self.d, n=44)
        self.replacement = equipment(self.d, n=46)
        self.included = equipment(self.d, n=48)
        self.standard[-1]['content']['assignment'] = 'standard'
        seal(self.standard[-1]['content'])
        self.records = records + self.tx + self.option + self.standard + self.replacement + self.included
        self.change = rule(self.d, dict(kind='replaces', trigger=operand(self.option[-1]),
            removed_items=[record_ref(self.standard[0])], added_items=[record_ref(self.replacement[0])]), 60)
        self.include = rule(self.d, dict(kind='includes', trigger=operand(self.standard[-1]),
            items=[record_ref(self.included[0])]), 61)
        self.proof = rule(self.d, dict(kind='supports_combination', offerings=sorted(
            [operand(self.option[-1]), operand(self.tx[-1])], key=lambda v: (v['kind'], v['revision']['uuid'])),
            scope_complete=False, universe=[]), 62)
        self.selection = dict(language_version='1.0', baseline_uuid=uid(4), catalogue_revision_uuid=uid(101),
            transmission=dict(status='known', offering_revision_uuid=uid(31)),
            equipment=dict(status='known', offering_revision_uuids=[uid(41)]),
            production_date=dict(status='unknown'), order_date=dict(status='unknown'))

    def assert_permutations(self, expected, rules=None):
        rules = rules if rules is not None else [self.change, self.include, self.proof]
        records = self.records + rules
        update_members(self.d, records)
        validate_enrichment(self.d, artifacts=self.a)
        offerings = validate_snapshot(self.d['catalogue'], {record_key(r): r for r in records},
            validate_unit_registry(loads(self.a['fixture/units.json'])))
        original = copy.deepcopy(self.selection)
        visits = set()
        for order in permutations(rules):
            with self.subTest(order=[record_ref(r)['uuid'] for r in order]):
                budget = EvaluationBudget()
                result = compatibility(EvaluationContext(uid(4), uid(101), self.selection, offerings), order, budget)
                self.assertEqual(result, expected)
                visits.add(budget.visits)
        self.assertEqual(self.selection, original)
        self.assertEqual(len(visits), 1)

    def test_established_replacement_disables_standard_include_in_every_order(self):
        # S is demonstrably removed. Its include is inactive; only the separate
        # exact proof establishes coexistence of the unchanged selection.
        self.assert_permutations(Compatibility.SUPPORTED)

    def test_effects_without_coexistence_proof_remain_unverified(self):
        self.assert_permutations(Compatibility.UNVERIFIED, [self.change, self.include])

    def test_inapplicable_replacement_does_not_obscure_standard_include(self):
        self.change['content']['qualified']['applicability']['predicate'] = {'op': 'false'}
        seal(self.change['content'])
        self.assert_permutations(Compatibility.SUPPORTED)

    def test_unknown_replacement_applicability_remains_uncertain(self):
        self.change['content']['qualified']['applicability']['predicate'] = dict(op='eq', field='market', value='US')
        seal(self.change['content'])
        self.assert_permutations(Compatibility.UNVERIFIED)

    def test_expired_replacement_does_not_obscure_standard_include(self):
        self.change['content']['qualified']['effective']['production_end'] = '2019-12-31'
        seal(self.change['content'])
        self.selection['production_date'] = dict(status='known', value='2020-01-01')
        self.assert_permutations(Compatibility.SUPPORTED)

    def test_unknown_replacement_date_remains_uncertain(self):
        self.change['content']['qualified']['effective']['production_end'] = '2019-12-31'
        seal(self.change['content'])
        self.assert_permutations(Compatibility.UNVERIFIED)

    def test_unselected_replacement_trigger_is_inactive(self):
        self.change['content']['rule']['trigger'] = operand(self.replacement[-1])
        seal(self.change['content'])
        self.assert_permutations(Compatibility.SUPPORTED)

    def test_unresolved_replacement_finding_remains_uncertain(self):
        self.change['content']['meta']['finding'] = 'unresolved'
        seal(self.change['content'])
        self.assert_permutations(Compatibility.UNVERIFIED)

    def test_inapplicable_standard_trigger_does_not_activate_replacement(self):
        self.replacement[-1]['content']['assignment'] = 'standard'
        self.replacement[-1]['content']['qualified']['applicability']['predicate'] = {'op': 'false'}
        seal(self.replacement[-1]['content'])
        self.change['content']['rule']['trigger'] = operand(self.replacement[-1])
        seal(self.change['content'])
        self.assert_permutations(Compatibility.SUPPORTED)

    def test_unknown_standard_trigger_does_not_establish_replacement(self):
        self.replacement[-1]['content']['assignment'] = 'standard'
        self.replacement[-1]['content']['qualified']['applicability']['predicate'] = dict(op='eq', field='market', value='US')
        seal(self.replacement[-1]['content'])
        self.change['content']['rule']['trigger'] = operand(self.replacement[-1])
        seal(self.change['content'])
        self.assert_permutations(Compatibility.UNVERIFIED)

    def test_mutually_dependent_replacements_remain_unknown(self):
        self.replacement[-1]['content']['assignment'] = 'standard'
        seal(self.replacement[-1]['content'])
        self.change['content']['rule']['trigger'] = operand(self.replacement[-1])
        self.change['content']['rule']['added_items'] = [record_ref(self.included[0])]
        seal(self.change['content'])
        dependent = rule(self.d, dict(kind='replaces', trigger=operand(self.standard[-1]),
            removed_items=[record_ref(self.replacement[0])], added_items=[record_ref(self.included[0])]), 63)
        self.assert_permutations(Compatibility.UNVERIFIED, [self.change, dependent, self.proof])

    def test_conflicting_add_remove_is_order_independent(self):
        inclusion = rule(self.d, dict(kind='includes', trigger=operand(self.option[-1]),
            items=[record_ref(self.standard[0])]), 63)
        self.assert_permutations(Compatibility.UNVERIFIED, [self.change, self.include, self.proof, inclusion])

    def test_standard_dependent_replacement_chain_resolves_together(self):
        # Removing S disables its replacement of the other standard item.
        self.replacement[-1]['content']['assignment'] = 'standard'
        seal(self.replacement[-1]['content'])
        dependent = rule(self.d, dict(kind='replaces', trigger=operand(self.standard[-1]),
            removed_items=[record_ref(self.replacement[0])], added_items=[record_ref(self.included[0])]), 63)
        # R adds a different item so it does not conflict with its own removal.
        self.change['content']['rule']['added_items'] = [record_ref(self.included[0])]
        seal(self.change['content'])
        requirement = rule(self.d, dict(kind='requires_all', trigger=operand(self.option[-1]),
            operands=[operand(self.replacement[-1])]), 64)
        self.assert_permutations(Compatibility.SUPPORTED, [self.change, dependent, requirement, self.proof])

    def test_package_inclusion_conflicting_with_removal_stays_unknown(self):
        package = self.option[0]['content']
        package.update(kind='factory_package', contents=[dict(item=record_ref(self.standard[0]), quantity=1,
            condition=dict(language_version='1.0', predicate={'op': 'true'}), replaces=[])])
        seal(package)
        self.option[-1]['content']['item'] = record_ref(self.option[0])
        self.option[-1]['content']['policy']['manufacturer_identifies_package'] = True
        seal(self.option[-1]['content'])
        for r in (self.change, self.proof):
            body = r['content']['rule']
            if 'trigger' in body:
                body['trigger'] = operand(self.option[-1])
            else:
                body['offerings'][0] = operand(self.option[-1])
            seal(r['content'])
        self.assert_permutations(Compatibility.UNVERIFIED)


class PackageAccessoryCorrectionTests(unittest.TestCase):
    def validate_package(self, *, accessory_constituent=False, accessory_replacement=False, nested=False):
        d, artifacts, records = fixture()
        child = equipment(d, n=40, kind='accessory' if accessory_constituent else 'equipment_item')[0]
        target = equipment(d, n=42, kind='accessory' if accessory_replacement else 'equipment_item')[0]
        package, offering = equipment(d, n=44)
        package['content'].update(kind='factory_package', contents=[dict(item=record_ref(child), quantity=1,
            condition=dict(language_version='1.0', predicate={'op': 'true'}), replaces=[record_ref(target)])])
        seal(package['content'])
        offering['content']['item'] = record_ref(package)
        offering['content']['policy']['manufacturer_identifies_package'] = True
        seal(offering['content'])
        records += [child, target, package, offering]
        if nested:
            outer, outer_offering = equipment(d, n=46)
            outer['content'].update(kind='factory_package', contents=[dict(item=record_ref(package), quantity=1,
                condition=dict(language_version='1.0', predicate={'op': 'true'}), replaces=[])])
            seal(outer['content'])
            outer_offering['content']['item'] = record_ref(outer)
            outer_offering['content']['policy']['manufacturer_identifies_package'] = True
            seal(outer_offering['content'])
            # The inner package need not have a standalone offering.
            records.remove(offering)
            records += [outer, outer_offering]
        update_members(d, records)
        return validate_enrichment(d, artifacts=artifacts)

    def test_accessory_package_constituent_rejected(self):
        with self.assertRaisesRegex(ContractError, 'Accessory factory package constituent'):
            self.validate_package(accessory_constituent=True)

    def test_accessory_package_replacement_target_rejected(self):
        with self.assertRaisesRegex(ContractError, 'Accessory factory package replacement target'):
            self.validate_package(accessory_replacement=True)

    def test_nested_package_accessory_effects_rejected(self):
        for field in ('accessory_constituent', 'accessory_replacement'):
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, 'Accessory factory package'):
                self.validate_package(nested=True, **{field: True})

    def test_valid_nonaccessory_package_contents_accepted(self):
        self.validate_package()
        self.validate_package(nested=True)


class AdditionalContractTests(unittest.TestCase):
    def test_standard_equipment_satisfies_prerequisite_without_checkbox(self):
        d,a,records = fixture();tx = transmission(d);option = equipment(d);standard = equipment(d,n=44)
        standard[-1]['content']['assignment'] = 'standard';seal(standard[-1]['content'])
        requirement = rule(d,dict(kind='requires_all',trigger=operand(option[-1]),operands=[operand(standard[-1])]),60)
        proof = rule(d,dict(kind='supports_combination',offerings=sorted([operand(option[-1]),operand(tx[-1])],key=lambda v:(v['kind'],v['revision']['uuid'])),scope_complete=False,universe=[]),61)
        records += tx+option+standard+[requirement,proof];update_members(d,records)
        validate_enrichment(d,artifacts=a)
        offerings = validate_snapshot(d['catalogue'],{record_key(r):r for r in records},validate_unit_registry(loads(a['fixture/units.json'])))
        selected = dict(language_version='1.0',baseline_uuid=uid(4),catalogue_revision_uuid=uid(101),transmission=dict(status='known',offering_revision_uuid=uid(31)),equipment=dict(status='known',offering_revision_uuids=[uid(41)]),production_date=dict(status='unknown'),order_date=dict(status='unknown'))
        c=EvaluationContext(uid(4),uid(101),selected,offerings)
        self.assertEqual(compatibility(c,[requirement,proof],EvaluationBudget()),Compatibility.SUPPORTED)
        self.assertEqual(selected['equipment']['offering_revision_uuids'],[uid(41)])

    def test_standard_triggered_include_does_not_invent_unknown_selection(self):
        d,a,records=fixture();tx=transmission(d);option=equipment(d);standard=equipment(d,n=44);included=equipment(d,n=46)
        standard[-1]['content']['assignment']='standard';seal(standard[-1]['content'])
        inclusion=rule(d,dict(kind='includes',trigger=operand(standard[-1]),items=[record_ref(included[0])]),60)
        proof=rule(d,dict(kind='supports_combination',offerings=sorted([operand(option[-1]),operand(tx[-1])],key=lambda v:(v['kind'],v['revision']['uuid'])),scope_complete=False,universe=[]),61)
        records+=tx+option+standard+included+[inclusion,proof];update_members(d,records);validate_enrichment(d,artifacts=a)
        offers=validate_snapshot(d['catalogue'],{record_key(r):r for r in records},validate_unit_registry(loads(a['fixture/units.json'])))
        selected=dict(language_version='1.0',baseline_uuid=uid(4),catalogue_revision_uuid=uid(101),transmission=dict(status='known',offering_revision_uuid=uid(31)),equipment=dict(status='known',offering_revision_uuids=[uid(41)]),production_date=dict(status='unknown'),order_date=dict(status='unknown'))
        self.assertEqual(compatibility(EvaluationContext(uid(4),uid(101),selected,offers),[inclusion,proof],EvaluationBudget()),Compatibility.SUPPORTED)
        self.assertEqual(selected['equipment']['offering_revision_uuids'],[uid(41)])

    def test_replacement_does_not_leave_standard_prerequisite_present(self):
        d,a,records=fixture();tx=transmission(d);option=equipment(d);standard=equipment(d,n=44);replacement=equipment(d,n=46)
        standard[-1]['content']['assignment']='standard';seal(standard[-1]['content'])
        requirement=rule(d,dict(kind='requires_all',trigger=operand(option[-1]),operands=[operand(standard[-1])]),60)
        change=rule(d,dict(kind='replaces',trigger=operand(option[-1]),removed_items=[record_ref(standard[0])],added_items=[record_ref(replacement[0])]),61)
        proof=rule(d,dict(kind='supports_combination',offerings=sorted([operand(option[-1]),operand(tx[-1])],key=lambda v:(v['kind'],v['revision']['uuid'])),scope_complete=False,universe=[]),62)
        records+=tx+option+standard+replacement+[requirement,change,proof];update_members(d,records);validate_enrichment(d,artifacts=a)
        offers=validate_snapshot(d['catalogue'],{record_key(r):r for r in records},validate_unit_registry(loads(a['fixture/units.json'])))
        selected=dict(language_version='1.0',baseline_uuid=uid(4),catalogue_revision_uuid=uid(101),transmission=dict(status='known',offering_revision_uuid=uid(31)),equipment=dict(status='known',offering_revision_uuids=[uid(41)]),production_date=dict(status='unknown'),order_date=dict(status='unknown'))
        self.assertEqual(compatibility(EvaluationContext(uid(4),uid(101),selected,offers),[requirement,change,proof],EvaluationBudget()),Compatibility.INCOMPATIBLE)

    def test_factory_package_contains_items_without_inventing_option_group(self):
        d,a,records=fixture();item,offer=equipment(d)
        package=copy.deepcopy(item);package['content'].update(meta=meta(44),name='Synthetic manufacturer package',source_native_identity='package44',kind='factory_package',contents=[dict(item=record_ref(item),quantity=1,condition=dict(language_version='1.0',predicate={'op':'true'}),replaces=[])])
        seal(package['content']);package_offer=copy.deepcopy(offer);package_offer['content'].update(meta=meta(45),item=record_ref(package));package_offer['content']['policy']['manufacturer_identifies_package']=True;seal(package_offer['content'])
        update_members(d,records+[item,package,package_offer]);validate_enrichment(d,artifacts=a)
        package_offer['content']['policy']['manufacturer_identifies_package']=False;seal(package_offer['content']);update_members(d,records+[item,package,package_offer])
        with self.assertRaises(ContractError):validate_enrichment(d,artifacts=a)

    def test_snapshot_removal_requires_explicit_historical_account(self):
        d,a,records=fixture();old=copy.deepcopy(d['catalogue']);new=copy.deepcopy(old)
        new.update(revision_uuid=uid(102),revision_number=2,supersedes=dict(uuid=old['revision_uuid'],content_hash=old['content_hash']),members=old['members'][:1]);seal(new)
        units=validate_unit_registry(loads(a['fixture/units.json']));remaining={record_key(records[0]):records[0]}
        with self.assertRaises(ContractError):validate_snapshot(new,remaining,units,predecessor=old)
        new['removals']=[dict(member=old['members'][1],reason='reviewed supersession',evidence_refs=old['evidence_refs'])];seal(new)
        validate_snapshot(new,remaining,units,predecessor=old)
        self.assertEqual(len(old['members']),2)

    def test_duplicate_local_assertions_in_different_documents_stay_independent(self):
        d,a,records=fixture();doc=copy.deepcopy(d['evidence_documents'][0]);doc['uuid']=uid(12)
        raw=b'second synthetic document';doc['raw_artifact']=dict(reference='fixture/second.bin',content_hash=byte_hash(raw));doc['byte_size']=len(raw);seal(doc);a['fixture/second.bin']=raw
        source=loads(a['fixture/assertions.json']);source['provenance']['extraction_provenance']['raw_artifact_hash']=doc['raw_artifact']['content_hash'];source['provenance']['extraction_provenance']['raw_artifact_reference']='fixture/second.bin';source['source_assertions'][0]['raw_value']='456'
        source_raw=canonical_bytes(source);a['fixture/second-assertions.json']=source_raw
        assertion=copy.deepcopy(d['assertion_references'][0]);assertion['uuid']=uid(13);assertion['reference']['document_hash']=doc['raw_artifact']['content_hash'];assertion['reference']['document_reference_hash']=doc['content_hash'];assertion['original_value_text']='456';assertion['retained_assertion_artifact']=dict(reference='fixture/second-assertions.json',content_hash=byte_hash(source_raw));seal(assertion)
        d['evidence_documents'].append(doc);d['assertion_references'].append(assertion)
        d['catalogue']['evidence_refs'].append(assertion['reference']|dict(assertion_hash=assertion['content_hash']));seal(d['catalogue']);seal(d)
        validate_enrichment(d,artifacts=a)
        self.assertEqual([v['reference']['local_assertion_id'] for v in d['assertion_references']],['a','a'])

    def test_unit_registry_factor_is_not_caller_conversion_permission(self):
        from reference.specifications.values import validate_conversion_units
        conversion=dict(rule_id='bogus',rule_version='1',input_value='1',input_unit='mm',output_value='100',output_unit='mm',factor_numerator='100',factor_denominator='1',offset='0',rounding='exact',decimal_places=None)
        _,a,_=fixture();units=validate_unit_registry(loads(a['fixture/units.json']))
        with self.assertRaises(ContractError):validate_conversion_units(conversion,units)

    def test_structured_legacy_numeric_values_keep_number_lexemes(self):
        from reference.specifications.artifacts import _legacy_assertion_binding
        d,a,_=fixture();source=a['fixture/assertions.json'].replace(b'"raw_value":"123.40"',b'"raw_value":{"amount":123.40}')
        a['fixture/assertions.json']=source;assertion=d['assertion_references'][0]
        assertion['retained_assertion_artifact']['content_hash']=byte_hash(source);assertion['original_value_text']='{"amount":123.40}'
        _legacy_assertion_binding(assertion,a);self.assertEqual(a['fixture/assertions.json'],source)

    def test_predicate_unknown_context_does_not_create_supported_rating(self):
        from reference.specifications.predicates import Fact
        d,a,records=fixture();tx=transmission(d);records+=tx;update_members(d,records)
        offerings=validate_snapshot(d['catalogue'],{record_key(r):r for r in records},validate_unit_registry(loads(a['fixture/units.json'])))
        selected=dict(language_version='1.0',baseline_uuid=uid(4),catalogue_revision_uuid=uid(101),transmission=dict(status='unknown'),equipment=dict(status='known',offering_revision_uuids=[]),production_date=dict(status='unknown'),order_date=dict(status='unknown'))
        context=EvaluationContext(uid(4),uid(101),selected,offerings,fields={'body_uuid':Fact()})
        assertion=copy.deepcopy(records[1]['content']);assertion['applicability']['predicate']=dict(op='eq',field='body_uuid',value=uid(99))
        self.assertEqual(assertion_applicability(assertion,context,EvaluationBudget(),Compatibility.SUPPORTED),Applicability.UNESTABLISHED)

    def test_closed_value_malformed_tags_and_keys(self):
        from reference.specifications.values import validate_value
        for value in [dict(status='reported',kind=[],value='x'),dict(status='reported',kind='boolean',value=1),dict(status='reported',kind='quantity',amount=1,unit='mm'),dict(status='not_published',reason='x',unit='mm')]:
            with self.subTest(value=value),self.assertRaises(ContractError):validate_value(value)
