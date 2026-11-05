"""B3 synthetic tests for later execution; not run during implementation."""
import copy
from unittest.mock import patch
from django.test import TestCase
from django.db import DatabaseError
from django.core.exceptions import ValidationError
from reference.models import VehicleDefinition
from reference.specifications.models import (
    TransmissionDescription, TransmissionDescriptionRevision,
    TransmissionOffering, TransmissionOfferingRevision, TransmissionEngineeringAssertion,
    SpecificationCatalogueRevision,
)
from reference.specifications.publication import PublicationInfrastructureError
from reference.specifications.canonical import ContractError, loads
from reference.specifications.predicates import EvaluationContext, EvaluationBudget, Truth, evaluate, validate_selection
from reference.specifications.evaluation import compatibility, Compatibility
from reference.specifications.catalogue import validate_snapshot, record_key, record_ref
from reference.specifications.values import validate_unit_registry
from reference.tests.test_specification_publication import FixtureMixin
from reference.tests.specification_fixtures import uid, transmission, seal, update_members


class TransmissionPublicationTests(FixtureMixin, TestCase):
    def alternatives(self):
        d = copy.deepcopy(self.d)
        a, b = transmission(d), transmission(d, n=32)
        b[0]['content'].update(type='manual', designation='Synthetic manual')
        for pair in (a, b):
            pair[0]['content']['code'] = 'SYNTHETIC-REUSED-CODE'
            pair[0]['content']['engineering_assertions'] = [record_ref(self.records[1])]
            seal(pair[0]['content'])
            pair[1]['content']['description'] = record_ref(pair[0]);seal(pair[1]['content'])
        records = copy.deepcopy(self.records) + a + b
        update_members(d, records)
        return d, records, self.plan(d)

    def test_two_alternatives_preserve_one_baseline_and_exact_links(self):
        d, _, m = self.alternatives()
        baseline = (str(self.vd.uuid), self.vd.slug, self.vd.generation_id)
        revision, receipt = self.execute(m)
        self.assertEqual(receipt.outcome, 'published')
        self.assertEqual(VehicleDefinition.objects.count(), 1)
        self.vd.refresh_from_db();self.assertEqual((str(self.vd.uuid), self.vd.slug, self.vd.generation_id), baseline)
        self.assertEqual(TransmissionDescription.objects.count(), 2)
        self.assertEqual(TransmissionOfferingRevision.objects.count(), 2)
        self.assertEqual(TransmissionEngineeringAssertion.objects.count(), 2)
        self.assertEqual(revision.memberships.count(), 6)
        self.assertEqual(revision.content['coverage'], d['catalogue']['coverage'])
        self.assertEqual(set(TransmissionDescriptionRevision.objects.values_list('transmission_type', flat=True)), {'automatic', 'manual'})
        self.assertEqual(self.execute(m)[1].outcome, 'no_op_exact_match')
        self.assertEqual(TransmissionOfferingRevision.objects.count(), 2)

    def test_offering_supersession_keeps_historical_availability(self):
        d, records, m = self.alternatives();first, _ = self.execute(m)
        old = next(r for r in records if r['kind'] == 'transmission_offering' and record_ref(r)['uuid'] == uid(31))
        successor = copy.deepcopy(old)
        successor['content']['meta'].update(revision_uuid=uid(35), revision_number=2, supersedes=record_ref(old))
        successor['content']['availability'] = 'unavailable';seal(successor['content'])
        records = [r for r in records if record_key(r) != ('transmission_offering', uid(31))] + [successor]
        d['catalogue'].update(revision_uuid=uid(102), revision_number=2, supersedes={'uuid': str(first.uuid), 'content_hash': first.content_hash})
        d['catalogue']['removals'] = [{'member': {'kind': 'transmission_offering', 'revision': record_ref(old)}, 'reason': 'Synthetic reviewed availability correction', 'evidence_refs': d['catalogue']['evidence_refs']}]
        d['expected_state'] = {'state': 'current', 'catalogue': d['catalogue']['supersedes'], 'logical_uuid': d['catalogue']['logical_uuid'], 'revision_number': 1}
        update_members(d, records)
        deps = []
        for p in d['proposed_members']:
            kind = p['member']['kind']
            if kind == 'specification_assertion':
                p['state'] = 'existing';p.pop('payload');continue
            current = p['member']['revision']
            deps.append({'kind': kind, 'revision': current, 'expected_leaf': record_ref(old) if current['uuid'] == uid(35) else current, 'finding': 'established'})
            if current['uuid'] != uid(35):
                p['state'] = 'existing';p.pop('payload')
        d['dependencies'] = sorted(deps, key=lambda v: (v['kind'], v['revision']['uuid']));seal(d)
        _, receipt = self.execute(self.plan(d))
        self.assertEqual(receipt.outcome, 'published')
        self.assertEqual(TransmissionOfferingRevision.objects.get(uuid=uid(31)).availability, 'optional')
        self.assertEqual(TransmissionOfferingRevision.objects.get(uuid=uid(35)).availability, 'unavailable')
        self.assertEqual(SpecificationCatalogueRevision.objects.get(pk=first.pk).content, m['draft']['catalogue'])
        self.assertEqual(self.execute(m)[1].outcome, 'aborted_stale_plan')

    def test_wrong_baseline_is_rejected_during_zero_write_planning(self):
        d, records, _ = self.alternatives()
        record = next(r for r in records if r['kind'] == 'transmission_offering')
        record['content']['target_uuid'] = uid(99);seal(record['content']);update_members(d, records)
        with self.assertRaises(ContractError):self.plan(d)
        self.assertEqual(TransmissionOffering.objects.count(), 0)

    def test_transmission_rows_roll_back_with_receipt_failure(self):
        _, _, m = self.alternatives()
        with patch('reference.specifications.publication._receipt', side_effect=DatabaseError('synthetic audit failure')):
            with self.assertRaises(PublicationInfrastructureError):self.execute(m)
        for model in (TransmissionDescription, TransmissionDescriptionRevision, TransmissionOffering, TransmissionOfferingRevision, TransmissionEngineeringAssertion):
            self.assertEqual(model.objects.count(), 0)

    def test_immutable_transmission_rows(self):
        _, _, m = self.alternatives();self.execute(m)
        for model in (TransmissionDescription, TransmissionDescriptionRevision, TransmissionOffering, TransmissionOfferingRevision):
            row = model.objects.first()
            with self.assertRaises(ValidationError):row.save()
            with self.assertRaises(ValidationError):model.objects.filter(pk=row.pk).delete()

    def test_availability_is_not_selection_or_compatibility(self):
        d, records, _ = self.alternatives()
        registry = loads((self.root / 'fixture/units.json').read_bytes())
        offers = validate_snapshot(d['catalogue'], {record_key(r): r for r in records}, validate_unit_registry(registry))
        selected = {'language_version': '1.0', 'baseline_uuid': uid(4), 'catalogue_revision_uuid': uid(101), 'transmission': {'status': 'unknown'}, 'equipment': {'status': 'known', 'offering_revision_uuids': []}, 'production_date': {'status': 'unknown'}, 'order_date': {'status': 'unknown'}}
        context = EvaluationContext(uid(4), uid(101), selected, offers)
        self.assertEqual(evaluate({'op': 'selected', 'offering_revision_uuid': uid(31)}, context, EvaluationBudget()), Truth.UNKNOWN)
        self.assertEqual(compatibility(context, [], EvaluationBudget()), Compatibility.UNVERIFIED)
        selected['transmission'] = {'status': 'known', 'offering_revision_uuid': uid(31)}
        offers[uid(31)]['content']['availability'] = 'unavailable'
        with self.assertRaises(ContractError):validate_selection(selected, uid(4), uid(101), offers)
