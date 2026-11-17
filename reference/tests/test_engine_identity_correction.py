"""Protected correction tests; never use the live development database."""
from copy import deepcopy
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.test import TestCase, Client
from django.urls import reverse

from reference.models import Engine, EngineIdentityCorrection, Manufacturer, VehicleDefinition, VehicleModel, Generation
from reference.engine_identity_correction import preview_correction, execute_correction, digest

PT=dict(engine_displacement_liters='2.4',engine_cylinders=4,engine_aspiration='turbocharged',fuel_type='gasoline',electrification_type='none')


class EngineIdentityCorrectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner=get_user_model().objects.create_superuser(username='correction-owner',email='',password='test')
        cls.staff=get_user_model().objects.create_user(username='no-correction-permission',is_staff=True,password='test')
        cls.maker=Manufacturer.objects.create(name='Toyota')
        cls.engine=Engine.objects.create(manufacturer=cls.maker,engine_code='T24A-FTS',name='2.4L I4 Turbo',**PT)
        cls.hybrid=Engine.objects.create(manufacturer=cls.maker,engine_code='T24A-FTS',internal_variant_key='i-force-max',name='2.4L I4 Hybrid',**(PT|{'electrification_type':'hybrid'}))
        model=VehicleModel.objects.create(manufacturer=cls.maker,name='4Runner')
        gen=Generation.objects.create(vehicle_model=model,name='Generation',start_year=2025)
        cls.vehicle=VehicleDefinition.objects.create(generation=gen,model_year=2026,trim_name='Limited',engine=cls.engine)

    def review(self, **extra):
        return preview_correction(self.engine.pk,**(dict(proposed_key='non-hybrid',reason='Reviewed correction of original authoring.',actor=self.owner)|extra))

    def execute(self, review=None, **extra):
        return execute_correction(review or self.review(),**(dict(actor=self.owner,acknowledged=True,confirmed=True)|extra))

    def test_ordinary_model_and_admin_still_immutable(self):
        engine=Engine.objects.get(pk=self.engine.pk);engine.internal_variant_key='non-hybrid'
        with self.assertRaises(ValidationError):engine.save()
        self.client.force_login(self.owner)
        page=self.client.get(reverse('admin:reference_engine_change',args=[engine.pk]))
        self.assertNotIn('internal_variant_key',page.context['adminform'].form.fields)
        self.assertContains(page,'Correct Engine Identity')

    def test_permissions_in_service_and_admin(self):
        for actor in [self.staff,None]:
            with self.assertRaises(PermissionDenied):self.review(actor=actor)
        self.client.force_login(self.staff)
        url=reverse('admin:reference_engine_correct_identity',args=[self.engine.pk])
        self.assertEqual(self.client.get(url).status_code,403)
        self.assertEqual(self.client.post(url,{'confirm':'1'}).status_code,403)
        review=self.review();self.owner.is_active=False
        with self.assertRaises(PermissionDenied):self.execute(review)

    def test_reason_acknowledgment_and_confirmation_required(self):
        for reason in ['', '  ', None]:
            with self.assertRaises(ValidationError):self.review(reason=reason)
        for kwargs in [dict(acknowledged=False),dict(confirmed=False),dict(acknowledged='yes')]:
            with self.assertRaises(ValidationError):self.execute(**kwargs)
        self.assertFalse(EngineIdentityCorrection.objects.exists())
        from django.db import connection
        with patch.object(connection.introspection,'table_names',return_value=[]):
            with self.assertRaisesMessage(ValidationError,'audit storage'):self.execute()
        self.engine.refresh_from_db();self.assertEqual(self.engine.internal_variant_key,'')

    def test_invalid_duplicate_and_unchanged_keys(self):
        for key in [None,True,'a b','é','x'*101,'i-force-max','']:
            with self.subTest(key=key),self.assertRaises(ValidationError):self.review(proposed_key=key)

    def test_review_rejects_stale_engine_vehicle_registry_and_receipt_changes(self):
        review=self.review();engine=Engine.objects.get(pk=self.engine.pk);engine.name='Edited name';engine.save()
        with self.assertRaisesMessage(ValidationError,'Stale'):self.execute(review)
        review=self.review();vehicle=VehicleDefinition.objects.get(pk=self.vehicle.pk);vehicle.notes='Changed after review';vehicle.save(update_fields=['notes'])
        with self.assertRaisesMessage(ValidationError,'Stale'):self.execute(review)
        review=self.review();self.hybrid.name='Edited hybrid';self.hybrid.save()
        with self.assertRaisesMessage(ValidationError,'Stale'):self.execute(review)
        with self.assertRaises(ValidationError):self.execute(review|{'reason':'Unreviewed change'})

    def test_success_preserves_everything_except_key_and_audits(self):
        before=list(Engine.objects.order_by('pk').values());vehicles=list(VehicleDefinition.objects.order_by('pk').values())
        review=self.review();self.assertTrue(review['impact']['eligible'])
        audit=self.execute(review)
        after=list(Engine.objects.order_by('pk').values());expected=deepcopy(before)
        next(e for e in expected if e['id']==self.engine.pk)['internal_variant_key']='non-hybrid'
        self.assertEqual(after,expected);self.assertEqual(list(VehicleDefinition.objects.order_by('pk').values()),vehicles)
        self.assertEqual(audit.before_state,review['before']);self.assertEqual(audit.after_state,review['after'])
        self.assertEqual(audit.actor,self.owner);self.assertEqual(audit.reason,review['reason'])
        self.assertEqual(str(audit.request_reference),review['request_reference']);self.assertEqual(audit.review_digest,review['review_digest'])
        self.assertEqual(audit.engine_uuid_snapshot,self.engine.uuid)
        from reference.engine_registry import resolve_engine
        self.assertEqual(resolve_engine(self.maker,'T24A-FTS',internal_variant_key='non-hybrid').pk,self.engine.pk)
        with self.assertRaises(ValidationError):resolve_engine(self.maker,'T24A-FTS',internal_variant_key='')
        with self.assertRaises(ValidationError):resolve_engine(self.maker,'T24A-FTS')
        with self.assertRaises(ValidationError):audit.save()
        with self.assertRaises(ValidationError):audit.delete()
        with self.assertRaises(ValidationError):EngineIdentityCorrection.objects.update(reason='Changed')
        # Subsequent ordinary name authoring cannot rewrite the audit snapshot.
        engine=Engine.objects.get(pk=self.engine.pk);engine.name='Later wording';engine.save()
        audit.refresh_from_db();self.assertEqual(audit.after_state['name'],review['before']['name'])

    def test_audit_failure_rolls_back_key(self):
        with patch('reference.engine_identity_correction.EngineIdentityCorrection.objects.create',side_effect=IntegrityError('Audit failure')):
            with self.assertRaises(IntegrityError):self.execute()
        self.engine.refresh_from_db();self.assertEqual(self.engine.internal_variant_key,'');self.assertFalse(EngineIdentityCorrection.objects.exists())

    def test_historical_conflict_and_mechanical_conflict_fail_closed(self):
        with patch('reference.engine_identity_correction._retained_authorizations',return_value=([],['Legacy binding cannot remain valid.'])):
            review=self.review();self.assertFalse(review['impact']['eligible'])
            with self.assertRaisesMessage(ValidationError,'Legacy binding'):self.execute(review)
        # Raw SQL here deliberately constructs an incompatible isolated fixture.
        from django.db import connection
        with connection.cursor() as c:c.execute("UPDATE reference_vehicledefinition SET electrification_type='hybrid' WHERE id=%s",[self.vehicle.pk])
        review=self.review();self.assertFalse(review['impact']['eligible'])
        with self.assertRaises(ValidationError):self.execute(review)
        self.engine.refresh_from_db();self.assertEqual(self.engine.internal_variant_key,'')

    def test_legacy_receipt_pin_blocks_correction(self):
        from reference.models import ImportExecutionReceipt
        # Reuse a complete isolated receipt factory, not a live artifact.
        receipt=ImportExecutionReceipt.objects.create(operator_label='Isolated owner',manifest_hash='sha256:'+'1'*64,
            candidate_reference='isolated',
            planned_action='create',create_basis='first_representation',source_id='test',raw_artifact_hash='sha256:'+'2'*64,
            raw_artifact_reference='test',source_identity_type='model_code',native_identifier='test',
            target_slug=self.vehicle.slug,target_model_year=2026,target_trim_name='Limited',target_engine_name=self.engine.name,
            target_drivetrain='UNK',target_market='US',target_fields_json={'engine_id':self.engine.pk},
            execution_outcome='created',resolution_snapshot_json={'version':'unknown','engine_uuid':str(self.engine.uuid)})
        review=self.review();self.assertFalse(review['impact']['eligible'])
        with self.assertRaises(ValidationError):self.execute(review)
        receipt.refresh_from_db();self.assertEqual(receipt.resolution_snapshot_json['version'],'unknown')

    def test_explicit_empty_identity_and_opaque_uuid_are_recognized(self):
        from reference.engine_identity_correction import _mentions
        self.assertTrue(_mentions({'engine_code':'T24A-FTS','internal_variant_key':''},self.engine))
        self.assertTrue(_mentions('retained reference '+str(self.engine.uuid),self.engine))
        self.assertFalse(_mentions({'engine_code':'T24A-FTS','internal_variant_key':'i-force-max'},self.engine))

    def test_missing_engine_stale_preview_and_other_actor(self):
        review=self.review()
        other=get_user_model().objects.create_superuser(username='other-owner',email='',password='test')
        with self.assertRaises(PermissionDenied):self.execute(review,actor=other)
        unused=Engine.objects.create(manufacturer=self.maker,engine_code='UNUSED',name='2.4L I4',**PT)
        review=preview_correction(unused.pk,proposed_key='reviewed',reason='Reviewed',actor=self.owner)
        unused.delete()
        with self.assertRaisesMessage(ValidationError,'Stale'):self.execute(review)
        self.assertFalse(EngineIdentityCorrection.objects.exists())

    def test_audit_is_inspectable_and_reverse_guard_preserves_history(self):
        import importlib
        from django.apps import apps
        from django.db import connection
        from django.db.migrations.exceptions import IrreversibleError
        guard=importlib.import_module('reference.migrations.0016_engine_identity_correction').preserve_correction_history
        editor=type('Editor',(),{'connection':connection})()
        guard(apps,editor)
        audit=self.execute()
        with self.assertRaises(IrreversibleError):guard(apps,editor)
        self.client.force_login(self.owner)
        response=self.client.get(reverse('admin:reference_engineidentitycorrection_change',args=[audit.pk]))
        self.assertEqual(response.status_code,200)
        self.assertContains(response,audit.reason)
        self.assertFalse(admin.site._registry[EngineIdentityCorrection].has_delete_permission(response.wsgi_request,audit))

    def test_admin_preview_confirm_csrf_and_tamper(self):
        self.client.force_login(self.owner);url=reverse('admin:reference_engine_correct_identity',args=[self.engine.pk])
        bad=self.client.post(url,{'preview':'1','proposed_key':'non-hybrid','reason':'Reviewed'})
        self.assertIsNone(bad.context['review'])
        response=self.client.post(url,{'preview':'1','proposed_key':' NON-HYBRID ','reason':'Reviewed','acknowledgment':'on'})
        self.assertEqual(response.status_code,200);token=response.context['review_token'];self.assertTrue(token)
        self.engine.refresh_from_db();self.assertEqual(self.engine.internal_variant_key,'')
        self.assertContains(response,'Confirm Engine identity correction')
        rejected=self.client.post(url,{'confirm':'1','review_token':token+'bad','acknowledgment':'on'})
        self.assertEqual(rejected.status_code,200);self.assertFalse(EngineIdentityCorrection.objects.exists())
        rejected=self.client.post(url,{'confirm':'1','review_token':token})
        self.assertEqual(rejected.status_code,200);self.assertFalse(EngineIdentityCorrection.objects.exists())
        protected=Client(enforce_csrf_checks=True);protected.force_login(self.owner)
        self.assertEqual(protected.post(url,{'confirm':'1','review_token':token,'acknowledgment':'on'}).status_code,403)
        response=self.client.post(url,{'confirm':'1','review_token':token,'acknowledgment':'on'})
        self.assertEqual(response.status_code,302);self.engine.refresh_from_db();self.assertEqual(self.engine.internal_variant_key,'non-hybrid')

    def test_submillisecond_state_change_rejects_preview(self):
        from datetime import datetime, timezone
        from django.db import connection
        from reference.engine_identity_correction import wire
        first = datetime(2026, 11, 17, 12, 0, 0, 123001, tzinfo=timezone.utc)
        second = first.replace(microsecond=123002)
        self.assertNotEqual(digest({'timestamp': first}), digest({'timestamp': second}))
        self.assertEqual(wire(first), first.isoformat())
        with connection.cursor() as cursor:
            cursor.execute('UPDATE reference_engine SET updated_at=%s WHERE id=%s', [first, self.engine.pk])
        review = self.review()
        with connection.cursor() as cursor:
            cursor.execute('UPDATE reference_engine SET updated_at=%s WHERE id=%s', [second, self.engine.pk])
        with self.assertRaisesMessage(ValidationError, 'Stale'):
            self.execute(review)
        self.engine.refresh_from_db()
        self.assertEqual(self.engine.internal_variant_key, '')
        self.assertFalse(EngineIdentityCorrection.objects.exists())

    def test_admin_confirmation_is_bound_to_engine_url(self):
        from django.core import signing
        self.client.force_login(self.owner)
        token = signing.dumps(self.review(), salt='engine-identity-correction')
        response = self.client.post(reverse('admin:reference_engine_correct_identity', args=[self.hybrid.pk]),
                                    {'confirm': '1', 'review_token': token, 'acknowledgment': 'on'})
        self.assertContains(response, 'different Engine')
        self.engine.refresh_from_db(); self.hybrid.refresh_from_db()
        self.assertEqual(self.engine.internal_variant_key, '')
        self.assertEqual(self.hybrid.internal_variant_key, 'i-force-max')
        self.assertFalse(EngineIdentityCorrection.objects.exists())

    def test_admin_expired_preview_is_rejected(self):
        from django.core import signing
        self.client.force_login(self.owner)
        with patch('django.core.signing.time.time', return_value=0):
            token = signing.dumps(self.review(), salt='engine-identity-correction')
        response = self.client.post(reverse('admin:reference_engine_correct_identity', args=[self.engine.pk]),
                                    {'confirm': '1', 'review_token': token, 'acknowledgment': 'on'})
        self.assertContains(response, 'Correction not executed')
        self.assertFalse(EngineIdentityCorrection.objects.exists())
        self.engine.refresh_from_db(); self.assertEqual(self.engine.internal_variant_key, '')

    def test_change_permission_alone_cannot_correct_identity(self):
        from django.contrib.auth.models import Permission
        self.staff.user_permissions.add(Permission.objects.get(codename='change_engine'))
        staff = get_user_model().objects.get(pk=self.staff.pk)
        with self.assertRaises(PermissionDenied):
            self.review(actor=staff)
        self.client.force_login(staff)
        url = reverse('admin:reference_engine_correct_identity', args=[self.engine.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename='correct_engine_identity'))
        staff = get_user_model().objects.get(pk=staff.pk)
        self.assertTrue(self.review(actor=staff)['impact']['eligible'])
