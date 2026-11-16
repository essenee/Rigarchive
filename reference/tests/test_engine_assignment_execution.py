from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
from unittest.mock import patch
import uuid

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from reference import engine_assignment as service
from reference.engine_reconciliation import preview_engine_assignments
from reference.models import Engine, Generation, Manufacturer, VehicleDefinition, VehicleModel
from reference.services import _label_configuration_choices


class ApprovedEngineAssignmentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        maker = Manufacturer.objects.create(name='Jeep')
        model = VehicleModel.objects.create(manufacturer=maker, name='Wrangler')
        cls.generation = Generation.objects.create(vehicle_model=model, name='JL', start_year=2018)
        cls.properties = dict(engine_displacement_liters=Decimal('3.6'), engine_cylinders=6,
                              engine_aspiration='naturally_aspirated', fuel_type='gasoline',
                              electrification_type='none')
        cls.engine = Engine.objects.create(manufacturer=maker, engine_code='ERC', name='3.6L V6', **cls.properties)

    def vehicle(self, **extra):
        return VehicleDefinition.objects.create(**(dict(generation=self.generation, model_year=2022,
            trim_name='Sport', engine_name='3.6L V6', slug=f'preserved-{VehicleDefinition.objects.count()}') | extra))

    @contextmanager
    def approved(self):
        """The production command pins the real artifact; tests approve isolated fixtures."""
        plan = preview_engine_assignments()
        counts = {k: v for k, v in plan['totals']['statuses'].items() if k in service.MATCHES}
        with patch.object(service, 'APPROVED_DIGEST', plan['snapshot_digest']), patch.object(service, 'APPROVED_COUNTS', counts):
            yield plan

    def test_exact_alias_completion_and_full_field_preservation(self):
        exact = self.vehicle(base_msrp=12345, is_public=False)
        alias = self.vehicle(engine_name='3.6L V6 ESS', electrification_type='none', is_active=False)
        excluded = self.vehicle(engine_name='3.6L V6 with ESS', electrification_type='mild_hybrid')
        before = service.canonical_state()
        with self.approved() as plan:
            receipt = service.execute_assignments(plan, baseline=before)
        self.assertEqual(receipt['assigned'], 2)
        self.assertEqual(receipt['assignments_by_method'], {'EXACT_MATCH': 1, 'APPROVED_ALIAS_MATCH': 1})
        self.assertEqual(receipt['unknown_attributes_completed']['electrification_type'], 1)
        self.assertEqual(receipt['unknown_attributes_completed']['engine_cylinders'], 2)
        self.assertTrue(receipt['identities_and_unrelated_fields_preserved'])
        exact.refresh_from_db(); alias.refresh_from_db(); excluded.refresh_from_db()
        self.assertEqual(exact.engine_id, self.engine.pk)
        self.assertEqual(alias.engine_id, self.engine.pk)
        self.assertIsNone(excluded.engine_id)
        self.assertEqual(alias.engine_name, '3.6L V6 ESS')
        self.assertEqual(alias.slug, 'preserved-1')
        self.assertEqual(_label_configuration_choices([alias])[0].choice_label, '3.6L V6')
        self.assertEqual(before['engines'], service.canonical_state()['engines'])

    def test_alias_with_ess_spelling_and_hybrid_distinction(self):
        alias = self.vehicle(engine_name='3.6L V6 with ESS', electrification_type='none')
        hybrid = Engine.objects.create(manufacturer=self.engine.manufacturer, engine_code='ERG',
            name='3.6L V6 eTorque', **(self.properties | {'electrification_type': 'mild_hybrid'}))
        linked = self.vehicle(engine=hybrid, engine_name=hybrid.name)
        with self.approved() as plan:
            self.assertEqual(service.execute_assignments(plan)['assigned'], 1)
        linked.refresh_from_db(); alias.refresh_from_db()
        self.assertIn('MHEV', _label_configuration_choices([linked])[0].choice_label)
        self.assertEqual(alias.engine_id, self.engine.pk)

    def test_ambiguous_known_conflicts_and_unrecognized_records_never_selected(self):
        good = self.vehicle()
        conflict = self.vehicle(electrification_type='mild_hybrid')
        unknown = self.vehicle(engine_name='Unknown')
        other = Engine.objects.create(manufacturer=self.engine.manufacturer, engine_code='OTHER', name='Ambiguous', **self.properties)
        Engine.objects.create(manufacturer=self.engine.manufacturer, engine_code='OTHER2', name=other.name, **self.properties)
        ambiguous = self.vehicle(engine_name=other.name)
        with self.approved() as plan:
            self.assertEqual(service.execute_assignments(plan)['assigned'], 1)
        for vehicle in (conflict, unknown, ambiguous):
            vehicle.refresh_from_db(); self.assertIsNone(vehicle.engine_id)
        good.refresh_from_db(); self.assertEqual(good.engine_id, self.engine.pk)

    def test_stale_vehicle_and_uuid_rejected_without_writes(self):
        row = self.vehicle()
        with self.approved() as plan:
            row.trim_name = 'Changed'; row.save()
            before = service.canonical_state()
            with self.assertRaisesMessage(ValidationError, 'stale proposal'):
                service.execute_assignments(plan)
            self.assertEqual(before, service.canonical_state())

    def test_stale_engine_properties_and_name_rejected(self):
        self.vehicle()
        with self.approved() as plan:
            self.engine.name = 'Changed'; self.engine.save()
            before = service.canonical_state()
            with self.assertRaisesMessage(ValidationError, 'Stale Engine registry'):
                service.execute_assignments(plan)
            self.assertEqual(before, service.canonical_state())

    def test_changed_vehicle_uuid_or_missing_vehicle_rejected(self):
        row = self.vehicle()
        with self.approved() as plan:
            VehicleDefinition.objects.filter(pk=row.pk).update(uuid=uuid.uuid4())
            with self.assertRaisesMessage(ValidationError, 'UUID changed'):
                service.execute_assignments(plan)
            row.delete()
            with self.assertRaisesMessage(ValidationError, 'missing'):
                service.execute_assignments(plan)

    def test_changed_engine_uuid_rejected(self):
        self.vehicle()
        with self.approved() as plan:
            # Simulate corrupt/external state in the isolated test DB. Normal
            # Engine saves correctly prohibit this identity mutation themselves.
            with connection.cursor() as cursor:
                cursor.execute('UPDATE reference_engine SET uuid = %s WHERE id = %s',
                               [uuid.uuid4().hex, self.engine.pk])
            with self.assertRaisesMessage(ValidationError, 'Stale Engine registry'):
                service.execute_assignments(plan)

    def test_missing_engine_rejected(self):
        self.vehicle()
        with self.approved() as plan:
            self.engine.delete()
            with self.assertRaisesMessage(ValidationError, 'Stale Engine registry'):
                service.execute_assignments(plan)
        self.assertEqual(VehicleDefinition.objects.filter(engine__isnull=True).count(), 1)

    def test_material_engine_change_even_with_same_pk_rejected(self):
        self.vehicle()
        with self.approved() as plan:
            self.engine.electrification_type = 'mild_hybrid'; self.engine.save()
            with self.assertRaises(ValidationError): service.execute_assignments(plan)

    def test_altered_unapproved_plan_and_engine_substitution_rejected(self):
        self.vehicle()
        with self.approved() as plan:
            altered = deepcopy(plan)
            altered['rows'][0]['proposed_engine']['pk'] = 999999
            with self.assertRaisesMessage(ValidationError, 'altered'):
                service.execute_assignments(altered)

    def test_safe_rerun_has_no_update_sql_or_metadata_changes(self):
        self.vehicle()
        with self.approved() as plan:
            service.execute_assignments(plan)
            before = service.canonical_state()
            with CaptureQueriesContext(connection) as queries:
                result = service.execute_assignments(plan)
            self.assertEqual(result['assigned'], 0)
            self.assertEqual(result['skipped_already_applied'], 1)
            self.assertEqual(before, service.canonical_state())
            self.assertFalse(any(q['sql'].lstrip().upper().startswith(('UPDATE', 'INSERT', 'DELETE')) for q in queries))

    def test_conflicting_existing_association_on_rerun_is_not_skipped(self):
        row = self.vehicle()
        with self.approved() as plan:
            service.execute_assignments(plan)
            other = Engine.objects.create(manufacturer=self.engine.manufacturer, engine_code='SECOND', name='Other', **self.properties)
            row.refresh_from_db(); row.engine = other; row.save()
            with self.assertRaises(ValidationError): service.execute_assignments(plan)

    def test_backup_baseline_drift_rejected(self):
        row = self.vehicle()
        with self.approved() as plan:
            baseline = service.canonical_state()
            row.is_public = False; row.save()
            with self.assertRaisesMessage(ValidationError, 'verified backup'):
                service.execute_assignments(plan, baseline=baseline)

    def test_atomic_rollback_after_second_model_save_failure(self):
        self.vehicle(); self.vehicle(trim_name='Other')
        with self.approved() as plan:
            before = service.canonical_state()
            original = VehicleDefinition.save
            calls = []
            def fail_second(instance, *args, **kwargs):
                calls.append(instance.pk)
                if len(calls) == 2:
                    raise ValidationError('Injected failure')
                return original(instance, *args, **kwargs)
            with patch.object(VehicleDefinition, 'save', fail_second):
                with self.assertRaisesMessage(ValidationError, 'Injected failure'):
                    service.execute_assignments(plan)
            self.assertEqual(before, service.canonical_state())

    def test_preservation_guard_rolls_back_unrelated_field_mutation(self):
        self.vehicle()
        with self.approved() as plan:
            before = service.canonical_state()
            original = VehicleDefinition.save
            def incorrect_save(instance, *args, **kwargs):
                result = original(instance, *args, **kwargs)
                VehicleDefinition.objects.filter(pk=instance.pk).update(is_public=False)
                return result
            with patch.object(VehicleDefinition, 'save', incorrect_save):
                with self.assertRaisesMessage(ValidationError, 'unauthorized field'):
                    service.execute_assignments(plan)
            self.assertEqual(before, service.canonical_state())

    def test_command_rejects_nonlocal_database_execution(self):
        with patch('reference.management.commands.assign_registered_engines.validate_assignments', return_value=([], [])):
            with self.assertRaisesMessage(CommandError, 'local development'):
                call_command('assign_registered_engines', execute=True)
