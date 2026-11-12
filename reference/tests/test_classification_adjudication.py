"""Synthetic approval/evidence tests; no real vehicle fact or live DB write."""
import copy
import json
from io import StringIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from django.test import TestCase

from reference.ingestion.classification_adjudication import (
    SOURCE_ID, apply_classification_adjudication, validate_classification_adjudication,
)
from reference.ingestion.contracts import CanonicalImportAdjudication
from reference.ingestion.generation_correspondence import digest
from reference.ingestion.importing.powertrain_identity import candidate_powertrain, assess_peer
from reference.ingestion.importing.workflow import CanonicalExecutionWorkflowError
from reference.ingestion.serialization import (serialize_artifact, deserialize_artifact,
    candidate_config_doc_to_dict, adjudication_to_dict, adjudication_from_dict, compute_adjudication_hash)
from reference.ingestion.validation import validate_adjudication
from reference.models import VehicleDefinition
from reference.tests.test_generation_correspondence import SyntheticWranglerSetup
from reference.tests import test_structured_powertrain as fixtures


class ClassificationAdjudicationTests(SyntheticWranglerSetup, TestCase):
    powertrain_candidate = fixtures.StructuredPowertrainTests.powertrain_candidate
    matrix = fixtures.StructuredPowertrainTests.matrix

    def setUp(self):
        super().setUp()
        self.jk.is_active = False
        self.jk.save()
        self.base = self.powertrain_candidate(omitted=("engine_aspiration", "electrification_type"))
        self.base_path = self.root / 'base.candidate.json'
        self.base_path.write_text(serialize_artifact(self.base))

    def artifact(self, *, approved=False):
        docs = copy.deepcopy(self.base.evidence_documents)
        ref = '|'.join((docs[0]['source_id'], docs[0]['raw_artifact_hash'],
                        docs[0]['assertion_set_id'], docs[0]['assertions'][0]['assertion_id']))
        h = digest(candidate_config_doc_to_dict(self.base))
        adj = CanonicalImportAdjudication(
            adjudication_version='1.1', created_at='2026-11-08T12:00:00+00:00',
            operator_label='synthetic_director' if approved else 'pending_human_signoff',
            candidate_reference=self.base.candidate_reference,
            source_identity={'source_id':SOURCE_ID,'source_identity_type':'candidate_digest','native_identifier':h},
            original_review_category='missing_classification', adjudication_category='evidence_backed_classification',
            adjudication_decision='approved_classifications' if approved else 'proposed_classifications',
            adjudicated_trim_name=self.base.candidate_identity.trim_name, adjudication_notes='Synthetic reviewed inference only.',
            evidence_anchors={'candidate_artifact_reference':self.base_path.name,'candidate_hash':h,
                'supporting_documents':docs,'classifications':{k:{'value':v,
                    'reasoning':'Synthetic human conclusion; not manufacturer words.',
                    'applicability':'This exact synthetic candidate digest.',
                    'limitations':'Synthetic fixture does not establish real configurations.',
                    'confidence':'moderate','source_assertion_refs':[ref],'evidence_status':'supported'}
                    for k,v in [('engine_aspiration','naturally_aspirated'),('electrification_type','none')]}})
        self.rehash(adj)
        return adj

    def rehash(self, adj):
        adj.adjudication_hash=compute_adjudication_hash(adjudication_to_dict(adj))

    def save(self, adj, name='finding.json'):
        path=self.root/name
        path.write_text(json.dumps(adjudication_to_dict(adj)))
        return path.name

    def test_proposal_valid_but_cannot_supply_canonical_facts(self):
        adj=self.artifact(); validate_adjudication(adj)
        with self.assertRaises(ValidationError): apply_classification_adjudication(self.save(adj))
        self.assertIsNone(self.base.canonical_powertrain['electrification_type'])

    def test_approved_projection_retains_human_lineage_and_round_trip(self):
        c=apply_classification_adjudication(self.save(self.artifact(approved=True)))
        self.assertEqual(candidate_powertrain(c,complete=True,verify_bytes=True)['electrification_type'],'none')
        self.assertEqual(c.evidence_documents[-1]['source_id'],SOURCE_ID)
        self.assertIn('Human-adjudicated conclusion',c.evidence_documents[-1]['assertions'][0]['source_context'])
        self.assertEqual(serialize_artifact(deserialize_artifact(serialize_artifact(c))),serialize_artifact(c))
        self.assertIsNone(self.base.canonical_powertrain['engine_aspiration'])

    def test_stale_candidate_and_changed_support_bytes_rejected(self):
        adj=self.artifact(approved=True); reference=self.save(adj)
        self.base_path.write_text(self.base_path.read_text().replace('Synthetic Sport','Different Trim'))
        with self.assertRaises(ValidationError): apply_classification_adjudication(reference)
        self.base_path.write_text(serialize_artifact(self.base))
        source=self.root/self.base.evidence_documents[0]['raw_artifact_reference']
        source.write_bytes(b'changed source')
        with self.assertRaises(ValidationError): apply_classification_adjudication(reference)

    def test_forged_projection_or_changed_approval_rejected(self):
        adj=self.artifact(approved=True); reference=self.save(adj)
        c=apply_classification_adjudication(reference)
        c.evidence_documents[-1]['assertions'][0]['raw_value']='turbocharged'
        with self.assertRaises(ValidationError): candidate_powertrain(c)
        c=apply_classification_adjudication(reference)
        adj.adjudication_decision='proposed_classifications';self.rehash(adj);self.save(adj)
        with self.assertRaises(ValidationError): candidate_powertrain(c)

    def test_human_declaration_cannot_be_relabelled_as_direct_source(self):
        from reference.ingestion.importing.powertrain_identity import _supports
        c=apply_classification_adjudication(self.save(self.artifact(approved=True)))
        doc=c.evidence_documents[-1]
        self.assertFalse(_supports(doc['assertions'][0]['raw_value'],'engine_aspiration','naturally_aspirated'))
        old_prefix=SOURCE_ID+'|'
        doc['source_id']='pretend_manufacturer';doc['extractor_id']='pretend_direct_extractor'
        for i in c.normalized_assertions:
            if i.source_assertion_ref.startswith(old_prefix):
                i.source_assertion_ref='pretend_manufacturer|'+i.source_assertion_ref[len(old_prefix):]
        with self.assertRaises(ValidationError): candidate_powertrain(c)

    def test_unsupported_contradictory_or_broken_evidence_stays_blocked(self):
        for status in ['unsupported','materially_contradictory']:
            adj=self.artifact(approved=True)
            adj.evidence_anchors['classifications']['engine_aspiration']['evidence_status']=status
            self.rehash(adj)
            with self.assertRaises(ValidationError): validate_classification_adjudication(adj,require_approved=True)
        adj=self.artifact(approved=True)
        adj.evidence_anchors['classifications']['engine_aspiration']['source_assertion_refs']=['missing']
        self.rehash(adj)
        with self.assertRaises(ValidationError): validate_adjudication(adj)

    def test_cannot_override_established_value_or_add_unknown_attribute(self):
        adj=self.artifact(approved=True)
        adj.evidence_anchors['classifications']['fuel_type']=copy.deepcopy(adj.evidence_anchors['classifications']['engine_aspiration'])
        adj.evidence_anchors['classifications']['fuel_type']['value']='gasoline'
        self.rehash(adj)
        with self.assertRaises(ValidationError): validate_adjudication(adj)
        adj=self.artifact(approved=True)
        adj.evidence_anchors['classifications']['horsepower']=adj.evidence_anchors['classifications'].pop('engine_aspiration')
        self.rehash(adj)
        with self.assertRaises(ValidationError): validate_adjudication(adj)

    def test_existing_planning_execution_receipt_and_peer_revalidation(self):
        reference=self.save(self.artifact(approved=True))
        c=apply_classification_adjudication(reference)
        plan,manifest=self.plan_and_manifest(c)
        self.assertEqual(plan.planned_action.value,'create')
        result,receipt=self.execute(plan,manifest)
        record=VehicleDefinition.objects.get(pk=result.vehicle_definition_id)
        self.assertEqual(record.electrification_type,'none')
        docs=receipt.resolution_snapshot_json['generation_resolution']['documents']
        self.assertEqual(docs[-1]['source_id'],SOURCE_ID)
        self.assertEqual(assess_peer(record)[0]['engine_aspiration'],'naturally_aspirated')
        self.assertEqual(self.plan_and_manifest(c)[0].planned_action.value,'no_op_exact_match')
        (self.root/reference).write_text('{}')
        with self.assertRaises(ValidationError): assess_peer(record)

    def test_source_change_stales_already_reviewed_execution(self):
        c=apply_classification_adjudication(self.save(self.artifact(approved=True)))
        plan,manifest=self.plan_and_manifest(c)
        (self.root/'finding.json').write_text('{}')
        with self.assertRaisesRegex(CanonicalExecutionWorkflowError,'Retained source bytes changed'):
            self.execute(plan,manifest)
        self.assertEqual(VehicleDefinition.objects.count(),0)

    def test_command_requires_human_confirmation_and_preserves_proposal(self):
        proposal=self.artifact(); path=self.save(proposal,'proposal.json')
        output=self.root/'approved.json'; revised=self.root/'revised.json'
        args={'classification_review':path,'output':str(output),'candidate_output':str(revised),'operator':'synthetic_director','stdout':StringIO()}
        with self.assertRaisesRegex(CommandError,'explicit human --operator'):
            call_command('adjudicate_canonical_import',**(args | {'operator':None}))
        with patch('builtins.input',return_value='no'):
            call_command('adjudicate_canonical_import',**args)
        self.assertFalse(output.exists());self.assertFalse(revised.exists())
        with patch('builtins.input',return_value='APPROVE CLASSIFICATIONS'):
            call_command('adjudicate_canonical_import',**args)
        approved=adjudication_from_dict(json.loads(output.read_text()))
        validate_classification_adjudication(approved,require_approved=True)
        self.assertEqual(adjudication_from_dict(json.loads((self.root/path).read_text())).adjudication_decision,'proposed_classifications')
        self.assertEqual(candidate_powertrain(deserialize_artifact(revised.read_text()),complete=True)['electrification_type'],'none')

    def test_matrix_reuses_approval_receipts_and_idempotency(self):
        from reference.ingestion.matrix_approval import build_matrix_approval
        from reference.ingestion.importing.matrix_workflow import execute_matrix_year
        from reference.models import ImportExecutionReceipt
        classified=apply_classification_adjudication(self.save(self.artifact(approved=True)))
        direct=self.powertrain_candidate(electrification='mild_hybrid')
        matrix=self.matrix([classified,direct])
        approval=build_matrix_approval(matrix,operator='synthetic_director',confirmed=True)
        candidates={c.candidate_reference:c for c in [classified,direct]}
        execute_matrix_year(matrix,approval,2018,candidates,self.root,execution_operator='synthetic_director')
        self.assertEqual(VehicleDefinition.objects.count(),2)
        count=ImportExecutionReceipt.objects.count()
        execute_matrix_year(matrix,approval,2018,candidates,self.root,execution_operator='synthetic_director')
        self.assertEqual(ImportExecutionReceipt.objects.count(),count)

    def test_classification_does_not_bypass_generation_resolution(self):
        from reference.ingestion.importing.planner import plan_candidate_import
        c=apply_classification_adjudication(self.save(self.artifact(approved=True)))
        self.jk.is_active=True;self.jk.save()
        plan=plan_candidate_import(c)
        self.assertEqual(plan.planned_action.value,'flag_review')
        self.assertIn('generations',str(plan.reasons).lower())

    def test_chained_or_cyclic_base_is_rejected_before_deserialization(self):
        adj=self.artifact(approved=True)
        self.base_path.write_text(json.dumps({'envelope':{'schema_version':'2.1.0'},
            'evidence_documents':[{'source_id':SOURCE_ID,'extractor_id':'approved_human_classification'}]}))
        with self.assertRaisesRegex(ValidationError,'Chained classification'):
            validate_adjudication(adj)

    def test_unrelated_evidence_conflict_blocks_despite_approved_adjudication(self):
        from reference.ingestion.contracts import AttributeReconciliationState, ReconciliationState
        from reference.ingestion.importing.planner import plan_candidate_import
        self.base.reconciliation_and_review.requires_human_review = True
        self.base.reconciliation_and_review.attribute_states['trim'] = AttributeReconciliationState(
            ReconciliationState.CONFLICTING.value, 'pending_review', 'Unrelated conflict across sources',
        )
        self.base_path.write_text(serialize_artifact(self.base))
        adj = self.artifact(approved=True)
        classified = apply_classification_adjudication(self.save(adj))
        self.assertTrue(classified.reconciliation_and_review.requires_human_review)
        self.assertIn('trim', classified.reconciliation_and_review.attribute_states)
        self.assertEqual(
            classified.reconciliation_and_review.attribute_states['trim'].reconciliation_state,
            ReconciliationState.CONFLICTING.value,
        )
        plan = plan_candidate_import(classified)
        self.assertEqual(plan.planned_action.value, 'flag_review')
        self.assertTrue(any('trim' in r or 'human review' in r for r in plan.reasons))

    def test_unresolved_non_powertrain_context_contradiction_blocks(self):
        from reference.ingestion.importing.planner import plan_candidate_import
        self.base.reconciliation_and_review.requires_human_review = True
        self.base.reconciliation_and_review.reconciliation_notes = 'Context contradiction detected: model_year context 2022 vs evidence 2021'
        self.base_path.write_text(serialize_artifact(self.base))
        adj = self.artifact(approved=True)
        classified = apply_classification_adjudication(self.save(adj))
        self.assertTrue(classified.reconciliation_and_review.requires_human_review)
        plan = plan_candidate_import(classified)
        self.assertEqual(plan.planned_action.value, 'flag_review')

    def test_partially_resolved_powertrain_classification_blocks(self):
        from reference.ingestion.contracts import AttributeReconciliationState, ReconciliationState
        from reference.ingestion.importing.planner import plan_candidate_import
        self.base.reconciliation_and_review.requires_human_review = True
        self.base.reconciliation_and_review.attribute_states['engine_aspiration'] = AttributeReconciliationState(
            ReconciliationState.INCOMPLETE.value, 'pending_review', 'Null field',
        )
        self.base.reconciliation_and_review.attribute_states['electrification_type'] = AttributeReconciliationState(
            ReconciliationState.INCOMPLETE.value, 'pending_review', 'Null field',
        )
        self.base_path.write_text(serialize_artifact(self.base))
        adj = self.artifact(approved=True)
        del adj.evidence_anchors['classifications']['electrification_type']
        self.rehash(adj)
        classified = apply_classification_adjudication(self.save(adj))
        self.assertIsNone(classified.canonical_powertrain['electrification_type'])
        self.assertTrue(classified.reconciliation_and_review.requires_human_review)
        self.assertIn('electrification_type', classified.reconciliation_and_review.attribute_states)
        plan = plan_candidate_import(classified)
        self.assertEqual(plan.planned_action.value, 'flag_review')

    def test_unapproved_adjudication_cannot_clear_holds_or_project(self):
        proposal = self.artifact(approved=False)
        self.assertEqual(proposal.adjudication_decision, 'proposed_classifications')
        with self.assertRaises(ValidationError):
            apply_classification_adjudication(self.save(proposal))

    def test_rejected_adjudication_rejected_by_validator(self):
        rejected = self.artifact(approved=True)
        rejected.adjudication_decision = 'rejected'
        self.rehash(rejected)
        with self.assertRaises(ValidationError):
            validate_classification_adjudication(rejected)

    def test_mismatched_candidate_digest_raises_stale_validation(self):
        adj = self.artifact(approved=True)
        new_digest = 'sha256:' + 'f' * 64
        adj.evidence_anchors['candidate_hash'] = new_digest
        adj.source_identity['native_identifier'] = new_digest
        self.rehash(adj)
        with self.assertRaisesRegex(ValidationError, 'Adjudication candidate became stale.'):
            apply_classification_adjudication(self.save(adj))

    def test_missing_supporting_evidence_fails_verification(self):
        adj = self.artifact(approved=True)
        adj.evidence_anchors['supporting_documents'][0]['raw_artifact_reference'] = 'nonexistent_file.pdf'
        self.rehash(adj)
        with self.assertRaises((ValidationError, OSError)):
            apply_classification_adjudication(self.save(adj))

    def test_conflicting_classification_evidence_remains_blocker(self):
        from reference.ingestion.contracts import AttributeReconciliationState, ReconciliationState
        from reference.ingestion.importing.planner import plan_candidate_import
        self.base.reconciliation_and_review.requires_human_review = True
        self.base.reconciliation_and_review.attribute_states['engine_aspiration'] = AttributeReconciliationState(
            ReconciliationState.CONFLICTING.value, 'pending_review', 'Conflicting aspiration evidence',
        )
        self.base_path.write_text(serialize_artifact(self.base))
        adj = self.artifact(approved=True)
        classified = apply_classification_adjudication(self.save(adj))
        self.assertIn('engine_aspiration', classified.reconciliation_and_review.attribute_states)
        self.assertEqual(
            classified.reconciliation_and_review.attribute_states['engine_aspiration'].reconciliation_state,
            ReconciliationState.CONFLICTING.value,
        )
        self.assertTrue(classified.reconciliation_and_review.requires_human_review)
        plan = plan_candidate_import(classified)
        self.assertEqual(plan.planned_action.value, 'flag_review')

    def test_legitimate_classification_holds_resolved_enables_create(self):
        from reference.ingestion.contracts import AttributeReconciliationState, ReconciliationState, ReviewDisposition
        from reference.ingestion.importing.planner import plan_candidate_import
        self.base.reconciliation_and_review.requires_human_review = True
        self.base.reconciliation_and_review.attribute_states['engine_aspiration'] = AttributeReconciliationState(
            ReconciliationState.INCOMPLETE.value, 'pending_review', 'Missing aspiration',
        )
        self.base.reconciliation_and_review.attribute_states['electrification_type'] = AttributeReconciliationState(
            ReconciliationState.INCOMPLETE.value, 'pending_review', 'Missing electrification',
        )
        self.base_path.write_text(serialize_artifact(self.base))
        adj = self.artifact(approved=True)
        classified = apply_classification_adjudication(self.save(adj))
        self.assertFalse(classified.reconciliation_and_review.requires_human_review)
        self.assertEqual(
            classified.reconciliation_and_review.review_workflow_disposition,
            ReviewDisposition.NOT_REQUIRED.value,
        )
        self.assertNotIn('engine_aspiration', classified.reconciliation_and_review.attribute_states)
        self.assertNotIn('electrification_type', classified.reconciliation_and_review.attribute_states)
        plan = plan_candidate_import(classified)
        self.assertEqual(plan.planned_action.value, 'create')
        self.assertEqual(plan.eligibility_status.value, 'eligible')
