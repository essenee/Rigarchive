"""B4 synthetic tests: factory equipment, offerings, compatibility rules, and publication."""
import copy
from unittest.mock import patch
from django.test import TestCase
from django.db import DatabaseError
from django.core.exceptions import ValidationError
from reference.models import VehicleDefinition
from reference.specifications.models import (
    EquipmentItem, EquipmentItemRevision, EquipmentOffering, EquipmentOfferingRevision,
    CompatibilityRule, CompatibilityRuleRevision, SpecificationCatalogueRevision,
    SpecificationCatalogueMembership, SpecificationEvidenceLink,
)
from reference.specifications.publication import PublicationInfrastructureError
from reference.specifications.canonical import ContractError, loads
from reference.specifications.predicates import EvaluationContext, EvaluationBudget, Truth, evaluate, validate_selection
from reference.specifications.evaluation import compatibility, Compatibility
from reference.specifications.catalogue import validate_snapshot, record_key, record_ref
from reference.specifications.values import validate_unit_registry
from reference.tests.test_specification_publication import FixtureMixin
from reference.tests.specification_fixtures import uid, transmission, equipment, rule, operand, seal, update_members, meta


class EquipmentPublicationTests(FixtureMixin, TestCase):
    def factory_fixtures(self):
        d = copy.deepcopy(self.d)
        ev = d['catalogue']['evidence_refs'][0]
        # Option A (Standard)
        item_a, offer_a = equipment(d, n=40, kind='factory_option')
        offer_a['content']['assignment'] = 'standard'
        seal(offer_a['content'])
        # Option B (Optional)
        item_b, offer_b = equipment(d, n=42, kind='factory_option')
        # Item C (Constituent item of package)
        item_c = dict(kind='equipment_item', content=seal(dict(
            meta=meta(44), manufacturer_uuid=uid(1), namespace='synthetic',
            source_native_identity='item44', code='C01', name='Constituent item 44',
            description='part of package', kind='equipment_item', installation_channel='factory',
            contents=[], qualified=dict(applicability=dict(language_version='1.0', predicate={'op': 'true'}),
                                       effective=dict(status='established', production_start=None, production_end=None, order_start=None, order_end=None, notes='synthetic'),
                                       evidence_links=[dict(role='supports', reference=ev)])
        )))
        # Package P (Factory package containing item C)
        item_pkg = dict(kind='equipment_item', content=seal(dict(
            meta=meta(46), manufacturer_uuid=uid(1), namespace='synthetic',
            source_native_identity='pkg46', code='PKG46', name='Synthetic Package 46',
            description='factory package', kind='factory_package', installation_channel='factory',
            contents=[dict(item=record_ref(item_c), quantity=1,
                           condition=dict(language_version='1.0', predicate={'op': 'true'}),
                           replaces=[])],
            qualified=dict(applicability=dict(language_version='1.0', predicate={'op': 'true'}),
                           effective=dict(status='established', production_start=None, production_end=None, order_start=None, order_end=None, notes='synthetic'),
                           evidence_links=[dict(role='supports', reference=ev)])
        )))
        offer_pkg = dict(kind='equipment_offering', content=seal(dict(
            meta=meta(47), target_uuid=uid(4), item=record_ref(item_pkg), assignment='optional',
            policy=dict(brochure_document=dict(uuid=d['evidence_documents'][0]['uuid'], content_hash=d['evidence_documents'][0]['content_hash']),
                        brochure_listed=True, manufacturer_identifies_package=True, exception_authorization=None,
                        evidence_refs=[ev], finding='eligible', reason='package in brochure'),
            qualified=dict(applicability=dict(language_version='1.0', predicate={'op': 'true'}),
                           effective=dict(status='established', production_start=None, production_end=None, order_start=None, order_end=None, notes='synthetic'),
                           evidence_links=[dict(role='supports', reference=ev)])
        )))
        # Accessory (Catalogue-only)
        item_acc, offer_acc = equipment(d, n=48, kind='accessory')

        new_records = [item_a, offer_a, item_b, offer_b, item_c, item_pkg, offer_pkg, item_acc, offer_acc]
        records = copy.deepcopy(self.records) + new_records
        update_members(d, records)
        return d, records, self.plan(d)

    def test_equipment_classifications_and_exact_links_published(self):
        d, _, m = self.factory_fixtures()
        baseline = (str(self.vd.uuid), self.vd.slug, self.vd.generation_id)
        revision, receipt = self.execute(m)
        self.assertEqual(receipt.outcome, 'published')
        self.assertEqual(VehicleDefinition.objects.count(), 1)
        self.vd.refresh_from_db()
        self.assertEqual((str(self.vd.uuid), self.vd.slug, self.vd.generation_id), baseline)

        # 4 items with offerings + 1 constituent item without standalone offering = 5 items total
        self.assertEqual(EquipmentItem.objects.count(), 5)
        self.assertEqual(EquipmentItemRevision.objects.count(), 5)
        self.assertEqual(EquipmentOffering.objects.count(), 4)
        self.assertEqual(EquipmentOfferingRevision.objects.count(), 4)

        # Total catalogue memberships: 2 original (definition, assertion) + 9 new = 11
        self.assertEqual(revision.memberships.count(), 11)

        # Confirm distinct classifications
        kinds = set(EquipmentItemRevision.objects.values_list('kind', flat=True))
        self.assertEqual(kinds, {'factory_option', 'equipment_item', 'factory_package', 'accessory'})
        assignments = set(EquipmentOfferingRevision.objects.values_list('assignment', flat=True))
        self.assertEqual(assignments, {'standard', 'optional', 'accessory_catalogue_only'})

        # Idempotent exact replay
        self.assertEqual(self.execute(m)[1].outcome, 'no_op_exact_match')
        self.assertEqual(EquipmentOfferingRevision.objects.count(), 4)

    def test_brochure_controlled_scope_and_accessory_exclusion(self):
        d, records, _ = self.factory_fixtures()
        acc_offer = next(r for r in records if r['kind'] == 'equipment_offering' and r['content']['assignment'] == 'accessory_catalogue_only')
        # If brochure_listed is False for accessory, planning must reject
        acc_offer['content']['policy']['brochure_listed'] = False
        seal(acc_offer['content'])
        update_members(d, records)
        with self.assertRaises(ContractError):
            self.plan(d)
        self.assertEqual(EquipmentOffering.objects.count(), 0)

    def test_accessory_package_effects_rejected_during_zero_write_planning(self):
        for nested in (False, True):
            for field in ('item', 'replaces'):
                with self.subTest(nested=nested, field=field):
                    d, records, _ = self.factory_fixtures()
                    package = next(r for r in records if r['kind'] == 'equipment_item' and r['content']['kind'] == 'factory_package')
                    accessory = next(r for r in records if r['kind'] == 'equipment_item' and r['content']['kind'] == 'accessory')
                    part = package['content']['contents'][0]
                    part[field] = record_ref(accessory) if field == 'item' else [record_ref(accessory)]
                    seal(package['content'])
                    package_offer = next(r for r in records if r['kind'] == 'equipment_offering' and r['content']['item']['uuid'] == record_ref(package)['uuid'])
                    package_offer['content']['item'] = record_ref(package)
                    seal(package_offer['content'])
                    if nested:
                        outer, outer_offer = equipment(d, n=70)
                        outer['content'].update(kind='factory_package', contents=[dict(item=record_ref(package), quantity=1,
                            condition=dict(language_version='1.0', predicate={'op': 'true'}), replaces=[])])
                        seal(outer['content'])
                        outer_offer['content']['item'] = record_ref(outer)
                        outer_offer['content']['policy']['manufacturer_identifies_package'] = True
                        seal(outer_offer['content'])
                        records.remove(package_offer)
                        records += [outer, outer_offer]
                    update_members(d, records)
                    before = self.counts()
                    with self.assertRaisesRegex(ContractError, 'Accessory factory package'):
                        self.plan(d)
                    self.assertEqual(self.counts(), before)
                    for model in (EquipmentItem, EquipmentItemRevision, EquipmentOffering, EquipmentOfferingRevision,
                                  CompatibilityRule, CompatibilityRuleRevision):
                        self.assertEqual(model.objects.count(), 0)

    def test_compatibility_rules_evaluation_and_publication(self):
        d = copy.deepcopy(self.d)
        tx = transmission(d, n=30)  # tx[0] description, tx[1] offering
        opt_a = equipment(d, n=40)  # item, offering
        opt_b = equipment(d, n=42)  # item, offering

        # Rule 1: Requires all (tx requires opt_a)
        r_prereq = rule(d, {
            'kind': 'requires_all',
            'trigger': operand(tx[1]),
            'operands': [operand(opt_a[1])],
        }, n=60)
        # Rule 2: Excludes (opt_a excludes opt_b)
        r_exclude = rule(d, {
            'kind': 'excludes',
            'trigger': operand(opt_a[1]),
            'operands': [operand(opt_b[1])],
        }, n=62)
        # Rule 3: Cardinality on [opt_a, opt_b] between 0 and 1
        r_card = rule(d, {
            'kind': 'cardinality',
            'offerings': [operand(opt_a[1]), operand(opt_b[1])],
            'minimum': 0,
            'maximum': 1,
        }, n=64)
        # Rule 4: Supports combination for tx + opt_a
        # Operands are sorted by member_key: ('equipment_offering', ...) < ('transmission_offering', ...)
        r_combo = rule(d, {
            'kind': 'supports_combination',
            'offerings': [operand(opt_a[1]), operand(tx[1])],
            'scope_complete': True,
            'universe': [operand(opt_a[1]), operand(tx[1])],
        }, n=66)

        records = copy.deepcopy(self.records) + tx + opt_a + opt_b + [r_prereq, r_exclude, r_card, r_combo]
        update_members(d, records)

        registry = loads((self.root / 'fixture/units.json').read_bytes())
        offers = validate_snapshot(d['catalogue'], {record_key(r): r for r in records}, validate_unit_registry(registry))

        # Test Evaluation:
        # Case 1: tx selected, opt_a selected -> prereq met, exclude met, cardinality met, combo met => SUPPORTED
        selected_valid = {
            'language_version': '1.0', 'baseline_uuid': uid(4), 'catalogue_revision_uuid': uid(101),
            'transmission': {'status': 'known', 'offering_revision_uuid': uid(31)},
            'equipment': {'status': 'known', 'offering_revision_uuids': [uid(41)]},
            'production_date': {'status': 'unknown'}, 'order_date': {'status': 'unknown'},
        }
        ctx_valid = EvaluationContext(uid(4), uid(101), selected_valid, offers)
        rules_list = [r_prereq, r_exclude, r_card, r_combo]
        self.assertEqual(compatibility(ctx_valid, rules_list, EvaluationBudget()), Compatibility.SUPPORTED)

        # Case 2: tx selected without opt_a -> prereq violated => INCOMPATIBLE
        selected_missing_prereq = {
            'language_version': '1.0', 'baseline_uuid': uid(4), 'catalogue_revision_uuid': uid(101),
            'transmission': {'status': 'known', 'offering_revision_uuid': uid(31)},
            'equipment': {'status': 'known', 'offering_revision_uuids': []},
            'production_date': {'status': 'unknown'}, 'order_date': {'status': 'unknown'},
        }
        ctx_missing_prereq = EvaluationContext(uid(4), uid(101), selected_missing_prereq, offers)
        self.assertEqual(compatibility(ctx_missing_prereq, rules_list, EvaluationBudget()), Compatibility.INCOMPATIBLE)

        # Case 3: opt_a and opt_b both selected -> excludes violated and cardinality violated => INCOMPATIBLE
        selected_conflict = {
            'language_version': '1.0', 'baseline_uuid': uid(4), 'catalogue_revision_uuid': uid(101),
            'transmission': {'status': 'known', 'offering_revision_uuid': uid(31)},
            'equipment': {'status': 'known', 'offering_revision_uuids': [uid(41), uid(43)]},
            'production_date': {'status': 'unknown'}, 'order_date': {'status': 'unknown'},
        }
        ctx_conflict = EvaluationContext(uid(4), uid(101), selected_conflict, offers)
        self.assertEqual(compatibility(ctx_conflict, rules_list, EvaluationBudget()), Compatibility.INCOMPATIBLE)

        # Case 4: Publish all and verify persistence
        m = self.plan(d)
        rev, receipt = self.execute(m)
        self.assertEqual(receipt.outcome, 'published')
        self.assertEqual(CompatibilityRule.objects.count(), 4)
        self.assertEqual(CompatibilityRuleRevision.objects.count(), 4)
        rule_kinds = set(CompatibilityRuleRevision.objects.values_list('rule_kind', flat=True))
        self.assertEqual(rule_kinds, {'requires_all', 'excludes', 'cardinality', 'supports_combination'})

    def test_higher_order_uncertainty_and_unknown_selection(self):
        d = copy.deepcopy(self.d)
        opt_a = equipment(d, n=40)
        records = copy.deepcopy(self.records) + opt_a
        update_members(d, records)
        registry = loads((self.root / 'fixture/units.json').read_bytes())
        offers = validate_snapshot(d['catalogue'], {record_key(r): r for r in records}, validate_unit_registry(registry))

        # Unknown equipment selection status => UNKNOWN evaluation, not FALSE
        selected_unknown = {
            'language_version': '1.0', 'baseline_uuid': uid(4), 'catalogue_revision_uuid': uid(101),
            'transmission': {'status': 'unknown'},
            'equipment': {'status': 'unknown'},
            'production_date': {'status': 'unknown'}, 'order_date': {'status': 'unknown'},
        }
        ctx = EvaluationContext(uid(4), uid(101), selected_unknown, offers)
        self.assertEqual(evaluate({'op': 'selected', 'offering_revision_uuid': uid(41)}, ctx, EvaluationBudget()), Truth.UNKNOWN)
        self.assertEqual(compatibility(ctx, [], EvaluationBudget()), Compatibility.UNVERIFIED)

    def test_foreign_or_wrong_baseline_rejected_zero_writes(self):
        d, records, _ = self.factory_fixtures()
        offering = next(r for r in records if r['kind'] == 'equipment_offering')
        offering['content']['target_uuid'] = uid(99)
        seal(offering['content'])
        update_members(d, records)
        with self.assertRaises(ContractError):
            self.plan(d)
        self.assertEqual(EquipmentOffering.objects.count(), 0)

    def test_equipment_supersession_keeps_history(self):
        d, records, m = self.factory_fixtures()
        first, _ = self.execute(m)

        old = next(r for r in records if r['kind'] == 'equipment_offering' and record_ref(r)['uuid'] == uid(41))
        successor = copy.deepcopy(old)
        successor['content']['meta'].update(revision_uuid=uid(55), revision_number=2, supersedes=record_ref(old))
        successor['content']['assignment'] = 'unavailable'
        seal(successor['content'])

        records = [r for r in records if record_key(r) != ('equipment_offering', uid(41))] + [successor]
        d['catalogue'].update(revision_uuid=uid(102), revision_number=2, supersedes={'uuid': str(first.uuid), 'content_hash': first.content_hash})
        d['catalogue']['removals'] = [{'member': {'kind': 'equipment_offering', 'revision': record_ref(old)}, 'reason': 'Equipment withdrawn from factory scope', 'evidence_refs': d['catalogue']['evidence_refs']}]
        d['expected_state'] = {'state': 'current', 'catalogue': d['catalogue']['supersedes'], 'logical_uuid': d['catalogue']['logical_uuid'], 'revision_number': 1}
        update_members(d, records)

        deps = []
        for p in d['proposed_members']:
            kind = p['member']['kind']
            if kind == 'specification_assertion':
                p['state'] = 'existing'; p.pop('payload'); continue
            current = p['member']['revision']
            deps.append({'kind': kind, 'revision': current, 'expected_leaf': record_ref(old) if current['uuid'] == uid(55) else current, 'finding': 'established'})
            if current['uuid'] != uid(55):
                p['state'] = 'existing'; p.pop('payload')
        d['dependencies'] = sorted(deps, key=lambda v: (v['kind'], v['revision']['uuid']))
        seal(d)

        _, receipt = self.execute(self.plan(d))
        self.assertEqual(receipt.outcome, 'published')
        self.assertEqual(EquipmentOfferingRevision.objects.get(uuid=uid(41)).assignment, 'standard')
        self.assertEqual(EquipmentOfferingRevision.objects.get(uuid=uid(55)).assignment, 'unavailable')
        self.assertEqual(self.execute(m)[1].outcome, 'aborted_stale_plan')

    def test_atomic_rollback_on_receipt_failure(self):
        _, _, m = self.factory_fixtures()
        with patch('reference.specifications.publication._receipt', side_effect=DatabaseError('synthetic audit failure')):
            with self.assertRaises(PublicationInfrastructureError):
                self.execute(m)
        for model in (EquipmentItem, EquipmentItemRevision, EquipmentOffering, EquipmentOfferingRevision):
            self.assertEqual(model.objects.count(), 0)

    def test_immutable_equipment_and_rule_rows(self):
        d = copy.deepcopy(self.d)
        opt = equipment(d, n=40)
        r = rule(d, {'kind': 'cardinality', 'offerings': [operand(opt[1])], 'minimum': 0, 'maximum': 1}, n=60)
        update_members(d, copy.deepcopy(self.records) + opt + [r])
        m = self.plan(d)
        self.execute(m)

        for model in (EquipmentItem, EquipmentItemRevision, EquipmentOffering, EquipmentOfferingRevision, CompatibilityRule, CompatibilityRuleRevision):
            row = model.objects.first()
            self.assertIsNotNone(row)
            with self.assertRaises(ValidationError):
                row.save()
            with self.assertRaises(ValidationError):
                model.objects.filter(pk=row.pk).delete()
