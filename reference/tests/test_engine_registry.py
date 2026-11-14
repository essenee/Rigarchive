"""Human Engine registry: isolated records only; no research or publication."""
from decimal import Decimal
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction, connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase, RequestFactory
from django.urls import reverse

from reference.engine_registry import resolve_engine, prepare_registered_vehicle, EngineRegistryError
from reference.models import Engine, Manufacturer, VehicleModel, Generation, VehicleDefinition
from reference.powertrain import FIELDS, record_powertrain

PT = dict(engine_displacement_liters='2', engine_cylinders=4, engine_aspiration='turbocharged',
          fuel_type='gasoline', electrification_type='none')


class EngineRegistryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maker = Manufacturer.objects.create(name='Registry Jeep')
        cls.other = Manufacturer.objects.create(name='Other Maker')
        model = VehicleModel.objects.create(manufacturer=cls.maker, name='Wrangler')
        cls.generation = Generation.objects.create(vehicle_model=model, name='JL', start_year=2018)
        cls.engine = Engine.objects.create(manufacturer=cls.maker, engine_code=' ec1 ', name='2.0L I4 Turbo', **PT)

    def vehicle(self, **kwargs):
        defaults=dict(generation=self.generation, model_year=2024,trim_name='Sport')
        defaults.update(kwargs)
        return VehicleDefinition(**defaults)

    def test_creation_normalized_unique_and_standard_identity(self):
        self.assertEqual(self.engine.engine_code,'EC1')
        self.assertTrue(self.engine.uuid)
        self.assertTrue(self.engine.created_at)
        with self.assertRaises(ValidationError):
            Engine.objects.create(manufacturer=self.maker,engine_code=' eC1 ', name='Duplicate',**PT)

    def test_full_clean_bound_code_constraint_and_persistence(self):
        for supplied, normalized in (("ERC", "ERC"), ("  ea888-cjxc  ", "EA888-CJXC")):
            with self.subTest(code=supplied):
                engine = Engine(manufacturer=self.maker, engine_code=supplied,
                                name="Validated engine", **PT)
                engine.full_clean()
                self.assertIsNone(engine.pk)
                self.assertEqual(engine.engine_code, normalized)
                engine.save()
                engine.refresh_from_db()
                self.assertEqual(engine.engine_code, normalized)
                duplicate = Engine(manufacturer=self.maker, engine_code=supplied.lower(),
                                   name="Duplicate", **PT)
                with self.assertRaises(ValidationError):
                    duplicate.full_clean()

    def test_code_constraint_preserves_applied_migration_sql_and_identity(self):
        executor = MigrationExecutor(connection)
        historical = executor.loader.project_state(
            [("reference", "0012_engine_registry")]
        ).apps.get_model("reference", "Engine")
        current = next(c for c in Engine._meta.constraints
                       if c.name == "reference_engine_code_normalized")
        previous = next(c for c in historical._meta.constraints
                        if c.name == current.name)
        self.assertEqual(current, previous)
        editor = connection.schema_editor(collect_sql=True)
        self.assertEqual(current.constraint_sql(Engine, editor),
                         previous.constraint_sql(historical, editor))

    def test_code_constraint_rejects_invalid_bound_values(self):
        constraint = next(c for c in Engine._meta.constraints
                          if c.name == "reference_engine_code_normalized")
        for code in ("", "ec2", " EC2", "EC2 ", "EC/2", "ÉC2", "-EC2"):
            with self.subTest(code=code):
                engine = Engine(manufacturer=self.maker, engine_code=code,
                                name="Invalid", **PT)
                with self.assertRaises(ValidationError):
                    constraint.validate(Engine, engine)
                if code not in ("ec2", " EC2", "EC2 "):
                    with self.assertRaises(ValidationError):
                        engine.full_clean()
                with self.assertRaises(IntegrityError), transaction.atomic():
                    engine.save_base(raw=True)

    def test_code_scoped_to_manufacturer(self):
        other=Engine.objects.create(manufacturer=self.other,engine_code='EC1',name='Different maker',**PT)
        self.assertEqual(resolve_engine(self.other,'ec1'),other)
        self.assertEqual(resolve_engine(self.maker,'ec1'),self.engine)

    def test_hyphenated_volkswagen_variants_coexist_with_exact_lookup(self):
        volkswagen=Manufacturer.objects.create(name='Volkswagen')
        engines={code: Engine.objects.create(manufacturer=volkswagen, engine_code=code,
                    name='2.0L I4 Turbo', **PT) for code in ('EA888-CJXC','EA888-CHHB')}
        self.assertNotEqual(engines['EA888-CJXC'].pk, engines['EA888-CHHB'].pk)
        for code,engine in engines.items():
            self.assertEqual(resolve_engine(volkswagen,code),engine)
        for partial in ('EA888','EA888-CJX','EA888CJXC'):
            with self.assertRaises(EngineRegistryError) as caught:resolve_engine(volkswagen,partial)
            self.assertEqual(caught.exception.code,'ENGINE_NOT_REGISTERED')
        self.assertEqual(Engine.objects.filter(manufacturer=volkswagen).count(),2)

    def test_full_code_normalization_preserves_hyphens_and_suffix(self):
        volkswagen=Manufacturer.objects.create(name='Volkswagen')
        engine=Engine.objects.create(manufacturer=volkswagen,engine_code='  ea888-cjxc  ',name='2.0L I4 Turbo',**PT)
        engine.refresh_from_db()
        self.assertEqual(engine.engine_code,'EA888-CJXC')
        self.assertEqual(resolve_engine(volkswagen,' ea888-CjXc '),engine)
        with self.assertRaises(ValidationError):
            Engine.objects.create(manufacturer=volkswagen,engine_code=' Ea888-CJXC ',name='Duplicate',**PT)
        for code in ('','  ','EA888/CJXC','EA888 CJXC','EA888–CJXC'):
            with self.assertRaises(ValidationError):
                Engine.objects.create(manufacturer=volkswagen,engine_code=code,name='Invalid',**PT)

    def test_full_code_reused_across_models_and_years(self):
        volkswagen=Manufacturer.objects.create(name='Volkswagen')
        engine=Engine.objects.create(manufacturer=volkswagen,engine_code='EA888-CJXC',name='2.0L I4 Turbo',**PT)
        for model_name,year in (('Golf',2020),('Other model',2024)):
            model=VehicleModel.objects.create(manufacturer=volkswagen,name=model_name)
            generation=Generation.objects.create(vehicle_model=model,name='Generation',start_year=2010)
            vehicle=prepare_registered_vehicle(volkswagen,' ea888-cjxc ',generation=generation,model_year=year,trim_name='Test')
            vehicle.save()
            self.assertEqual(vehicle.engine_id,engine.pk)
            self.assertEqual(record_powertrain(vehicle),PT)
        self.assertEqual(Engine.objects.filter(manufacturer=volkswagen).count(),1)

    def test_seven_existing_jeep_codes_keep_exact_lookup(self):
        import json
        from pathlib import Path
        proposal=json.loads((Path(__file__).resolve().parents[2]/'docs/implementation/handoffs/engine_registry_20261114/wrangler_engine_seed_proposal.json').read_text())
        self.assertEqual({row['engine_code'] for row in proposal['proposals']},{'ERC','EC1','ESG','EC3','ERG','ECX','EXJ'})
        for row in proposal['proposals']:
            if row['engine_code']=='EC1':engine=self.engine
            else:engine=Engine.objects.create(manufacturer=self.maker,engine_code=row['engine_code'],name=row['proposed_name'],**row['parameters'])
            self.assertEqual(resolve_engine(self.maker,' '+row['engine_code'].lower()+' '),engine)
            self.assertEqual(record_powertrain(engine),row['parameters'])

    def test_identity_immutable(self):
        for field,value in [('engine_code','EC3'),('manufacturer',self.other),('uuid',self.other.uuid)]:
            obj=Engine.objects.get(pk=self.engine.pk)
            setattr(obj,field,value)
            with self.assertRaises(ValidationError):obj.save()
        self.engine.refresh_from_db()
        self.assertEqual(self.engine.engine_code,'EC1')

    def test_properties_human_editable_without_vehicle_cascade(self):
        vehicle=self.vehicle(engine=self.engine);vehicle.save();slug=vehicle.slug
        self.engine.name='Corrected description';self.engine.fuel_type='diesel';self.engine.save()
        vehicle.refresh_from_db();vehicle.notes='Existing snapshot';vehicle.save(update_fields=['notes'])
        self.assertEqual(vehicle.fuel_type,'gasoline')
        self.assertEqual(vehicle.slug,slug)
        self.assertEqual(resolve_engine(self.maker,'EC1').fuel_type,'diesel')

    def test_invalid_codes_and_powertrain_rejected(self):
        for name in (None, '', '   '):
            with self.assertRaises(ValidationError):Engine.objects.create(manufacturer=self.maker,engine_code='INVALID',name=name,**PT)
        for code in ['', ' ', 'EC 1','ÉC1','EC1\nBAD']:
            with self.assertRaises(ValidationError):Engine.objects.create(manufacturer=self.maker,engine_code=code,name='Invalid',**PT)
        for key,value in [('engine_cylinders',True),('fuel_type','water'),('engine_displacement_liters','-1')]:
            with self.assertRaises(ValidationError):Engine.objects.create(manufacturer=self.maker,engine_code='TEST',name='Invalid',**(PT|{key:value}))

    def test_missing_engine_fk_and_boolean_snapshot_fail_validation(self):
        with self.assertRaises(ValidationError):self.vehicle(engine_id=999999).save()
        with self.assertRaises(ValidationError):self.vehicle(engine=self.engine,engine_cylinders=True).save()

    def test_exact_existing_tracked_field_definitions(self):
        for key in FIELDS:
            a=Engine._meta.get_field(key).deconstruct();b=VehicleDefinition._meta.get_field(key).deconstruct()
            self.assertEqual(a[1:],b[1:])

    def test_database_constraints_protect_normalized_identity(self):
        for code,values in [('EC1',PT),('ec2',PT),('EC2\n',PT),('EC2',PT|{'fuel_type':'water'})]:
            obj=Engine(manufacturer=self.maker,engine_code=code,name='Bypass',**values)
            with self.assertRaises(IntegrityError), transaction.atomic():obj.save_base(raw=True)

    def test_existing_matching_snapshot_can_receive_fk_without_identity_changes(self):
        vehicle=self.vehicle(engine_name='2.0L I4 Published alias',**PT);vehicle.save()
        original=(vehicle.pk,vehicle.uuid,vehicle.slug,vehicle.engine_name)
        vehicle.engine=self.engine;vehicle.save(update_fields=['engine'])
        vehicle.refresh_from_db()
        self.assertEqual((vehicle.pk,vehicle.uuid,vehicle.slug,vehicle.engine_name),original)

    def test_protected_manufacturer_and_engine(self):
        with self.assertRaises(ProtectedError):self.maker.delete()
        self.vehicle(engine=self.engine).save()
        with self.assertRaises(ProtectedError):self.engine.delete()

    def test_unknown_code_blocks_without_creation(self):
        count=Engine.objects.count()
        with self.assertRaises(EngineRegistryError) as caught:resolve_engine(self.maker,'UNKNOWN')
        self.assertEqual(caught.exception.code,'ENGINE_NOT_REGISTERED')
        self.assertEqual(Engine.objects.count(),count)

    def test_registry_conflict_preserves_registered_properties(self):
        with self.assertRaises(EngineRegistryError) as caught:resolve_engine(self.maker,'EC1',incoming_powertrain={'fuel_type':'diesel'})
        self.assertEqual(caught.exception.code,'ENGINE_REGISTRY_CONFLICT')
        self.engine.refresh_from_db();self.assertEqual(self.engine.fuel_type,'gasoline')

    def test_known_code_reuses_properties_without_external_evidence(self):
        self.assertEqual(resolve_engine(self.maker,' ec1 ',incoming_powertrain={'fuel_type':None}),self.engine)
        self.assertEqual(record_powertrain(self.engine),PT)
        self.assertEqual(Engine.objects.count(),1)

    def test_incomplete_registry_does_not_guess(self):
        Engine.objects.create(manufacturer=self.maker,engine_code='PENDING',name='Not complete')
        with self.assertRaises(EngineRegistryError) as caught:resolve_engine(self.maker,'PENDING')
        self.assertEqual(caught.exception.code,'ENGINE_REGISTRY_INCOMPLETE')

    def test_unsaved_construction_uses_registry_and_checks_manufacturer(self):
        vehicle=prepare_registered_vehicle(self.maker,'EC1',generation=self.generation,model_year=2024,trim_name='Sport')
        self.assertIsNone(vehicle.pk)
        self.assertEqual(VehicleDefinition.objects.count(),0)
        self.assertEqual(record_powertrain(vehicle),PT)
        vehicle.save();self.assertEqual(vehicle.engine_id,self.engine.pk)
        wrong=Engine.objects.create(manufacturer=self.other,engine_code='EC1',name='Wrong maker',**PT)
        with self.assertRaises(ValidationError):self.vehicle(engine=wrong).save()

    def test_constructor_conflicts_not_hidden_by_multiple_input_dictionaries(self):
        with self.assertRaises(EngineRegistryError):prepare_registered_vehicle(self.maker,'EC1',incoming_powertrain={'fuel_type':'gasoline'},fuel_type='diesel',generation=self.generation)
        with self.assertRaises(ValidationError) as caught:self.vehicle(engine=self.engine,fuel_type='diesel').save()
        self.assertEqual(caught.exception.error_dict['fuel_type'][0].code,'ENGINE_REGISTRY_CONFLICT')

    def test_legacy_vehicle_remains_nullable_and_slug_stable(self):
        vehicle=self.vehicle(engine_name='Historical engine');vehicle.save();slug=vehicle.slug
        vehicle.trim_name='Corrected description';vehicle.save()
        self.assertIsNone(vehicle.engine_id);self.assertEqual(vehicle.slug,slug)

    def test_partial_saves_validate_effective_persisted_values(self):
        vehicle=self.vehicle(engine=self.engine);vehicle.save()
        vehicle.fuel_type='diesel';vehicle.notes='Safe';vehicle.save(update_fields=iter(['notes']))
        vehicle.refresh_from_db();self.assertEqual(vehicle.fuel_type,'gasoline')
        vehicle.fuel_type='diesel'
        with self.assertRaises(ValidationError):vehicle.save(update_fields=['fuel_type'])
        vehicle.refresh_from_db();self.assertEqual(vehicle.fuel_type,'gasoline')

    def test_partial_engine_assignment_cannot_validate_omitted_snapshot(self):
        vehicle=self.vehicle(engine_name='Legacy',fuel_type='diesel');vehicle.save()
        vehicle.engine=self.engine
        for k,v in PT.items():setattr(vehicle,k,v)
        with self.assertRaises(ValidationError):vehicle.save(update_fields=['engine'])
        vehicle.refresh_from_db();self.assertIsNone(vehicle.engine_id)

    def test_partial_generation_change_cannot_bypass_manufacturer(self):
        other_model=VehicleModel.objects.create(manufacturer=self.other,name='Other')
        generation=Generation.objects.create(vehicle_model=other_model,name='Other',start_year=2018)
        vehicle=self.vehicle(engine=self.engine);vehicle.save();vehicle.generation=generation
        with self.assertRaises(ValidationError):vehicle.save(update_fields=['generation'])

    def test_supported_bulk_paths_do_not_bypass_validation(self):
        for action in [lambda:Engine.objects.filter(pk=self.engine.pk).update(engine_code='NEW'),
                       lambda:Engine.objects.bulk_create([Engine(manufacturer=self.maker,engine_code='NEW',name='New')]),
                       lambda:Engine.objects.bulk_update([self.engine],['name']),
                       lambda:VehicleDefinition.objects.bulk_create([self.vehicle(engine=self.engine)])]:
            with self.assertRaises(ValidationError):action()
        legacy=self.vehicle();legacy.save()
        with self.assertRaises(ValidationError):VehicleDefinition.objects.filter(pk=legacy.pk).update(engine=self.engine)
        associated=self.vehicle(engine=self.engine,trim_name='Sport S');associated.save()
        with self.assertRaises(ValidationError):VehicleDefinition.objects.filter(pk=associated.pk).update(fuel_type='diesel')
        with self.assertRaises(ValidationError):VehicleDefinition.objects.bulk_create([self.vehicle()],update_conflicts=True,update_fields=['fuel_type'],unique_fields=['generation','slug'])

    def test_engine_admin_identity_readonly_and_permissions(self):
        registered=admin.site._registry[Engine];request=RequestFactory().get('/')
        self.assertIn('engine_code',registered.get_readonly_fields(request,self.engine))
        self.assertNotIn('engine_code',registered.get_readonly_fields(request))
        url=reverse('admin:reference_engine_add');self.assertEqual(self.client.get(url).status_code,302)
        owner=get_user_model().objects.create_superuser(username='engine-owner',email='engine@example.com',password='pass')
        self.client.force_login(owner)
        response=self.client.post(url,{'manufacturer':self.maker.pk,'engine_code':'erc','name':'3.6L V6 ESS',**(PT|{'engine_displacement_liters':'3.6','engine_cylinders':6,'engine_aspiration':'naturally_aspirated'}),'_save':'Save'})
        self.assertEqual(response.status_code,302)
        self.assertTrue(Engine.objects.filter(engine_code='ERC').exists())
        from django.contrib.admin.models import LogEntry
        self.assertTrue(LogEntry.objects.filter(object_id=str(Engine.objects.get(engine_code='ERC').pk)).exists())

    def test_ra049_contracts_cannot_silently_carry_registry_identity(self):
        from reference import candidate_v3 as wire
        from pathlib import Path
        import json
        candidate=json.loads((Path(__file__).parent/'fixtures/ingestion/candidate_v3/B.json').read_text())
        candidate['engine_uuid']=str(self.engine.uuid);candidate['candidate_hash']=wire.candidate_hash(candidate)
        with self.assertRaises(wire.CandidateV3Error):wire.parse_candidate(candidate)
        from reference.ingestion import body_import_contracts as contracts
        # Schema remains closed; no speculative registry member is accepted.
        with self.assertRaises(ValidationError):contracts.validate('TargetFields',{'engine_uuid':str(self.engine.uuid)})


class EngineMigrationPreservationTests(TransactionTestCase):
    def test_plain_sqlite_snapshot_preserves_populated_registry(self):
        import sqlite3
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.core.management import call_command
        maker=Manufacturer.objects.create(name='Snapshot Engine Maker')
        engine=Engine.objects.create(manufacturer=maker,engine_code='EC1',name='2.0L I4',**PT)
        with TemporaryDirectory() as directory:
            path=Path(directory)/'snapshot.sqlite3'
            call_command('snapshot_db',output=str(path),verbosity=0)
            with sqlite3.connect(path) as snapshot:
                self.assertEqual(snapshot.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                self.assertEqual(snapshot.execute('SELECT engine_code FROM reference_engine WHERE id=?',(engine.pk,)).fetchone()[0],'EC1')


    def test_additive_migration_preserves_all_old_table_columns(self):
        executor=MigrationExecutor(connection);latest=executor.loader.graph.leaf_nodes()
        old=[('reference','0011_factory_body_configuration')]
        try:
            executor.migrate(old);apps=executor.loader.project_state(old).apps
            Maker=apps.get_model('reference','Manufacturer');Model=apps.get_model('reference','VehicleModel');Gen=apps.get_model('reference','Generation');Vehicle=apps.get_model('reference','VehicleDefinition')
            maker=Maker.objects.create(name='Preserved Engine Maker',slug='preserved-engine-maker')
            model=Model.objects.create(manufacturer=maker,name='Model',slug='model')
            generation=Gen.objects.create(vehicle_model=model,name='Generation',slug='generation',start_year=2020)
            vehicle=Vehicle.objects.create(generation=generation,model_year=2024,trim_name='Historical',engine_name='Historic engine',slug='historical-engine')
            snapshot={}
            with connection.cursor() as cursor:
                for table in connection.introspection.table_names():
                    if table=='django_migrations' or table.startswith('sqlite_'):continue
                    columns=[c.name for c in connection.introspection.get_table_description(cursor,table)]
                    quoted=','.join(connection.ops.quote_name(c) for c in columns)
                    cursor.execute(f'SELECT {quoted} FROM {connection.ops.quote_name(table)} ORDER BY 1')
                    snapshot[table]=(quoted,cursor.fetchall())
            executor=MigrationExecutor(connection);executor.migrate([('reference','0012_engine_registry')])
            with connection.cursor() as cursor:
                for table,(columns,rows) in snapshot.items():
                    cursor.execute(f'SELECT {columns} FROM {connection.ops.quote_name(table)} ORDER BY 1')
                    self.assertEqual(cursor.fetchall(),rows,table)
            apps=executor.loader.project_state([('reference','0012_engine_registry')]).apps
            self.assertIsNone(apps.get_model('reference','VehicleDefinition').objects.get(pk=vehicle.pk).engine_id)
            self.assertEqual(apps.get_model('reference','Engine').objects.count(),0)
        finally:
            MigrationExecutor(connection).migrate(latest)
