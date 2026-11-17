"""Registry-aware 3.1.0 envelope; original 3.0.0 path remains an independent reader."""
from copy import deepcopy
from unittest.mock import patch
import json
from django.test import TestCase
from django.core.exceptions import ValidationError
from reference.models import Engine, VehicleDefinition, ImportExecutionReceipt
from reference.engine_registry import EngineRegistryError
from reference.ingestion.importing import registry_body_import as r
from reference.ingestion.importing.body_import import build_matrix, build_manifest, execute_body_import_batch
from reference.ingestion.matrix_approval import build_matrix_approval
from reference.ingestion.manifest import dict_to_manifest, manifest_to_dict
from reference.ingestion.importing.planner import plan_candidate_import
from reference.tests.body_import_support import BodyImportFixture


class RegistryBodyImportTests(TestCase):
    def setUp(self):
        self.fx=BodyImportFixture(registry=True)
        self.addCleanup(self.fx.close)

    def authorize(self,plans):
        matrix=build_matrix(plans)
        approval=build_matrix_approval(matrix,operator='project-owner',confirmed=True)
        return build_manifest(matrix,approval)

    def execute(self,plans,manifest=None,**kwargs):
        return execute_body_import_batch(manifest or self.authorize(plans),plans,self.fx.release,
            operator='project-owner',execution_agent='implementation-agent',confirmed=True,**kwargs)

    def test_published_exact_binding_survives_another_same_code_variant(self):
        wrapped = self.fx.candidates['JL24-01']
        bound = Engine.objects.get(pk=wrapped['binding']['engine']['pk'])
        from reference.powertrain import record_powertrain
        Engine.objects.create(manufacturer=bound.manufacturer, engine_code=bound.engine_code,
                              internal_variant_key='reviewed-other', name=bound.name, **record_powertrain(bound))
        plan = plan_candidate_import(wrapped, body_release=self.fx.release)
        self.assertEqual(r.subject(plan)['binding'], wrapped['binding'])
        with self.assertRaises(EngineRegistryError):
            r.prepare_registry_candidate(wrapped['candidate'], wrapped['code_reference'], root=self.fx.root)

    def test_registry_properties_without_repeated_source_assertions(self):
        wrapped=self.fx.candidates['JL24-01']
        candidate=wrapped['candidate']
        raw=candidate['evidence_documents'][0]['assertions'][0]['raw_value']
        self.assertNotIn('fuel_type',raw)
        self.assertEqual(candidate['canonical_powertrain'],wrapped['binding']['properties'])
        plan=plan_candidate_import(wrapped,body_release=self.fx.release)
        self.assertEqual(plan['plan_version'],'3.1.0')
        self.assertEqual(r.subject(plan)['binding'],wrapped['binding'])

    def test_all_31_retained_offerings_prepare_from_registry_in_isolation(self):
        from reference.tests.body_import_support import REPOSITORY
        for n in range(1,32):
            with self.subTest(candidate=n):
                wrapped=r.prepare_retained_candidate(f'JL24-{n:02d}',root=REPOSITORY)
                r.validate('Candidate',wrapped)
                self.assertEqual(wrapped['candidate']['canonical_powertrain'],wrapped['binding']['properties'])
                self.assertTrue(all(i['target_attribute_key'] not in r.FIELDS for i in wrapped['candidate']['normalized_assertions']))
                self.assertIsNone(wrapped['candidate']['factory_series'])

    def test_retained_my2024_drive_reuses_offering_and_preserves_lineage(self):
        from reference.tests.body_import_support import REPOSITORY
        from reference.ingestion.importing.body_identity import Release
        for n in range(1, 32):
            with self.subTest(offering=n):
                wrapped = r.prepare_retained_candidate(f'JL24-{n:02d}', root=REPOSITORY)
                candidate = wrapped['candidate']
                drive = next(i for i in candidate['normalized_assertions']
                             if i['target_attribute_key'] == 'generic_drive_classification')
                doc, assertion = r.wire.evidence_index(candidate)[drive['source_assertion_ref']]
                self.assertEqual(assertion['attribute_key'], 'research_offering_correspondence')
                self.assertEqual(assertion['raw_value']['drivetrain'], '4WD')
                self.assertEqual(candidate['drivetrain'], '4WD')
                self.assertNotIn('tech-4wd', drive['source_assertion_ref'])
                self.assertFalse(any(d['source_id'] == '2022_JP_Wrangler_SP'
                                     for d in candidate['evidence_documents']))
                original = json.loads((REPOSITORY / wrapped['source_candidate']['reference']).read_text())
                self.assertTrue(any(d['source_id'] == '2022_JP_Wrangler_SP'
                                    for d in original['evidence_documents']))
                self.assertTrue(self.fx.release._established_drive(candidate))
                projected = self.fx.release._evidence_projection(candidate)
                self.assertIsNone(projected['drivetrain'])
                self.assertEqual(Release([], root=REPOSITORY)._evidence_projection(candidate), candidate)
                self.assertIn(doc, candidate['evidence_documents'])

    def test_retained_drive_rejects_contradiction_and_wrong_group(self):
        from reference.tests.body_import_support import REPOSITORY
        candidate = r.prepare_retained_candidate('JL24-01', root=REPOSITORY)['candidate']
        for field, value in (('drivetrain', '2WD'), ('candidate_id', 'JL24-02'),
                             ('model_year', 2022), ('market', 'CA')):
            with self.subTest(field=field):
                altered = deepcopy(candidate)
                drive = next(i for i in altered['normalized_assertions']
                             if i['target_attribute_key'] == 'generic_drive_classification')
                _, assertion = r.wire.evidence_index(altered)[drive['source_assertion_ref']]
                assertion['raw_value'][field] = value
                with self.assertRaises(ValidationError):
                    self.fx.release._evidence_projection(altered)

    def test_unrelated_unsupported_evidence_still_blocks_registry_planning(self):
        from reference.ingestion.importing.body_identity import byte_hash
        wrapped = deepcopy(self.fx.candidates['JL24-01'])
        candidate = wrapped['candidate']
        doc = deepcopy(candidate['evidence_documents'][0])
        raw = b'%PDF unsupported non-engine evidence'
        doc.update(source_id='unsupported-source', assertion_set_id='unsupported',
                   raw_artifact_reference='evidence/unsupported.pdf', raw_artifact_hash=byte_hash(raw),
                   assertions=[{'assertion_id':'unknown', 'attribute_key':'unknown_nonengine',
                                'raw_value':'unsupported', 'source_context':'isolated test'}])
        (self.fx.root / doc['raw_artifact_reference']).write_bytes(raw)
        candidate['evidence_documents'].append(doc)
        candidate['evidence_documents'].sort(key=lambda d:(d['source_id'],d['raw_artifact_hash'],d['assertion_set_id']))
        candidate['evidence_raw_hashes'] = sorted({d['raw_artifact_hash'] for d in candidate['evidence_documents']})
        candidate['candidate_hash'] = r.wire.candidate_hash(candidate)
        wrapped = r.seal('Candidate', wrapped)
        (self.fx.root / 'candidates/JL24-01.json').write_bytes(r.serialize('Candidate', wrapped))
        result = self.fx.release.plan('JL24-01')
        self.assertEqual(result['diagnostics'][0]['code'], 'UNSUPPORTED_SOURCE_READER')

    def test_retained_csv_family_and_offering_scopes(self):
        from reference.tests.body_import_support import REPOSITORY
        from reference.ingestion.importing.body_identity import Release
        active, _, _ = r.Release([], root=REPOSITORY)._inventories()
        for n in range(1, 32):
            key = f'JL24-{n:02d}'
            candidate = r.prepare_retained_candidate(key, root=REPOSITORY)['candidate']
            shared = [d for d in candidate['evidence_documents']
                      if 'shared-selector' in d['assertion_set_id']]
            generation = {'correspondences':[{'review_payload':{'evidence':shared}}]}
            for doc in candidate['evidence_documents']:
                with self.subTest(offering=key, document=doc['assertion_set_id']):
                    raw = (REPOSITORY / doc['raw_artifact_reference']).read_bytes()
                    self.assertTrue(self.fx.release._reviewed_csv_projection(
                        doc, raw, candidate, active[key], generation))
                    self.assertFalse(Release([], root=REPOSITORY)._reviewed_csv_projection(
                        doc, raw, candidate, active[key], generation))

    def test_csv_heading_source_row_and_qop_mismatches_still_fail(self):
        from reference.tests.body_import_support import REPOSITORY
        active, _, _ = r.Release([], root=REPOSITORY)._inventories()
        candidate = r.prepare_retained_candidate('JL24-01', root=REPOSITORY)['candidate']
        shared = next(d for d in candidate['evidence_documents']
                      if 'shared-selector' in d['assertion_set_id'])
        generation = {'correspondences':[{'review_payload':{'evidence':[shared]}}]}
        raw = (REPOSITORY / shared['raw_artifact_reference']).read_bytes()
        altered = deepcopy(shared)
        next(a for a in altered['assertions'] if a['attribute_key'] == 'source_document_heading')['raw_value'] += ' WRONG'
        with self.assertRaises(ValidationError):
            self.fx.release._reviewed_csv_projection(altered, raw, candidate, active['JL24-01'], generation)
        altered = deepcopy(shared);altered['source_id'] = 'wrong-source'
        with self.assertRaises(ValidationError):
            self.fx.release._reviewed_csv_projection(altered, raw, candidate, active['JL24-01'], generation)
        for key, value in (('model_code','WRONG'), ('marketed_trim','Wrong trim'),
                           ('quick_order_package','WRONG'), ('engine_code','WRONG')):
            with self.subTest(field=key), self.assertRaises(ValidationError):
                row = dict(active['JL24-01']);row[key] = value
                self.fx.release._reviewed_csv_projection(shared, raw, candidate, row, generation)

    def test_create_and_receipt_bind_engine_uuid(self):
        plan=self.fx.plan()
        receipt=self.execute([plan])[0]
        vehicle=VehicleDefinition.objects.get()
        self.assertEqual(str(vehicle.engine.uuid),r.subject(plan)['binding']['engine']['uuid'])
        snapshot=receipt.resolution_snapshot_json['body_import']
        r.validate('Receipt',snapshot)
        self.assertEqual(snapshot['engine_uuid'],str(vehicle.engine.uuid))
        self.assertEqual(manifest_to_dict(dict_to_manifest(snapshot['manifest'])),snapshot['manifest'])

    def test_noop_preserves_existing_fk_and_snapshots(self):
        self.execute([self.fx.plan()])
        vehicle=VehicleDefinition.objects.get();vehicle.engine=None;vehicle.save(update_fields=['engine'])
        before=list(VehicleDefinition.objects.values())
        plan=self.fx.plan()
        self.assertEqual(plan['body_plan']['action'],'no_op')
        receipt=self.execute([plan])[0]
        self.assertEqual(list(VehicleDefinition.objects.values()),before)
        self.assertIsNone(receipt.resolution_snapshot_json['body_import']['engine_uuid'])

    def test_engine_state_drift_aborts_before_any_write(self):
        plans=[self.fx.plan('JL24-01'),self.fx.plan('JL24-11')];manifest=self.authorize(plans)
        engine=Engine.objects.get(engine_code='EC1');engine.name+=' corrected';engine.save()
        before=ImportExecutionReceipt.objects.count()
        with self.assertRaises(ValidationError):self.execute(plans,manifest)
        self.assertEqual(VehicleDefinition.objects.count(),0)
        self.assertEqual(ImportExecutionReceipt.objects.count(),before)

    def test_substituting_uuid_invalidates_existing_approval(self):
        plan=self.fx.plan();manifest=self.authorize([plan]);changed=deepcopy(plan)
        changed['engine_bindings'][0]['binding']['engine']['uuid']=str(Engine.objects.get(engine_code='ERC').uuid)
        with self.assertRaises(ValidationError):self.execute([changed],manifest)

    def test_fresh_registry_binding_invalidates_old_approval(self):
        old=self.fx.plan();manifest=self.authorize([old])
        engine=Engine.objects.get(engine_code='EC1');engine.name+=' revised';engine.save()
        for key,wrapped in self.fx.candidates.items():
            new=r.prepare_registry_candidate(wrapped['candidate'],wrapped['code_reference'])
            path=self.fx.root/('candidates/'+key+'.json')
            path.write_text(r.c.canonical_json(new))
            self.fx.candidates[key]=new
        fresh=self.fx.plan()
        self.assertNotEqual(fresh['plan_hash'],old['plan_hash'])
        with self.assertRaises(ValidationError):self.execute([fresh],manifest)
        self.assertEqual(VehicleDefinition.objects.count(),0)

    def test_registry_property_change_stales_approval(self):
        plan=self.fx.plan();manifest=self.authorize([plan])
        engine=Engine.objects.get(engine_code='EC1');engine.fuel_type='diesel';engine.save()
        with self.assertRaises(ValidationError):self.execute([plan],manifest)
        self.assertEqual(VehicleDefinition.objects.count(),0)

    def test_all_31_registry_creates_preserve_ten_collision_pairs(self):
        candidates,contexts,family=self.fx.release.load()
        plans=[self.fx.release.wrap_plan(r.plan_resolved(candidate,*contexts[key],family,self.fx.release)) for key,candidate in sorted(candidates.items())]
        self.assertEqual(len({p['body_plan']['target_slug'] for p in plans}),31)
        for a,b in zip(range(1,11),(11,12,13,14,15,16,19,20,21,22)):
            self.assertTrue(plans[a-1]['body_plan']['target_slug'].endswith('-2-door'))
            self.assertTrue(plans[b-1]['body_plan']['target_slug'].endswith('-4-door'))
        receipts=self.execute(plans)
        self.assertEqual(len(receipts),31)
        self.assertEqual(VehicleDefinition.objects.filter(engine__isnull=False).count(),31)

    def test_source_code_join_is_required_not_marketing_name(self):
        wrapped=self.fx.candidates['JL24-01']
        with self.assertRaises(ValidationError):r.prepare_registry_candidate(wrapped['candidate'],'missing-qualified-code')

    def test_unknown_engine_blocks_exact_code(self):
        Engine.objects.get(engine_code='EC1').delete()
        result=self.fx.release.plan("JL24-01")
        self.assertEqual(result['diagnostics'][0]['code'],'ENGINE_NOT_REGISTERED')

    def test_actual_conflict_does_not_modify_registry(self):
        wrapped=deepcopy(self.fx.candidates['JL24-01']);candidate=wrapped['candidate']
        candidate['canonical_powertrain']['fuel_type']='diesel';candidate['candidate_hash']=r.wire.candidate_hash(candidate)
        with self.assertRaises(EngineRegistryError) as caught:r.prepare_registry_candidate(candidate,wrapped['code_reference'])
        self.assertEqual(caught.exception.code,'ENGINE_REGISTRY_CONFLICT')
        self.assertEqual(Engine.objects.get(engine_code='EC1').fuel_type,'gasoline')

    def test_planning_rechecks_source_conflicts_even_without_preparation_helper(self):
        wrapped=deepcopy(self.fx.candidates['JL24-01'])
        doc=wrapped['candidate']['evidence_documents'][0]
        source=self.fx.root/doc['raw_artifact_reference']
        native=json.loads(source.read_text());native['assertions'][0]['raw_value']['fuel_type']='diesel'
        raw=r.c.canonical_json(native).encode();old=doc['raw_artifact_hash'];new='sha256:'+r.hashlib.sha256(raw).hexdigest()
        source.write_bytes(raw)
        doc['assertions']=deepcopy(native['assertions'])
        wrapped=json.loads(json.dumps(wrapped).replace(old,new))
        wrapped['candidate']['candidate_hash']=r.wire.candidate_hash(wrapped['candidate'])
        wrapped=r.seal('Candidate',wrapped)
        (self.fx.root/'candidates/JL24-01.json').write_bytes(r.serialize('Candidate',wrapped))
        result=self.fx.release.plan('JL24-01')
        self.assertEqual(result['diagnostics'][0]['code'],'ENGINE_REGISTRY_CONFLICT')
        self.assertEqual(VehicleDefinition.objects.count(),0)

    def test_two_bodies_and_atomic_rollback(self):
        plans=[self.fx.plan('JL24-01'),self.fx.plan('JL24-11')]
        self.assertNotEqual(plans[0]['body_plan']['target_slug'],plans[1]['body_plan']['target_slug'])
        before=ImportExecutionReceipt.objects.count()
        original=r.persist
        def fail_second(plan,*args):
            if plan['body_plan']['candidate_reference']=='JL24-11':raise RuntimeError('isolated failure')
            return original(plan,*args)
        with patch.object(r,'persist',side_effect=fail_second),self.assertRaises(RuntimeError):self.execute(plans)
        self.assertEqual(VehicleDefinition.objects.count(),0)
        self.assertEqual(ImportExecutionReceipt.objects.count(),before)

    def test_old_executor_cannot_consume_stripped_registry_envelope(self):
        plan=self.fx.plan();legacy_plan=plan['body_plan']
        matrix=build_matrix([legacy_plan]);approval=build_matrix_approval(matrix,operator='project-owner',confirmed=True)
        manifest=build_manifest(matrix,approval)
        with self.assertRaises(ValidationError):self.execute([legacy_plan],manifest)

    def test_complete_family_missing_member_blocks(self):
        self.fx.release.candidate_paths=self.fx.release.candidate_paths[:-1]
        self.assertEqual(self.fx.release.plan('JL24-01')['diagnostics'][0]['code'],'FAMILY_INCOMPLETE')
