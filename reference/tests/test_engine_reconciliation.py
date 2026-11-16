import io
from decimal import Decimal

from django.core.management import call_command
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from reference.engine_reconciliation import preview_engine_assignments
from reference.models import Engine, Generation, ImportExecutionReceipt, Manufacturer, VehicleDefinition, VehicleModel
from reference.powertrain import FIELDS, engine_label, record_powertrain
from reference.services import _label_configuration_choices, get_generation_hub_context


class EngineReconciliationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maker=Manufacturer.objects.create(name='Jeep')
        model=VehicleModel.objects.create(manufacturer=cls.maker,name='Wrangler')
        cls.gen=Generation.objects.create(vehicle_model=model,name='JL',start_year=2018)
        cls.pt=dict(engine_displacement_liters=Decimal('3.6'),engine_cylinders=6,
                    engine_aspiration='naturally_aspirated',fuel_type='gasoline',electrification_type='none')
        cls.erc=Engine.objects.create(manufacturer=cls.maker,engine_code='ERC',name='3.6L V6',**cls.pt)
        cls.erg=Engine.objects.create(manufacturer=cls.maker,engine_code='ERG',name='3.6L V6 eTorque',
                                     **(cls.pt|{'electrification_type':'mild_hybrid'}))

    def vehicle(self, **kwargs):
        return VehicleDefinition.objects.create(**(dict(generation=self.gen,model_year=2021,trim_name='Sport',
            engine_name='3.6L V6',slug=f'row-{VehicleDefinition.objects.count()}')|kwargs))

    def row(self, vehicle):
        return next(r for r in preview_engine_assignments()['rows'] if r['pk']==vehicle.pk)

    def test_exact_unknowns_and_known_conflict(self):
        row=self.vehicle()
        candidate=self.row(row)
        self.assertEqual(candidate['status'],'EXACT_MATCH')
        self.assertEqual(candidate['proposed_engine']['pk'],self.erc.pk)
        self.assertEqual(set(candidate['compatibility']['fills_unknown']),set(FIELDS))
        conflict=self.vehicle(electrification_type='mild_hybrid')
        self.assertEqual(self.row(conflict)['status'],'CONFLICT')
        self.assertIsNone(self.row(conflict)['proposed_engine'])

    def test_finite_approved_ess_alias_scope_and_no_etorque_stripping(self):
        for name in ('3.6L V6 with ESS','3.6L V6 ESS'):
            row=self.vehicle(engine_name=name,electrification_type='none')
            self.assertEqual(self.row(row)['status'],'APPROVED_ALIAS_MATCH')
        unknown=self.vehicle(engine_name='3.6L V6 with ESS')
        self.assertEqual(self.row(unknown)['status'],'INSUFFICIENT_EVIDENCE')
        hybrid=self.vehicle(engine_name='3.6L V6 with eTorque',electrification_type='mild_hybrid')
        self.assertEqual(self.row(hybrid)['status'],'INSUFFICIENT_EVIDENCE')
        othergen=Generation.objects.create(vehicle_model=self.gen.vehicle_model,name='JK',start_year=2007)
        other=self.vehicle(generation=othergen,engine_name='3.6L V6 with ESS',electrification_type='none')
        self.assertEqual(self.row(other)['status'],'INSUFFICIENT_EVIDENCE')

    def test_multiple_name_candidates_never_choose_first_or_code(self):
        Engine.objects.create(manufacturer=self.maker,engine_code='SECOND',name=self.erc.name,**self.pt)
        row=self.vehicle()
        self.assertEqual(self.row(row)['status'],'AMBIGUOUS')
        self.assertIsNone(self.row(row)['proposed_engine'])

    def test_already_linked_is_retained_even_if_registry_properties_changed(self):
        row=self.vehicle(engine=self.erc)
        self.erc.fuel_type='diesel';self.erc.save()
        item=self.row(row)
        self.assertEqual(item['status'],'ALREADY_LINKED')
        self.assertEqual(item['compatibility']['result'],'CONFLICT')
        self.assertEqual(item['proposed_engine']['pk'],self.erc.pk)

    def test_no_manufacturer_registry_and_unrecognized_name(self):
        maker=Manufacturer.objects.create(name='No Registry')
        model=VehicleModel.objects.create(manufacturer=maker,name='Model')
        gen=Generation.objects.create(vehicle_model=model,name='Generation',start_year=2000)
        absent=self.vehicle(generation=gen)
        self.assertEqual(self.row(absent)['status'],'NO_REGISTERED_ENGINE')
        unknown=self.vehicle(engine_name='Unreviewed descriptor')
        self.assertEqual(self.row(unknown)['status'],'INSUFFICIENT_EVIDENCE')

    def test_explicit_receipt_binding_precedes_name_and_checks_uuid(self):
        row=self.vehicle(engine_name='Historical description')
        target=dict(engine_id=self.erc.pk)
        receipt=ImportExecutionReceipt.objects.create(created_vehicle_definition=row,
            created_vehicle_definition_uuid_snapshot=str(row.uuid),execution_outcome='created',
            resolved_generation_id=self.gen.pk,target_model_year=row.model_year,target_trim_name=row.trim_name,
            target_drivetrain=row.drivetrain,target_market=row.market,target_fields_json=target,
            resolution_snapshot_json=dict(version='my2025-edmunds-registry/1',row={'fields':target},
                plan_hash='sha256:'+'0'*64,engines={'profile':dict(id=str(self.erc.pk),uuid=str(self.erc.uuid),engine_code='ERC')}))
        self.assertEqual(self.row(row)['status'],'EXPLICIT_BINDING_MATCH')
        receipt.resolution_snapshot_json['version']='my2026-registry/2'
        receipt.save()
        self.assertEqual(self.row(row)['status'],'EXPLICIT_BINDING_MATCH')
        receipt.target_fields_json['factory_body_configuration_id']=999999
        receipt.save()
        self.assertEqual(self.row(row)['status'],'CONFLICT')
        del receipt.target_fields_json['factory_body_configuration_id']
        receipt.resolution_snapshot_json['engines']['profile']['uuid']=str(self.erg.uuid)
        receipt.save()
        self.assertEqual(self.row(row)['status'],'CONFLICT')

    def test_preview_is_deterministic_complete_and_read_only(self):
        row=self.vehicle(is_active=False,is_public=False)
        before=list(VehicleDefinition.objects.values())
        with CaptureQueriesContext(connection) as queries:
            first=preview_engine_assignments()
        self.assertEqual(first,preview_engine_assignments())
        self.assertFalse(any(q['sql'].lstrip().upper().startswith(('INSERT','UPDATE','DELETE','REPLACE','CREATE','ALTER')) for q in queries))
        self.assertEqual(list(VehicleDefinition.objects.values()),before)
        self.assertEqual(first['totals']['proposed_archived'],1)
        self.assertEqual(sum(g['total'] for g in first['groups']),1)
        out=io.StringIO();call_command('preview_engine_assignments',stdout=out)
        self.assertIn(str(row.uuid),out.getvalue())
        row.refresh_from_db();self.assertIsNone(row.engine_id)

    def test_linked_configurator_uses_registry_name_and_preserves_specs_and_stored_identity(self):
        row=self.vehicle(engine=self.erc,engine_name='3.6L V6 with ESS')
        original=(row.pk,row.uuid,row.slug,row.engine_name)
        choices=_label_configuration_choices([row])
        self.assertEqual(choices[0].choice_label,'3.6L V6')
        self.assertIn('ESS',row.engine_description)  # shared long Specs caller unchanged
        self.assertIn('ESS',engine_label(row,short=True))  # legacy API default unchanged
        self.erc.name='Owner corrected name';self.erc.save()
        fresh=VehicleDefinition.objects.select_related('engine').get(pk=row.pk)
        self.assertEqual(_label_configuration_choices([fresh])[0].choice_label,'Owner corrected name')
        row.refresh_from_db();self.assertEqual((row.pk,row.uuid,row.slug,row.engine_name),original)

    def test_unlinked_fallback_hybrid_distinction_grouping_and_selection(self):
        legacy=self.vehicle(engine_name='3.6L V6 with ESS')
        self.assertEqual(_label_configuration_choices([legacy])[0].choice_label,'3.6L V6 with ESS')
        hybrid=self.vehicle(engine=self.erg,trim_name='Other')
        linked=self.vehicle(engine=self.erc)
        context=get_generation_hub_context(self.gen,model_year='2021')
        self.assertEqual(len(context['configuration_browser_choices']),3)
        selected=get_generation_hub_context(self.gen,config_slug=hybrid.slug)
        self.assertEqual(selected['selected_config'].pk,hybrid.pk)
        choice=next(v for v in selected['configuration_browser_choices'] if v.pk==hybrid.pk)
        self.assertIn('MHEV',choice.choice_label)
        self.assertIn('eTorque',choice.choice_label)
        self.assertEqual(len(context['available_trim_groups']),2)
        foreign=Manufacturer.objects.create(name='Foreign')
        other=Engine.objects.create(manufacturer=foreign,engine_code='ERC',name='3.6L V6',**self.pt)
        linked.engine=other
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):linked.save()
