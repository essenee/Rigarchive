"""B2 synthetic publication tests: isolated DB and explicit temporary evidence."""
import copy
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase
from django.db import DatabaseError, OperationalError, close_old_connections, connection
from django.db.models.deletion import ProtectedError
from django.core.exceptions import ValidationError
from reference.models import Manufacturer, VehicleModel, Generation, VehicleDefinition
from reference.specifications.models import (
    SpecificationUnitRegistry, EvidenceDocument, EvidenceAssertionReference,
    SpecificationDefinition, SpecificationDefinitionRevision, SpecificationAssertion,
    SpecificationCatalogue, SpecificationCatalogueRevision, SpecificationCatalogueMembership,
    SpecificationCatalogueCoverage, SpecificationEvidenceLink, SpecificationPublicationReceipt,
    publication_writes,
)
from reference.specifications.publication import plan_publication, publish, EvidenceStore, PublicationInfrastructureError
from reference.specifications.canonical import ContractError, content_hash, digest
from reference.tests.specification_fixtures import fixture, seal, uid, update_members, equipment

MODELS = [SpecificationUnitRegistry, EvidenceDocument, EvidenceAssertionReference, SpecificationDefinition,
          SpecificationDefinitionRevision, SpecificationAssertion, SpecificationCatalogue,
          SpecificationCatalogueRevision, SpecificationCatalogueMembership,
          SpecificationCatalogueCoverage, SpecificationEvidenceLink, SpecificationPublicationReceipt]


class FixtureMixin:
    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix='ra-b2-publication-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.d, artifacts, self.records = fixture()
        for ref, raw in artifacts.items():
            p = self.root / ref;p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(raw)
        m = Manufacturer.objects.create(uuid=uid(1), name='Synthetic')
        vm = VehicleModel.objects.create(uuid=uid(2), manufacturer=m, name='Synthetic')
        g = Generation.objects.create(uuid=uid(3), vehicle_model=vm, name='Synthetic', start_year=2000)
        self.vd = VehicleDefinition.objects.create(uuid=uid(4), generation=g, model_year=2018, trim_name='Synthetic', engine_name='Synthetic', drivetrain='4WD', market='US')
        for name, obj in [('manufacturer', m), ('vehicle_model', vm), ('generation', g)]:
            self.d['parents'][name]['pk'] = obj.pk
        self.d['target'].update(vehicle_definition_pk=self.vd.pk, slug=self.vd.slug, parent_snapshot_hash=digest(self.d['parents']))
        seal(self.d)
        self.manifest = self.plan()

    def plan(self, d=None):
        return plan_publication(d or self.d, artifact_root=self.root, authorization_scope='Synthetic test approval scope; not production authorization')

    def execute(self, manifest=None, **kwargs):
        m = manifest or self.manifest
        return publish(m, artifact_root=self.root, authorized=True, authorized_manifest_hash=m['manifest_hash'], operator_label='test-only operator; simulated director approval', **kwargs)

    def counts(self):
        return [m.objects.count() for m in MODELS]

    def successor(self, previous):
        d = copy.deepcopy(self.d)
        c = d['catalogue']
        c.update(revision_uuid=uid(102), revision_number=2, supersedes={'uuid': str(previous.uuid), 'content_hash': previous.content_hash})
        for p in d['proposed_members']:
            p['state'] = 'existing';p.pop('payload')
        definition = SpecificationDefinitionRevision.objects.get(uuid=uid(20))
        d['dependencies'] = [{'kind': 'definition', 'revision': {'uuid': str(definition.uuid), 'content_hash': definition.content_hash}, 'expected_leaf': {'uuid': str(definition.uuid), 'content_hash': definition.content_hash}, 'finding': 'established'}]
        d['expected_state'] = {'state': 'current', 'catalogue': c['supersedes'], 'logical_uuid': c['logical_uuid'], 'revision_number': 1}
        c['coverage']['technical_specifications']['gaps'] = ['remaining synthetic gap'];seal(c);seal(d)
        return self.plan(d)


class PublicationTests(FixtureMixin, TestCase):
    def test_zero_write_planning_all_tables(self):
        tables = connection.introspection.table_names()
        def rows():
            with connection.cursor() as cursor:
                result = {}
                for table in tables:
                    cursor.execute('SELECT * FROM ' + connection.ops.quote_name(table))
                    result[table] = repr(cursor.fetchall())
                return result
        before = rows();self.plan();self.assertEqual(rows(), before)

    def test_publish_persists_exact_members_coverage_evidence_and_receipt(self):
        revision, receipt = self.execute()
        self.assertEqual(receipt.outcome, 'published')
        self.assertEqual(revision.content, self.d['catalogue'])
        self.assertEqual(revision.memberships.count(), 2)
        self.assertEqual(revision.coverage_records.count(), 4)
        self.assertEqual(SpecificationEvidenceLink.objects.count(), 3)
        self.assertEqual(EvidenceDocument.objects.count(), 1)
        self.assertEqual(EvidenceAssertionReference.objects.count(), 1)
        self.assertEqual(SpecificationAssertion.objects.get().value['amount'], '123.4')
        self.assertEqual(SpecificationAssertion.objects.get().content['original']['value'], '123.40')
        self.vd.refresh_from_db();self.assertEqual(self.vd.uuid.hex, uid(4).replace('-', ''))

    def test_exact_replay_only_adds_receipt(self):
        revision, _ = self.execute();before = self.counts()
        again, receipt = self.execute()
        self.assertEqual(again.pk, revision.pk);self.assertEqual(receipt.outcome, 'no_op_exact_match')
        after = self.counts();self.assertEqual(after[:-1], before[:-1]);self.assertEqual(after[-1], before[-1] + 1)

    def test_supersession_and_historical_snapshot(self):
        first, _ = self.execute();original = copy.deepcopy(first.content)
        second, receipt = self.execute(self.successor(first))
        self.assertEqual(receipt.outcome, 'published');self.assertEqual(second.supersedes_id, first.pk)
        first.refresh_from_db();self.assertEqual(first.content, original)
        self.assertEqual(second.memberships.count(), 2)
        self.assertEqual(SpecificationDefinitionRevision.objects.count(), 1)
        none, receipt = self.execute();self.assertIsNone(none);self.assertEqual(receipt.outcome, 'aborted_stale_plan')

    def revised_members(self):
        definition, assertion = copy.deepcopy(self.records)
        old_ref = {'uuid': uid(20), 'content_hash': definition['content']['content_hash']}
        definition['content']['meta'].update(revision_uuid=uid(22), revision_number=2, supersedes=old_ref)
        definition['content']['description'] = 'Refined synthetic definition';seal(definition['content'])
        assertion['content'].update(assertion_uuid=uid(23), definition_revision_uuid=uid(22), definition_revision_hash=definition['content']['content_hash'], supersedes_assertion_uuid=uid(21));seal(assertion['content'])
        return [definition, assertion], old_ref

    def test_definition_and_assertion_supersession_preserves_old_rows(self):
        first, _ = self.execute();m = self.successor(first);d = m['draft']
        records, old_ref = self.revised_members()
        d['dependencies'] = [{'kind': 'definition', 'revision': {'uuid': uid(22), 'content_hash': records[0]['content']['content_hash']}, 'expected_leaf': old_ref, 'finding': 'established'}]
        d['catalogue']['removals'] = [{'member': item, 'reason': 'Reviewed synthetic correction', 'evidence_refs': self.d['catalogue']['evidence_refs']} for item in first.content['members']]
        update_members(d, records);m = self.plan(d)
        revision, receipt = self.execute(m)
        self.assertEqual(receipt.outcome, 'published')
        self.assertEqual(SpecificationDefinitionRevision.objects.count(), 2)
        self.assertEqual(SpecificationAssertion.objects.count(), 2)
        self.assertEqual(SpecificationDefinitionRevision.objects.get(uuid=uid(22)).supersedes.uuid.hex, uid(20).replace('-', ''))
        self.assertEqual(self.execute(m)[1].outcome, 'no_op_exact_match')
        self.assertEqual(SpecificationCatalogueRevision.objects.get(pk=first.pk).content, self.d['catalogue'])

    def test_current_catalogue_replay_rejects_superseded_shared_definition(self):
        self.execute();d = copy.deepcopy(self.d);records, old_ref = self.revised_members()
        vd2 = VehicleDefinition.objects.create(uuid=uid(5), generation=self.vd.generation, model_year=2018, trim_name='Other', engine_name='Synthetic', drivetrain='4WD', market='US')
        d['target'].update(vehicle_definition_uuid=uid(5),vehicle_definition_pk=vd2.pk,slug=vd2.slug)
        d['target']['identity']['trim_name']='Other'
        d['catalogue'].update(target_uuid=uid(5),logical_uuid=uid(200),revision_uuid=uid(201))
        d['dependencies']=[{'kind':'definition','revision':{'uuid':uid(22),'content_hash':records[0]['content']['content_hash']},'expected_leaf':old_ref,'finding':'established'}]
        update_members(d,records)
        _, receipt = self.execute(self.plan(d));self.assertEqual(receipt.outcome,'published')
        revision, receipt = self.execute()
        self.assertIsNone(revision);self.assertEqual(receipt.outcome,'aborted_stale_plan')

    def test_stale_parallel_successor_manifest(self):
        first, _ = self.execute();a = self.successor(first);b = copy.deepcopy(a)
        b['draft']['catalogue']['revision_uuid'] = uid(103);seal(b['draft']['catalogue']);seal(b['draft']);b['draft_hash'] = b['draft']['content_hash'];seal(b, 'manifest_hash')
        self.execute(a);before = SpecificationCatalogueRevision.objects.count()
        revision, receipt = self.execute(b)
        self.assertIsNone(revision);self.assertEqual(receipt.outcome, 'aborted_stale_plan')
        self.assertEqual(SpecificationCatalogueRevision.objects.count(), before)

    def test_withdrawal_blocks_old_and_withdrawn_replay(self):
        first, _ = self.execute();m = self.successor(first)
        m['draft']['catalogue']['finding'] = 'withdrawn';seal(m['draft']['catalogue']);seal(m['draft']);m['draft_hash'] = m['draft']['content_hash'];seal(m, 'manifest_hash')
        self.execute(m)
        self.assertEqual(self.execute()[1].outcome, 'aborted_stale_plan')
        self.assertEqual(self.execute(m)[1].outcome, 'aborted_stale_plan')

    def test_evidence_bytes_changed_after_review(self):
        (self.root / 'fixture/source.bin').write_bytes(b'changed')
        revision, receipt = self.execute()
        self.assertIsNone(revision);self.assertEqual(receipt.outcome, 'aborted_stale_plan')
        self.assertEqual(SpecificationCatalogue.objects.count(), 0)

    def test_parent_or_baseline_changed(self):
        # Only isolated synthetic data is changed to exercise stale detection.
        self.vd.trim_name = 'Changed';self.vd.save()
        revision, receipt = self.execute()
        self.assertIsNone(revision);self.assertEqual(receipt.outcome, 'aborted_stale_plan')

    def test_authorization_decline_and_hash_tamper_write_nothing(self):
        before = self.counts()
        with self.assertRaises(ContractError):
            publish(self.manifest, artifact_root=self.root, authorized=False, authorized_manifest_hash=self.manifest['manifest_hash'], operator_label='test')
        tampered = copy.deepcopy(self.manifest);tampered['draft']['target']['slug'] = 'wrong'
        with self.assertRaises(ContractError):self.execute(tampered)
        self.assertEqual(self.counts(), before)

    def test_receipt_failure_rolls_back_every_new_table(self):
        before = self.counts()
        with patch('reference.specifications.publication._receipt', side_effect=DatabaseError('synthetic receipt failure')):
            with self.assertRaises(PublicationInfrastructureError):self.execute()
        self.assertEqual(self.counts(), before)
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_rejected_payload_durable_attempt_only(self):
        m = copy.deepcopy(self.manifest);m['draft']['surprise'] = 'bad';seal(m['draft']);m['draft_hash'] = m['draft']['content_hash'];seal(m, 'manifest_hash')
        revision, receipt = self.execute(m)
        self.assertIsNone(revision);self.assertEqual(receipt.outcome, 'rejected')
        self.assertEqual(SpecificationDefinition.objects.count(), 0)

    def test_append_only_supported_model_and_queryset_paths(self):
        revision, receipt = self.execute()
        for row in [revision, receipt, SpecificationDefinition.objects.get(), SpecificationAssertion.objects.get(), EvidenceDocument.objects.get(), SpecificationCatalogueCoverage.objects.first()]:
            with self.subTest(model=type(row).__name__):
                with self.assertRaises(ValidationError):row.save()
                with self.assertRaises(ValidationError):row.delete()
                with self.assertRaises(ValidationError):type(row).objects.filter(pk=row.pk).update(uuid=row.uuid)
                with self.assertRaises(ValidationError):type(row).objects.filter(pk=row.pk).delete()
                with self.assertRaises(ValidationError):type(row).objects.bulk_create([])

    def test_protected_baseline_and_source_relationships(self):
        self.execute()
        with self.assertRaises(ProtectedError):self.vd.delete()
        with self.assertRaises(ValidationError):EvidenceDocument.objects.get().delete()

    def test_root_or_revision_cannot_be_created_outside_publication(self):
        with self.assertRaises(ValidationError):SpecificationCatalogue.objects.create(vehicle_definition=self.vd)

    def test_b5_members_guarded_before_any_publication(self):
        from reference.tests.specification_fixtures import meta, qualified
        d = copy.deepcopy(self.d)
        ev = d['catalogue']['evidence_refs'][0]
        fm = dict(kind='physical_feature_mapping', content=seal(dict(meta=meta(80), target_uuid=uid(4), feature_uuid=uid(500), state_uuid=uid(501), qualified=qualified(ev))))
        update_members(d, self.records + [fm])
        before = self.counts()
        with self.assertRaises(ContractError):self.plan(d)
        self.assertEqual(self.counts(), before)

    def test_new_correspondence_chain_invalidates_bound_review(self):
        from types import SimpleNamespace
        from reference.specifications.publication import _correspondences
        row = SimpleNamespace(uuid=uid(300),source_id='synthetic',source_namespace='section',identity_type='section',native_identifier='synthetic')
        d=copy.deepcopy(self.d);d['dependencies']=[{'kind':'generation_correspondence','revision':{'uuid':uid(300),'content_hash':'sha256:'+'0'*64},'expected_leaf':{'uuid':uid(300),'content_hash':'sha256:'+'0'*64},'finding':'established'}]
        with patch('reference.specifications.publication.GenerationCorrespondenceRevision.objects.filter',return_value=[row]), patch('reference.ingestion.generation_correspondence._applicable_revisions',return_value=[row,SimpleNamespace(uuid=uid(301))]):
            with self.assertRaises(ContractError):_correspondences(self.vd,d)

    def test_path_escape_is_rejected(self):
        with self.assertRaises(ContractError):EvidenceStore(self.root).read(__file__)


class ConcurrentPublicationTests(FixtureMixin, TransactionTestCase):
    def test_competing_publications_never_fork(self):
        def attempt():
            close_old_connections()
            try:
                _, receipt = self.execute()
                return receipt.outcome
            except (OperationalError, PublicationInfrastructureError):
                return 'sqlite_lock_abort'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        self.assertLessEqual(SpecificationCatalogueRevision.objects.count(), 1)
        self.assertEqual(SpecificationPublicationReceipt.objects.filter(outcome='published').count(), SpecificationCatalogueRevision.objects.count())
        self.assertTrue(set(results) <= {'published', 'no_op_exact_match', 'aborted_stale_plan', 'sqlite_lock_abort'})
