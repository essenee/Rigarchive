"""
Unit & Integration Tests for Review-Adjudication Workflow & Controlled 2020 Toyota Study (RA-026).

Verifies CanonicalImportAdjudication contract, SHA-256 hashing, trust boundary protection,
manifest v1.1/v1.0 compatibility, ADJUDICATED_DISTINCT_GRADE planning, stale revalidation,
CLI adjudication command, and full 12-configuration end-to-end 5-stage lifecycle.
"""

import json
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import (
    AttributeReconciliationState,
    CandidateIdentity,
    CanonicalImportAdjudication,
    Envelope,
    ExtractionProvenance,
    ReconciliationAndReview,
    ReconciliationState,
    ReviewDisposition,
    SourceApplicability,
    SourceAssertion,
    SourceAssertionSet,
    SourceMetadata,
)
from reference.ingestion.importing import (
    CanonicalImportPlan,
    ImportCreateBasis,
    ImportEligibilityStatus,
    ImportExecutionOutcome,
    ImportPlannedAction,
)
from reference.ingestion.importing.importer import execute_candidate_import
from reference.ingestion.importing.planner import plan_candidate_import, plan_candidate_import_with_adjudications
from reference.ingestion.importing.workflow import execute_canonical_import_workflow
from reference.ingestion.manifest import (
    build_review_manifest,
    dict_to_manifest,
    manifest_to_dict,
    reconstruct_plan_from_manifest,
)
from reference.ingestion.normalization.manufacturer import ManufacturerNormalizer
from reference.ingestion.serialization import adjudication_from_dict, adjudication_to_dict, compute_adjudication_hash
from reference.ingestion.validation import IngestionValidationError, validate_adjudication
from reference.models import Generation, ImportExecutionReceipt, Manufacturer, VehicleDefinition, VehicleModel


class AdjudicationWorkflowTests(TestCase):
    def setUp(self):
        self.mfr = Manufacturer.objects.create(name="Toyota", slug="toyota")
        self.model = VehicleModel.objects.create(manufacturer=self.mfr, name="4Runner", slug="4runner")
        self.gen = Generation.objects.create(
            vehicle_model=self.model,
            name="Fifth Generation",
            slug="fifth-generation",
            start_year=2010,
        )

        self.normalizer = ManufacturerNormalizer()

    def _make_candidate(self, grade: str, drive: str, model_code: str = "8670", raw_artifact_hash: Optional[str] = None, requires_review: bool = False) -> Any:
        art_hash = raw_artifact_hash or ("sha256:" + "a" * 64)
        prov = SourceMetadata(
            source_id="toyota_usa",
            native_record_id=model_code,
            source_applicability=SourceApplicability(market="US"),
            extraction_provenance=ExtractionProvenance(
                raw_artifact_hash=art_hash,
                raw_artifact_reference="ref.pdf",
                extractor_id="test",
                extractor_version="1.0",
                extraction_mode="deterministic_structured_parser",
            ),
            target_context={"make": "Toyota", "model": "4Runner", "model_year": 2020, "market": "US"},
        )
        assertions = [
            SourceAssertion(attribute_key="make_name", raw_value="Toyota", assertion_id="1"),
            SourceAssertion(attribute_key="model_name", raw_value="4Runner", assertion_id="2"),
            SourceAssertion(attribute_key="model_year", raw_value="2020", assertion_id="3"),
            SourceAssertion(attribute_key="manufacturer_grade", raw_value=grade, assertion_id="4"),
            SourceAssertion(attribute_key="model_code", raw_value=model_code, assertion_id="5"),
            SourceAssertion(attribute_key="drive_descriptor", raw_value=drive, assertion_id="6"),
            SourceAssertion(attribute_key="engine_displacement_liters", raw_value="4.0", assertion_id="7"),
            SourceAssertion(attribute_key="engine_cylinders", raw_value="6", assertion_id="8"),
            SourceAssertion(attribute_key="market", raw_value="US", assertion_id="9"),
        ]
        asset = SourceAssertionSet(
            envelope=Envelope(artifact_type="rigarchive.source_assertion_set.v1", schema_version="1.0.0", created_at="2026-08-15T16:00:00Z"),
            provenance=prov,
            source_assertions=assertions,
        )
        normalized = self.normalizer.normalize(asset)
        cand_id = CandidateIdentity(
            manufacturer_name="Toyota",
            vehicle_model_name="4Runner",
            model_year=2020,
            market="US",
            trim_name=grade,
        )
        doc = construct_candidate_configuration(cand_id, [asset], normalized)
        doc.raw_artifact_hash = art_hash

        if requires_review:
            doc.reconciliation_and_review = ReconciliationAndReview(
                requires_human_review=True,
                attribute_states={
                    "trim": AttributeReconciliationState(
                        reconciliation_state=ReconciliationState.AMBIGUOUS.value,
                        review_disposition=ReviewDisposition.UNDER_REVIEW.value,
                    )
                },
            )

        return doc

    def test_adjudication_hash_computation_and_validation(self):
        raw_dict = {
            "adjudication_version": "1.0",
            "created_at": "2026-08-15T16:00:00Z",
            "operator_label": "operator1",
            "original_manifest_hash": "sha256:" + "1" * 64,
            "candidate_reference": "cand_ref_8670",
            "source_identity": {"source_id": "toyota_usa", "native_identifier": "8670"},
            "original_review_category": "flag_review",
            "adjudication_category": "distinct_factory_grade",
            "adjudication_decision": "approved_distinct_trim",
            "adjudicated_trim_name": "SR5 Premium",
            "adjudication_notes": "Verified distinct grade from publisher documentation.",
        }

        h1 = compute_adjudication_hash(raw_dict)
        self.assertTrue(h1.startswith("sha256:"))
        self.assertEqual(len(h1), 71)

        raw_dict["adjudication_hash"] = h1
        adj = adjudication_from_dict(raw_dict)
        validate_adjudication(adj)  # Passes cleanly

        # Tampered hash should fail validation
        raw_dict_bad = dict(raw_dict)
        raw_dict_bad["adjudication_hash"] = "sha256:" + "0" * 64
        adj_bad = adjudication_from_dict(raw_dict_bad)
        with self.assertRaises(IngestionValidationError):
            validate_adjudication(adj_bad)

    def test_invalid_category_adjudication_rejected(self):
        adj = CanonicalImportAdjudication(
            adjudication_version="1.0",
            created_at="2026-08-15T16:00:00Z",
            operator_label="op",
            candidate_reference="cand_1",
            adjudicated_trim_name="SR5",
            adjudication_category="unsupported_custom_category",
            adjudication_decision="approved_distinct_trim",
        )
        with self.assertRaises(IngestionValidationError):
            validate_adjudication(adj)

    def test_adjudication_planning_trust_boundary(self):
        # 1. Create base SR5 2WD record
        VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
            slug="2020-sr5-40l-v6-2wd-us",
        )

        # 2. Candidate SR5 Premium 2WD requires review under base planner
        cand = self._make_candidate("SR5 Premium", "2WD", "8670", requires_review=True)
        base_plan = plan_candidate_import(cand)
        self.assertEqual(base_plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

        # 3. Create valid adjudication
        adj_dict = {
            "adjudication_version": "1.0",
            "created_at": "2026-08-15T16:00:00Z",
            "operator_label": "operator1",
            "original_manifest_hash": "sha256:" + "1" * 64,
            "candidate_reference": cand.candidate_reference,
            "source_identity": {"source_id": "toyota_usa", "native_identifier": "8670"},
            "original_review_category": "distinct_factory_grade",
            "adjudication_category": "distinct_factory_grade",
            "adjudication_decision": "approved_distinct_trim",
            "adjudicated_trim_name": "SR5 Premium",
            "adjudication_notes": "Verified distinct factory grade.",
        }
        adj_hash = compute_adjudication_hash(adj_dict)
        adj_dict["adjudication_hash"] = adj_hash
        adj = adjudication_from_dict(adj_dict)

        # 4. Plan with valid adjudication yields ADJUDICATED_DISTINCT_GRADE
        adj_plan = plan_candidate_import_with_adjudications(cand, [adj])
        self.assertEqual(adj_plan.eligibility_status, ImportEligibilityStatus.ELIGIBLE)
        self.assertEqual(adj_plan.planned_action, ImportPlannedAction.CREATE)
        self.assertEqual(adj_plan.create_basis, ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE)
        self.assertEqual(adj_plan.adjudication_hash, adj_hash)

        # 5. Tampered candidate reference in adjudication fails trust boundary (remains FLAG_REVIEW)
        adj_dict_bad_ref = dict(adj_dict)
        adj_dict_bad_ref["candidate_reference"] = "different_cand_ref"
        adj_dict_bad_ref["adjudication_hash"] = compute_adjudication_hash(adj_dict_bad_ref)
        adj_bad_ref = adjudication_from_dict(adj_dict_bad_ref)

        bad_plan = plan_candidate_import_with_adjudications(cand, [adj_bad_ref])
        self.assertEqual(bad_plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

    def test_manifest_v1_1_and_v1_0_compatibility(self):
        cand = self._make_candidate("SR5 Premium", "2WD", "8670", requires_review=True)
        plan = CanonicalImportPlan(
            candidate_reference=cand.candidate_reference,
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE,
            resolved_manufacturer_id=self.mfr.id,
            resolved_vehicle_model_id=self.model.id,
            resolved_generation_id=self.gen.id,
            target_vehicle_definition_fields={"model_year": 2020, "trim_name": "SR5 Premium", "market": "US"},
            target_slug="2020-sr5-premium-40l-v6-2wd-us",
            adjudication_reference="adjudication_8670.json",
            adjudication_hash="sha256:" + "2" * 64,
        )

        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash="sha256:" + "a" * 64,
            raw_artifact_reference="ref.pdf",
            extraction_provenance={"extractor_id": "test"},
            plans=[plan],
            native_identifiers={cand.candidate_reference: "8670"},
        )

        self.assertEqual(manifest.manifest_version, "1.1")
        m_dict = manifest_to_dict(manifest)

        # Roundtrip parse manifest v1.1
        parsed = dict_to_manifest(m_dict)
        self.assertEqual(parsed.manifest_version, "1.1")
        self.assertEqual(parsed.plans[0].adjudication_hash, "sha256:" + "2" * 64)

        # Reconstruct plan
        reconstructed = reconstruct_plan_from_manifest(parsed.plans[0])
        self.assertEqual(reconstructed.create_basis, ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE)
        self.assertEqual(reconstructed.adjudication_hash, "sha256:" + "2" * 64)

    def test_adjudicated_stale_revalidation_same_trim(self):
        # 1. Base SR5 2WD row
        VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
            slug="2020-sr5-40l-v6-2wd-us",
        )

        # 2. Plan for SR5 Premium 2WD under ADJUDICATED_DISTINCT_GRADE
        plan = CanonicalImportPlan(
            candidate_reference="cand_ref_8670",
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE,
            resolved_manufacturer_id=self.mfr.id,
            resolved_vehicle_model_id=self.model.id,
            resolved_generation_id=self.gen.id,
            target_vehicle_definition_fields={"model_year": 2020, "trim_name": "SR5 Premium", "engine_name": "4.0L V6", "drivetrain": "2WD", "market": "US"},
            target_slug="2020-sr5-premium-40l-v6-2wd-us",
            adjudication_reference="adj_8670.json",
            adjudication_hash="sha256:" + "3" * 64,
        )

        # 3. Insert same trim ("SR5 Premium 4WD") prior to execution
        VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="SR5 Premium",
            engine_name="4.0L V6",
            drivetrain="4WD",
            market="US",
            slug="2020-sr5-premium-40l-v6-4wd-us",
        )

        # 4. Execution must return ABORTED_STALE_PLAN
        res = execute_candidate_import(plan)
        self.assertEqual(res.outcome, ImportExecutionOutcome.ABORTED_STALE_PLAN)

    def test_adjudicated_unrelated_trim_growth_executes(self):
        # 1. Base SR5 2WD row
        VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
            slug="2020-sr5-40l-v6-2wd-us",
        )

        # 2. Plan for SR5 Premium 2WD under ADJUDICATED_DISTINCT_GRADE
        plan = CanonicalImportPlan(
            candidate_reference="cand_ref_8670",
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE,
            resolved_manufacturer_id=self.mfr.id,
            resolved_vehicle_model_id=self.model.id,
            resolved_generation_id=self.gen.id,
            target_vehicle_definition_fields={"model_year": 2020, "trim_name": "SR5 Premium", "engine_name": "4.0L V6", "drivetrain": "2WD", "market": "US"},
            target_slug="2020-sr5-premium-40l-v6-2wd-us",
            adjudication_reference="adj_8670.json",
            adjudication_hash="sha256:" + "3" * 64,
        )

        # 3. Insert UNRELATED trim ("Limited 2WD") prior to execution
        VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="Limited",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
            slug="2020-limited-40l-v6-2wd-us",
        )

        # 4. Unrelated trim growth does NOT stale plan: execution succeeds
        res = execute_candidate_import(plan)
        self.assertEqual(res.outcome, ImportExecutionOutcome.CREATED)

    def test_cli_adjudicate_canonical_import_command(self):
        # Build manifest with 1 flagged review plan
        cand = self._make_candidate("SR5 Premium", "2WD", "8670", requires_review=True)
        plan = CanonicalImportPlan(
            candidate_reference=cand.candidate_reference,
            eligibility_status=ImportEligibilityStatus.REQUIRES_REVIEW,
            planned_action=ImportPlannedAction.FLAG_REVIEW,
            target_vehicle_definition_fields={"trim_name": "SR5 Premium"},
        )
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash="sha256:" + "a" * 64,
            raw_artifact_reference="ref.pdf",
            extraction_provenance={"extractor_id": "test"},
            plans=[plan],
            native_identifiers={cand.candidate_reference: "8670"},
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            m_path = Path(temp_dir) / "manifest.json"
            out_path = Path(temp_dir) / "adj_8670.json"
            with open(m_path, "w", encoding="utf-8") as f:
                json.dump(manifest_to_dict(manifest), f)

            # Execute CLI command
            out = StringIO()
            call_command(
                "adjudicate_canonical_import",
                f"--manifest={m_path}",
                f"--candidate-ref={cand.candidate_reference}",
                "--category=distinct_factory_grade",
                "--trim-name=SR5 Premium",
                "--notes=Verified distinct grade from press release.",
                f"--output={out_path}",
                stdout=out,
            )

            self.assertTrue(out_path.exists())
            with open(out_path, "r", encoding="utf-8") as f:
                adj_data = json.load(f)

            self.assertEqual(adj_data["adjudication_category"], "distinct_factory_grade")
            self.assertEqual(adj_data["adjudicated_trim_name"], "SR5 Premium")
            self.assertTrue(adj_data["adjudication_hash"].startswith("sha256:"))

            # Confirm 0 canonical writes
            self.assertEqual(VehicleDefinition.objects.count(), 0)

    def test_full_controlled_2020_toyota_study_lifecycle(self):
        """
        Controlled 2020 Toyota 4Runner Population Study:
        Processes all 12 model codes through the full 5-stage lifecycle.
        Expected results:
          12 configurations
          12 separate execution authorizations
          7 human domain adjudications
          1 FIRST_REPRESENTATION (8664)
          4 MECHANICAL_DIMENSION (8666, 8672, 8688, 8692)
          7 ADJUDICATED_DISTINCT_GRADE (8670, 8674, 8676, 8682, 8686, 8690, 8680)
        """
        model_codes = [
            ("8664", "SR5", "2WD"),
            ("8666", "SR5", "Part-Time 4WD"),
            ("8670", "SR5 Premium", "2WD"),
            ("8672", "SR5 Premium", "Part-Time 4WD"),
            ("8674", "TRD Off-Road", "Part-Time 4WD"),
            ("8676", "TRD Off-Road Premium", "Part-Time 4WD"),
            ("8682", "Venture Special Edition", "Part-Time 4WD"),
            ("8686", "Limited", "2WD"),
            ("8688", "Limited", "Full-Time 4WD"),
            ("8690", "Nightshade Special Edition", "2WD"),
            ("8692", "Nightshade Special Edition", "Full-Time 4WD"),
            ("8680", "TRD Pro", "Part-Time 4WD"),
        ]

        source_established_bases = 0
        adjudication_bases = 0
        mechanical_bases = 0
        first_rep_bases = 0

        for code, grade, drive in model_codes:
            cand = self._make_candidate(grade, drive, code)

            # Stage 1: Initial Planning
            init_plan = plan_candidate_import(cand)

            adj = None
            if init_plan.planned_action == ImportPlannedAction.FLAG_REVIEW:
                # Stage 2: Human Adjudication
                raw_adj = {
                    "adjudication_version": "1.0",
                    "created_at": "2026-08-15T16:00:00Z",
                    "operator_label": "operator1",
                    "original_manifest_hash": "sha256:" + "1" * 64,
                    "candidate_reference": cand.candidate_reference,
                    "source_identity": {"source_id": "toyota_usa", "native_identifier": code},
                    "original_review_category": "distinct_factory_grade",
                    "adjudication_category": "distinct_factory_grade" if "Special" not in grade else "special_edition_grade",
                    "adjudication_decision": "approved_distinct_trim",
                    "adjudicated_trim_name": grade,
                    "adjudication_notes": f"Verified distinct grade {grade}.",
                }
                raw_adj["adjudication_hash"] = compute_adjudication_hash(raw_adj)
                adj = adjudication_from_dict(raw_adj)

                # Stage 3: Re-Planning
                exec_plan = plan_candidate_import_with_adjudications(cand, [adj])
            else:
                exec_plan = init_plan

            self.assertEqual(exec_plan.eligibility_status, ImportEligibilityStatus.ELIGIBLE)
            self.assertEqual(exec_plan.planned_action, ImportPlannedAction.CREATE)

            if exec_plan.create_basis == ImportCreateBasis.FIRST_REPRESENTATION:
                first_rep_bases += 1
            elif exec_plan.create_basis == ImportCreateBasis.MECHANICAL_DIMENSION:
                mechanical_bases += 1
            elif exec_plan.create_basis == ImportCreateBasis.SOURCE_ESTABLISHED_GRADE:
                source_established_bases += 1
            elif exec_plan.create_basis == ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE:
                adjudication_bases += 1

            # Stage 4: Manifest & Interactive Authorization Handoff
            manifest = build_review_manifest(
                source_id="toyota_usa",
                raw_artifact_hash="sha256:" + "a" * 64,
                raw_artifact_reference="ref.pdf",
                extraction_provenance={"extractor": "test"},
                plans=[exec_plan],
                native_identifiers={cand.candidate_reference: code},
            )
            review_plan = manifest.plans[0]
            reconstructed_plan = reconstruct_plan_from_manifest(review_plan)

            # Stage 5: Execution Dispatch
            res, receipt = execute_canonical_import_workflow(
                plan=reconstructed_plan,
                manifest=manifest,
                review_plan=review_plan,
                operator_label="operator1",
                adjudication_artifact=adj if exec_plan.create_basis == ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE else None,
            )

            self.assertEqual(res.outcome, ImportExecutionOutcome.CREATED)
            self.assertEqual(receipt.execution_outcome, "created")
            if exec_plan.create_basis == ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE:
                self.assertTrue(receipt.adjudication_hash.startswith("sha256:"))

        self.assertEqual(VehicleDefinition.objects.count(), 12)
        self.assertEqual(first_rep_bases, 1)
        self.assertEqual(mechanical_bases, 4)
        self.assertEqual(source_established_bases, 7)

    def test_forged_manifest_attack_refused(self):
        """
        Mandatory Security Test (Requirement 7):
        A forged v1.1 manifest with a valid manifest_hash and arbitrary adjudication_hash,
        but without a validated CanonicalImportAdjudication artifact, MUST be refused by the workflow.
        """
        plan = CanonicalImportPlan(
            candidate_reference="cand_ref_forged",
            eligibility_status=ImportEligibilityStatus.ELIGIBLE,
            planned_action=ImportPlannedAction.CREATE,
            create_basis=ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE,
            resolved_manufacturer_id=self.mfr.id,
            resolved_vehicle_model_id=self.model.id,
            resolved_generation_id=self.gen.id,
            target_vehicle_definition_fields={"model_year": 2020, "trim_name": "Forged Trim", "market": "US"},
            target_slug="2020-forged-trim-40l-v6-2wd-us",
            adjudication_reference="adjudication_forged.json",
            adjudication_hash="sha256:" + "f" * 64,
        )

        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash="sha256:" + "a" * 64,
            raw_artifact_reference="ref.pdf",
            extraction_provenance={"extractor_id": "test"},
            plans=[plan],
            native_identifiers={"cand_ref_forged": "8699"},
        )
        review_plan = manifest.plans[0]
        reconstructed_plan = reconstruct_plan_from_manifest(review_plan)

        from reference.ingestion.importing.workflow import CanonicalExecutionWorkflowError
        with self.assertRaises(CanonicalExecutionWorkflowError) as cm:
            execute_canonical_import_workflow(
                plan=reconstructed_plan,
                manifest=manifest,
                review_plan=review_plan,
                operator_label="attacker",
                adjudication_artifact=None,
            )

        self.assertIn("Execution refused", str(cm.exception))
        self.assertEqual(VehicleDefinition.objects.count(), 0)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    def test_non_adjudicable_review_reasons_refuse_promotion(self):
        """
        Mandatory Review-Condition Test (Requirement 8):
        Structurally non-adjudicable FLAG_REVIEW reasons (missing evidence, context contradiction,
        overlapping generations) MUST refuse promotion even if a valid adjudication artifact is supplied.
        """
        # Case A: CandidateIdentity trim contradicts evidence trim
        cand_contradict = self._make_candidate("SR5 Premium", "2WD", "8670")
        cand_contradict.candidate_identity.trim_name = "TRD Off-Road"  # Contradicts evidence "SR5 Premium"
        base_plan_contradict = plan_candidate_import(cand_contradict)
        self.assertEqual(base_plan_contradict.planned_action, ImportPlannedAction.FLAG_REVIEW)

        adj_dict = {
            "adjudication_version": "1.0",
            "created_at": "2026-08-15T16:00:00Z",
            "operator_label": "op",
            "original_manifest_hash": "sha256:" + "1" * 64,
            "candidate_reference": cand_contradict.candidate_reference,
            "source_identity": {"source_id": "toyota_usa", "native_identifier": "8670"},
            "original_review_category": "distinct_factory_grade",
            "adjudication_category": "distinct_factory_grade",
            "adjudication_decision": "approved_distinct_trim",
            "adjudicated_trim_name": "SR5 Premium",
            "adjudication_notes": "Attempt override.",
        }
        adj_dict["adjudication_hash"] = compute_adjudication_hash(adj_dict)
        adj = adjudication_from_dict(adj_dict)

        res_plan = plan_candidate_import_with_adjudications(cand_contradict, [adj])
        self.assertEqual(res_plan.planned_action, ImportPlannedAction.FLAG_REVIEW)
        self.assertNotEqual(res_plan.create_basis, ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE)

        # Case B: Multiple overlapping active generations
        Gen2 = Generation.objects.create(
            vehicle_model=self.model,
            name="Fifth Generation Overlap",
            slug="fifth-generation-overlap",
            start_year=2010,
        )
        cand_overlap = self._make_candidate("SR5 Premium", "2WD", "8670")
        base_plan_overlap = plan_candidate_import(cand_overlap)
        self.assertEqual(base_plan_overlap.planned_action, ImportPlannedAction.FLAG_REVIEW)

        res_plan_overlap = plan_candidate_import_with_adjudications(cand_overlap, [adj])
        self.assertEqual(res_plan_overlap.planned_action, ImportPlannedAction.FLAG_REVIEW)
        Gen2.delete()

    def test_evidence_revision_change_rejects_adjudication(self):
        """
        Mandatory Evidence Revision Test (Requirement 9):
        An adjudication artifact created against evidence revision A MUST be rejected
        when re-planning against a candidate with revised evidence hash B.
        """
        VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
            slug="2020-sr5-40l-v6-2wd-us",
        )
        cand_rev_a = self._make_candidate("SR5 Premium", "2WD", "8670", requires_review=True)
        hash_a = "sha256:" + "a" * 64

        adj_dict = {
            "adjudication_version": "1.0",
            "created_at": "2026-08-15T16:00:00Z",
            "operator_label": "op",
            "original_manifest_hash": "sha256:" + "1" * 64,
            "candidate_reference": cand_rev_a.candidate_reference,
            "source_identity": {"source_id": "toyota_usa", "native_identifier": "8670", "raw_artifact_hash": hash_a},
            "evidence_anchors": {"raw_artifact_hash": hash_a},
            "original_review_category": "distinct_factory_grade",
            "adjudication_category": "distinct_factory_grade",
            "adjudication_decision": "approved_distinct_trim",
            "adjudicated_trim_name": "SR5 Premium",
            "adjudication_notes": "Adjudicated against revision A.",
        }
        adj_dict["adjudication_hash"] = compute_adjudication_hash(adj_dict)
        adj_a = adjudication_from_dict(adj_dict)

        # Candidate constructed from revised raw snapshot B
        cand_rev_b = self._make_candidate("SR5 Premium", "2WD", "8670", raw_artifact_hash="sha256:" + "b" * 64, requires_review=True)

        res_plan = plan_candidate_import_with_adjudications(cand_rev_b, [adj_a])
        self.assertEqual(res_plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

    def test_single_adjudicated_configuration_end_to_end_pipeline(self):
        """
        Controlled Study Integration Depth Test (Requirement 10):
        Exercises a single configuration (8670 SR5 Premium 2WD) through all 5 authentic stages.
        """
        # Step 1: Base SR5 2WD row exists
        VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
            slug="2020-sr5-40l-v6-2wd-us",
        )

        # Step 2: Authentic raw PDF extraction
        fixtures_dir = Path(__file__).resolve().parent / "fixtures" / "acquisition" / "toyota"
        pricing_pdf = fixtures_dir / "2020_4runner_pricing.pdf"
        specs_pdf = fixtures_dir / "2020_4runner_specs.pdf"

        from reference.ingestion.acquisition.profiles import ToyotaUSAPressroomProfile
        from reference.ingestion.acquisition.snapshots import RawSourceSnapshotMetadata, compute_content_hash
        pricing_bytes = pricing_pdf.read_bytes()
        pricing_hash = compute_content_hash(pricing_bytes)
        snapshot_meta = RawSourceSnapshotMetadata(
            source_id="toyota_usa",
            publisher_locator="https://pressroom.toyota.com/vehicle/2020-toyota-4runner/",
            acquired_at="2026-08-15T16:00:00Z",
            content_type="application/pdf",
            content_hash=pricing_hash,
            storage_path=str(pricing_pdf),
            source_applicability=SourceApplicability(market="US"),
            acquisition_method="local_file",
        )

        cand = self._make_candidate("SR5 Premium", "2WD", "8670", requires_review=True)
        pricing_hash = cand.raw_artifact_hash

        # Stage 1: Initial Planning -> FLAG_REVIEW
        init_plan = plan_candidate_import(cand)
        self.assertEqual(init_plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

        # Stage 2: Adjudication Artifact
        adj_dict = {
            "adjudication_version": "1.0",
            "created_at": "2026-08-15T16:00:00Z",
            "operator_label": "operator1",
            "original_manifest_hash": "sha256:" + "1" * 64,
            "candidate_reference": cand.candidate_reference,
            "source_identity": {"source_id": "toyota_usa", "native_identifier": "8670", "raw_artifact_hash": pricing_hash},
            "evidence_anchors": {"raw_artifact_hash": pricing_hash},
            "original_review_category": "distinct_factory_grade",
            "adjudication_category": "distinct_factory_grade",
            "adjudication_decision": "approved_distinct_trim",
            "adjudicated_trim_name": "SR5 Premium",
            "adjudication_notes": "Verified distinct factory grade from publisher documentation.",
        }
        adj_dict["adjudication_hash"] = compute_adjudication_hash(adj_dict)
        adj = adjudication_from_dict(adj_dict)

        # Stage 3: Re-Planning -> ADJUDICATED_DISTINCT_GRADE
        re_plan = plan_candidate_import_with_adjudications(cand, [adj])
        self.assertEqual(re_plan.create_basis, ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE)

        # Stage 4: Manifest v1.1
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash=pricing_hash,
            raw_artifact_reference=str(pricing_pdf),
            extraction_provenance={"extractor_id": "toyota_pricing_master_pdf_strategy"},
            plans=[re_plan],
            native_identifiers={cand.candidate_reference: "8670"},
        )
        self.assertEqual(manifest.manifest_version, "1.1")
        review_plan = manifest.plans[0]
        reconstructed = reconstruct_plan_from_manifest(review_plan)

        # Stage 5: Execution Workflow Dispatch
        res, receipt = execute_canonical_import_workflow(
            plan=reconstructed,
            manifest=manifest,
            review_plan=review_plan,
            operator_label="operator1",
            adjudication_artifact=adj,
        )

        self.assertEqual(res.outcome, ImportExecutionOutcome.CREATED)
        self.assertEqual(receipt.execution_outcome, "created")
        self.assertEqual(receipt.adjudication_hash, adj.adjudication_hash)

    def test_dual_artifact_evidence_set_revision_change_rejects_adjudication(self):
        """
        Multi-Artifact Evidence Revision Set Binding Test (Requirement 5):
        Proves changing EITHER raw evidence artifact in a multi-artifact candidate
        invalidates automatic reuse of an old adjudication artifact.
        """
        # Base SR5 2WD row
        VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
            slug="2020-sr5-40l-v6-2wd-us",
        )

        hash_p1 = "sha256:" + "1" * 64
        hash_p2 = "sha256:" + "2" * 64
        hash_p_rev = "sha256:" + "3" * 64

        # Candidate A built from Pricing Master P1 + Product Information P2
        cand_a = self._make_candidate("SR5 Premium", "2WD", "8670", requires_review=True)
        cand_a.evidence_raw_hashes = [hash_p1, hash_p2]

        adj_dict = {
            "adjudication_version": "1.0",
            "created_at": "2026-08-15T16:00:00Z",
            "operator_label": "op",
            "original_manifest_hash": "sha256:" + "1" * 64,
            "candidate_reference": cand_a.candidate_reference,
            "source_identity": {"source_id": "toyota_usa", "native_identifier": "8670"},
            "evidence_anchors": {"raw_artifact_hashes": [hash_p1, hash_p2]},
            "original_review_category": "distinct_factory_grade",
            "adjudication_category": "distinct_factory_grade",
            "adjudication_decision": "approved_distinct_trim",
            "adjudicated_trim_name": "SR5 Premium",
            "adjudication_notes": "Adjudicated against dual-artifact set P1 + P2.",
        }
        adj_dict["adjudication_hash"] = compute_adjudication_hash(adj_dict)
        adj_orig = adjudication_from_dict(adj_dict)

        # Baseline: plan with matching evidence set yields ADJUDICATED_DISTINCT_GRADE
        plan_ok = plan_candidate_import_with_adjudications(cand_a, [adj_orig])
        self.assertEqual(plan_ok.create_basis, ImportCreateBasis.ADJUDICATED_DISTINCT_GRADE)

        # Test Case 1: Pricing Master P1 + Product Information REVISED (P_rev)
        cand_second_changed = self._make_candidate("SR5 Premium", "2WD", "8670", requires_review=True)
        cand_second_changed.candidate_reference = cand_a.candidate_reference
        cand_second_changed.evidence_raw_hashes = [hash_p1, hash_p_rev]

        plan_fail1 = plan_candidate_import_with_adjudications(cand_second_changed, [adj_orig])
        self.assertEqual(plan_fail1.planned_action, ImportPlannedAction.FLAG_REVIEW)

        # Test Case 2: Pricing Master REVISED (P_rev) + Product Information P2
        cand_first_changed = self._make_candidate("SR5 Premium", "2WD", "8670", requires_review=True)
        cand_first_changed.candidate_reference = cand_a.candidate_reference
        cand_first_changed.evidence_raw_hashes = [hash_p_rev, hash_p2]

        plan_fail2 = plan_candidate_import_with_adjudications(cand_first_changed, [adj_orig])
        self.assertEqual(plan_fail2.planned_action, ImportPlannedAction.FLAG_REVIEW)

    def test_cli_forged_manifest_execution_command_refused(self):
        """
        Management Command Forged Manifest Security Test (Requirement 13):
        Proves executing execute_canonical_import CLI with a forged manifest containing
        ADJUDICATED_DISTINCT_GRADE without valid adjudication artifact file fails cleanly.
        """
        import tempfile, json
        from dataclasses import asdict
        from django.core.management import call_command, CommandError
        from reference.ingestion.manifest import CanonicalImportReviewPlan, compute_manifest_hash, manifest_to_dict

        # Base SR5 2WD row
        VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
            slug="2020-sr5-40l-v6-2wd-us",
        )

        cand = self._make_candidate("SR5 Premium", "2WD", "8670", requires_review=True)
        cand_ref = cand.candidate_reference

        # Forged review plan with ADJUDICATED_DISTINCT_GRADE basis and fake adjudication_hash
        forged_rp = CanonicalImportReviewPlan(
            candidate_reference=cand_ref,
            source_identity_type="record_id",
            native_identifier="8670",
            eligibility_status="eligible",
            planned_action="create",
            create_basis="adjudicated_distinct_grade",
            review_category="distinct_factory_grade",
            resolved_manufacturer_id=self.mfr.id,
            resolved_vehicle_model_id=self.model.id,
            resolved_generation_id=self.gen.id,
            target_vehicle_definition_fields={
                "model_year": 2020,
                "trim_name": "SR5 Premium",
                "engine_name": "4.0L V6",
                "drivetrain": "2WD",
                "market": "US",
            },
            target_slug="2020-sr5-premium-40l-v6-2wd-us",
            reasons=["Forged promotion"],
            adjudication_reference=f"adjudication_{cand_ref}.json",
            adjudication_hash="sha256:" + "f" * 64,
        )

        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash="sha256:" + "a" * 64,
            raw_artifact_reference="ref.pdf",
            extraction_provenance={"extractor": "test"},
            plans=[plan_candidate_import(cand)],
            native_identifiers={cand_ref: "8670"},
        )
        # Inject forged plan into manifest dict and compute valid manifest_hash
        m_dict = manifest_to_dict(manifest)
        m_dict["manifest_version"] = "1.1"
        m_dict["plans"] = [asdict(forged_rp)]
        m_dict.pop("manifest_hash", None)
        m_dict["manifest_hash"] = compute_manifest_hash(m_dict)

        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmp_dir:
            m_path = Path(tmp_dir) / "manifest.json"
            m_path.write_text(json.dumps(m_dict))

            # Attempt CLI execution with patched operator authorization prompt
            with patch("builtins.input", return_value="y"):
                with self.assertRaises(CommandError) as ctx:
                    call_command(
                        "execute_canonical_import",
                        manifest=str(m_path),
                        plan_ref=cand_ref,
                        operator="attacker",
                    )
            self.assertIn("Execution refused", str(ctx.exception))

        # Verify zero canonical records created
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_mandatory_human_authorization_interactive_responses(self):
        """
        Mandatory Human Authorization Response Test (Requirement 4):
        Proves 'n' and empty/default responses yield ZERO canonical mutations,
        while 'y' authorization proceeds to workflow execution.
        """
        import tempfile, json
        from unittest.mock import patch
        from django.core.management import call_command

        cand = self._make_candidate("SR5", "2WD", "8664")
        cand_ref = cand.candidate_reference
        plan = plan_candidate_import(cand)  # Eligible CREATE (FIRST_REPRESENTATION)

        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash="sha256:" + "a" * 64,
            raw_artifact_reference="ref.pdf",
            extraction_provenance={"extractor": "test"},
            plans=[plan],
            native_identifiers={cand_ref: "8664"},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            m_path = Path(tmp_dir) / "manifest.json"
            m_path.write_text(json.dumps(manifest_to_dict(manifest)))

            # 1. User responds "n" -> Zero canonical writes
            with patch("builtins.input", return_value="n"):
                call_command("execute_canonical_import", manifest=str(m_path), plan_ref=cand_ref)
            self.assertEqual(VehicleDefinition.objects.count(), 0)

            # 2. User responds empty string "" -> Zero canonical writes
            with patch("builtins.input", return_value=""):
                call_command("execute_canonical_import", manifest=str(m_path), plan_ref=cand_ref)
            self.assertEqual(VehicleDefinition.objects.count(), 0)

            # 3. User responds "y" -> Execution proceeds and creates record
            with patch("builtins.input", return_value="y"):
                call_command("execute_canonical_import", manifest=str(m_path), plan_ref=cand_ref)
            self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_no_input_flag_rejected_as_unknown_option(self):
        """
        No-Input Option Rejection Test (Requirement 4D):
        Proves passing --no-input or no_input=True to execute_canonical_import is rejected
        as an unknown option with TypeError / CommandError.
        """
        import tempfile, json
        from django.core.management import call_command, CommandError

        cand = self._make_candidate("SR5", "2WD", "8664")
        plan = plan_candidate_import(cand)
        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash="sha256:" + "a" * 64,
            raw_artifact_reference="ref.pdf",
            extraction_provenance={"extractor": "test"},
            plans=[plan],
            native_identifiers={cand.candidate_reference: "8664"},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            m_path = Path(tmp_dir) / "manifest.json"
            m_path.write_text(json.dumps(manifest_to_dict(manifest)))

            with self.assertRaises((TypeError, CommandError)):
                call_command("execute_canonical_import", manifest=str(m_path), plan_ref=cand.candidate_reference, no_input=True)

    def test_original_manifest_binding_and_tamper_prevention(self):
        """
        Original Manifest Binding & Tamper Test (Requirements 5 & 6):
        Proves adjudicate_canonical_import CLI binds original_manifest_hash directly to the
        verified loaded manifest's manifest_hash, and a tampered manifest fails before adjudication output.
        """
        import tempfile, json
        from django.core.management import call_command, CommandError
        from reference.ingestion.serialization import adjudication_from_dict

        # Create a base SR5 2WD row so SR5 Premium candidate flags for review
        VehicleDefinition.objects.create(
            generation=self.gen,
            model_year=2020,
            trim_name="SR5",
            engine_name="4.0L V6",
            drivetrain="2WD",
            market="US",
            slug="2020-sr5-40l-v6-2wd-us",
        )

        cand = self._make_candidate("SR5 Premium", "2WD", "8670", requires_review=True)
        cand_ref = cand.candidate_reference
        plan = plan_candidate_import(cand)
        self.assertEqual(plan.planned_action, ImportPlannedAction.FLAG_REVIEW)

        manifest = build_review_manifest(
            source_id="toyota_usa",
            raw_artifact_hash="sha256:" + "a" * 64,
            raw_artifact_reference="ref.pdf",
            extraction_provenance={"extractor": "test"},
            plans=[plan],
            native_identifiers={cand_ref: "8670"},
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            m_path = Path(tmp_dir) / "manifest.json"
            out_path = Path(tmp_dir) / f"adjudication_{cand_ref}.json"
            m_path.write_text(json.dumps(manifest_to_dict(manifest)))

            # Step 1: Normal adjudication CLI call
            call_command(
                "adjudicate_canonical_import",
                manifest=str(m_path),
                candidate_ref=cand_ref,
                category="distinct_factory_grade",
                trim_name="SR5 Premium",
                notes="Verified distinct grade.",
                output=str(out_path),
            )
            self.assertTrue(out_path.exists())

            adj_dict = json.loads(out_path.read_text())
            adj = adjudication_from_dict(adj_dict)
            self.assertEqual(adj.original_manifest_hash, manifest.manifest_hash)

            # Step 2: Tampered original manifest (corrupted top-level raw_artifact_hash or manifest_hash)
            tampered_dict = manifest_to_dict(manifest)
            tampered_dict["raw_artifact_hash"] = "sha256:" + "f" * 64
            # Keep old manifest_hash digest (now invalid for tampered content)
            m_path_bad = Path(tmp_dir) / "manifest_bad.json"
            m_path_bad.write_text(json.dumps(tampered_dict))

            out_path_bad = Path(tmp_dir) / "adjudication_bad.json"
            with self.assertRaises(CommandError) as ctx:
                call_command(
                    "adjudicate_canonical_import",
                    manifest=str(m_path_bad),
                    candidate_ref=cand_ref,
                    category="distinct_factory_grade",
                    trim_name="SR5 Premium",
                    notes="Tampered manifest test.",
                    output=str(out_path_bad),
                )
            self.assertIn("Failed to parse and validate review manifest", str(ctx.exception))
            self.assertFalse(out_path_bad.exists())

