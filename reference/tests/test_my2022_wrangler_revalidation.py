"""Bounded ordinary agreement: no generation resolver, archive or ignored handoff required."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from reference import my2022_wrangler_revalidation as service
from reference.models import Manufacturer, VehicleModel, Generation, VehicleDefinition, ImportExecutionReceipt


class MY2022RevalidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.matrix = service.load_basis()
        cls.row = cls.matrix['rows'][0]
        def args(kind):
            return {k: cls.matrix['parents'][kind][k] for k in ('pk', 'uuid', 'slug')}
        maker = Manufacturer.objects.create(name='Jeep', **args('manufacturer'))
        model = VehicleModel.objects.create(manufacturer=maker, name='Wrangler', **args('vehicle_model'))
        generation = Generation.objects.create(vehicle_model=model, name='JL', start_year=2018, **args('generation'))
        cls.vehicle = VehicleDefinition.objects.create(generation=generation, slug=cls.row['target_slug'],
                                                       **cls.row['target_fields'])
        cls.receipt = ImportExecutionReceipt.objects.create(
            pk=3221, created_vehicle_definition=cls.vehicle,
            created_vehicle_definition_pk_snapshot=cls.vehicle.pk,
            created_vehicle_definition_uuid_snapshot=str(cls.vehicle.uuid),
            created_vehicle_definition_slug_snapshot=cls.vehicle.slug,
            operation_type='vehicle_definition_import', execution_outcome='created',
            candidate_reference=cls.row['candidate_reference'], manifest_hash='sha256:'+'1'*64,
            resolved_generation_id=generation.pk, target_slug=cls.vehicle.slug,
            target_fields_json=cls.row['target_fields'],
            **{'target_'+k: cls.row['target_fields'][k] for k in service.BASE_FIELDS},
            resolution_snapshot_json={'candidate_hash': cls.row['candidate_digest'],
                                      'matrix': {'matrix_digest': service.MATRIX_DIGEST, 'row_id': cls.row['row_id']}})

    def evaluate(self, receipt=None):
        return service.evaluate(receipt or self.receipt, evaluated_at='2026-11-16T20:00:00Z', revision='test')

    def compact(self):
        r = self.receipt
        entry = dict(receipt_pk=r.pk, receipt_uuid=str(r.uuid), snapshot_member='snapshots/test.json',
                     snapshot_canonical_sha256=service.digest(r.resolution_snapshot_json),
                     snapshot_raw_sha256=service.byte_hash(json.dumps(r.resolution_snapshot_json).encode()))
        return service.build_compact(r, self.evaluate(),
            {'matrix': {'reference': service.BASIS+'/matrix.json', 'sha256': service.MATRIX_SHA,
                        'digest': service.MATRIX_DIGEST},
             'approval': {'reference': service.BASIS+'/approval.json', 'sha256': service.APPROVAL_SHA}},
            {'horsepower': [], 'torque': []}, entry, 'sha256:'+'2'*64)

    def test_exact_agreement_and_determinism(self):
        a = self.evaluate()
        self.assertEqual(a['outcome'], 'EXACT_AGREEMENT')
        self.assertTrue(all(v['equal'] for v in a['comparisons'].values()))
        self.assertEqual(a, self.evaluate())

    def test_decimal_precision_uses_existing_normalization(self):
        # DecimalField persists 2.00; the approved wire value is canonical '2'.
        self.vehicle.refresh_from_db()
        self.assertEqual(str(self.vehicle.engine_displacement_liters), '2.00')
        self.assertEqual(self.evaluate()['comparisons']['engine_displacement_liters']['actual'], '2')
        self.assertEqual(service.decimal_string('2.0'), '2')
        self.assertEqual(self.evaluate()['outcome'], 'EXACT_AGREEMENT')

    def test_disagreement_is_not_forced_into_noop(self):
        self.vehicle.engine_cylinders = 6
        result = self.evaluate()
        self.assertEqual(result['outcome'], 'DISAGREEMENT')
        self.assertFalse(result['comparisons']['engine_cylinders']['equal'])

    def test_fixed_generation_is_compared_not_selected(self):
        self.vehicle.generation.slug = 'changed'
        self.assertEqual(self.evaluate()['outcome'], 'DISAGREEMENT')

    def test_missing_row(self):
        self.receipt.target_slug = 'missing'
        self.assertEqual(self.evaluate()['outcome'], 'INSUFFICIENT_EVIDENCE')

    def test_duplicate_canonical_identity_is_blocked(self):
        VehicleDefinition.objects.create(generation=self.vehicle.generation, slug='duplicate',
                                        **self.row['target_fields'])
        self.assertEqual(self.evaluate()['outcome'], 'EVALUATION_BLOCKED')

    def test_duplicate_creation_receipts_are_blocked(self):
        ImportExecutionReceipt.objects.create(created_vehicle_definition=self.vehicle,
            operation_type='vehicle_definition_import', execution_outcome='created')
        self.assertEqual(self.evaluate()['outcome'], 'EVALUATION_BLOCKED')

    def test_duplicate_matrix_row_rejected(self):
        matrix = copy.deepcopy(self.matrix)
        matrix['rows'].append(copy.deepcopy(matrix['rows'][0]))
        with patch.object(service, 'load_basis', return_value=matrix):
            self.assertEqual(self.evaluate()['outcome'], 'EVALUATION_BLOCKED')

    def test_approval_bytes_missing_or_changed(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root/service.BASIS).mkdir(parents=True)
            (root/service.BASIS/'matrix.json').write_bytes(service.retained(service.BASIS+'/matrix.json'))
            with self.assertRaises(service.EvidenceUnavailable):
                service.load_basis(root)
            (root/service.BASIS/'approval.json').write_text('{}')
            with self.assertRaises(ValidationError):
                service.load_basis(root)

    def test_wrong_candidate_or_receipt_binding(self):
        self.receipt.candidate_reference = 'wrong'
        self.assertEqual(self.evaluate()['outcome'], 'EVALUATION_BLOCKED')
        self.receipt.candidate_reference = self.row['candidate_reference']
        self.receipt.created_vehicle_definition_uuid_snapshot = 'wrong'
        self.assertEqual(self.evaluate()['outcome'], 'EVALUATION_BLOCKED')

    def test_wrong_candidate_digest_or_scalar_mirror(self):
        self.receipt.resolution_snapshot_json['candidate_hash'] = 'sha256:'+'0'*64
        self.assertEqual(self.evaluate()['outcome'], 'EVALUATION_BLOCKED')
        self.receipt.resolution_snapshot_json['candidate_hash'] = self.row['candidate_digest']
        self.receipt.target_engine_name = 'wrong'
        self.assertEqual(self.evaluate()['outcome'], 'EVALUATION_BLOCKED')

    def test_evaluation_has_no_database_writes(self):
        with CaptureQueriesContext(connection) as queries:
            self.evaluate()
        self.assertTrue(all(q['sql'].lstrip().upper().startswith('SELECT') for q in queries))

    def test_compact_integrity_metadata_and_current_identity(self):
        compact = self.compact()
        self.receipt.resolution_snapshot_json = compact
        self.assertEqual(service.validate_compact(self.receipt), compact)
        self.receipt.operator_label = 'changed'
        with self.assertRaisesMessage(ValidationError, 'metadata changed'):
            service.validate_compact(self.receipt)
        self.receipt.refresh_from_db()
        self.receipt.resolution_snapshot_json = compact
        self.vehicle.engine_cylinders = 6
        with self.assertRaises(ValidationError):
            service.validate_compact(self.receipt, self.vehicle)

    def test_tampering_is_detected(self):
        self.receipt.resolution_snapshot_json = self.compact()
        self.receipt.resolution_snapshot_json['revalidation']['identity']['fields']['engine_cylinders'] = 8
        with self.assertRaisesMessage(ValidationError, 'integrity mismatch'):
            service.validate_compact(self.receipt)

    def test_historical_hashes_are_archival_not_recreated(self):
        compact = self.compact()
        original = compact['original_execution']['historical_snapshot_digest']
        self.assertNotEqual(original, service.digest(compact))
        self.assertNotIn('generation_resolution', compact)
        self.assertNotIn('documents', json.dumps(compact))
        self.receipt.resolution_snapshot_json = compact
        values, binding = service.assess_compact_peer(self.vehicle, self.receipt)
        self.assertEqual(binding['receipt_evidence_digest'], service.digest(compact))
        self.assertEqual(binding['document_hashes'], [])

    def test_scoped_consumer_dispatch_uses_new_basis_only(self):
        from reference.ingestion.importing.powertrain_identity import assess_peer
        self.receipt.resolution_snapshot_json = self.compact()
        self.receipt.save(update_fields=['resolution_snapshot_json'])
        with patch('reference.ingestion.importing.powertrain_identity.validate_documents',
                   side_effect=AssertionError('Legacy evidence reader invoked')):
            self.assertEqual(assess_peer(self.vehicle)[0], service.record_powertrain(self.vehicle))

    def test_simulated_replacement_rolls_back_without_metadata_changes(self):
        old = service.metadata(self.receipt)
        original = copy.deepcopy(self.receipt.resolution_snapshot_json)
        compact = self.compact()
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.receipt.resolution_snapshot_json = compact
                self.receipt.save(update_fields=['resolution_snapshot_json'])
                self.receipt.refresh_from_db()
                self.assertEqual(service.metadata(self.receipt), old)
                service.validate_compact(self.receipt)
                raise RuntimeError('rollback')
        self.receipt.refresh_from_db()
        self.assertEqual(self.receipt.resolution_snapshot_json, original)
        self.assertEqual(service.metadata(self.receipt), old)

    def test_unsuccessful_result_cannot_be_compacted(self):
        self.vehicle.engine_cylinders = 6
        with self.assertRaises(ValidationError):
            self.compact()

    def test_66_historical_references_require_both_endpoints_and_preserve_hashes(self):
        edges = [{'source_receipt_pk': 3240, 'target_receipt_pk': 3221,
                  'original_digest': 'sha256:'+'a'*64} for _ in range(66)]
        retired = service.classify_archival_references(edges, {3221, 3240})
        self.assertEqual(len(retired), 66)
        self.assertTrue(all(e['treatment'] == 'ARCHIVAL_ONLY_AFTER_NEW_MATRIX_AGREEMENT'
                            and e['original_digest'] == edges[0]['original_digest'] for e in retired))
        blocked = service.classify_archival_references(edges, {3221})
        self.assertTrue(all(e['treatment'] == 'BLOCKED_ACTIVE_DEPENDENCY' for e in blocked))
        self.assertNotIn('treatment', edges[0])

    def test_compact_verification_does_not_read_handoff_sources_or_archive(self):
        self.receipt.resolution_snapshot_json = self.compact()
        original_reader = service.retained
        def basis_only(reference, root=None):
            self.assertTrue(reference.startswith(service.BASIS+'/'))
            return original_reader(reference, root)
        with patch.object(service, 'retained', side_effect=basis_only):
            service.validate_compact(self.receipt)

    def test_wrong_year_compact_cannot_enable_other_receipts(self):
        self.receipt.resolution_snapshot_json = self.compact()
        self.receipt.target_model_year = 2020
        with self.assertRaises(ValidationError):
            service.validate_compact(self.receipt)

    def make_matrix_vehicle(self, row):
        vehicle = VehicleDefinition.objects.create(generation=self.vehicle.generation,
            slug=row['target_slug'], **row['target_fields'])
        index = self.matrix['rows'].index(row)
        receipt = ImportExecutionReceipt.objects.create(pk=3221+index,
            created_vehicle_definition=vehicle, created_vehicle_definition_pk_snapshot=vehicle.pk,
            created_vehicle_definition_uuid_snapshot=str(vehicle.uuid),
            created_vehicle_definition_slug_snapshot=vehicle.slug,
            operation_type='vehicle_definition_import', execution_outcome='created',
            candidate_reference=row['candidate_reference'], resolved_generation_id=vehicle.generation_id,
            target_slug=vehicle.slug, target_fields_json=row['target_fields'],
            **{'target_'+k: row['target_fields'][k] for k in service.BASE_FIELDS},
            resolution_snapshot_json={'candidate_hash': row['candidate_digest'],
                'matrix': {'matrix_digest': service.MATRIX_DIGEST, 'row_id': row['row_id']}})
        return vehicle, receipt

    def test_high_tide_retains_its_approved_canonical_identity(self):
        row = next(r for r in self.matrix['rows'] if r['candidate_reference'] == 'JL22-20')
        vehicle, receipt = self.make_matrix_vehicle(row)
        result = self.evaluate(receipt)
        self.assertEqual(result['outcome'], 'EXACT_AGREEMENT')
        self.assertEqual(result['identity']['fields']['trim_name'], 'Unlimited High Tide')
        self.assertEqual(vehicle.slug, row['target_slug'])

    def test_erc_and_erg_do_not_collapse_into_one_displacement_match(self):
        rows = [r for r in self.matrix['rows'] if r['target_fields']['trim_name'] == 'Sport'
                and r['target_fields']['engine_cylinders'] == 6]
        self.assertEqual({r['target_fields']['electrification_type'] for r in rows}, {'none', 'mild_hybrid'})
        for row in rows:
            vehicle, receipt = self.make_matrix_vehicle(row)
            self.assertEqual(self.evaluate(receipt)['outcome'], 'EXACT_AGREEMENT')
            vehicle.electrification_type = ('mild_hybrid' if vehicle.electrification_type == 'none' else 'none')
            receipt.created_vehicle_definition = vehicle
            self.assertEqual(self.evaluate(receipt)['outcome'], 'DISAGREEMENT')

    def test_my2021_profile_cannot_be_impersonated(self):
        compact = self.compact()
        compact['version'] = 'my2021-approved-matrix-revalidation/1'
        compact['record_hash'] = service.digest({k:v for k,v in compact.items() if k != 'record_hash'})
        self.receipt.resolution_snapshot_json = compact
        with self.assertRaises(ValidationError):
            service.validate_compact(self.receipt)
