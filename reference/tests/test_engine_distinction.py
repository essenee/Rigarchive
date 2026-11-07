"""Engine creates use retained source evidence and revalidate it at execution."""
from pathlib import Path

from django.test import TestCase

from reference.ingestion.importing.matrix_workflow import MatrixExecutionError, _references, execute_matrix_year
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.matrix_approval import build_matrix_approval
from reference.models import ImportExecutionReceipt, VehicleDefinition
from reference.tests.test_generation_correspondence import SyntheticWranglerSetup


class EngineDistinctionTests(SyntheticWranglerSetup, TestCase):
    def setUp(self):
        super().setUp()
        self.jk.is_active = False
        self.jk.save(update_fields=["is_active"])
        self.v6 = self.make_candidate(None, engine=(3.6, 6, "3.6L V6"))
        self.turbo = self.make_candidate(None, engine=(2.0, 4, "2.0L Turbo I4"))

    def test_exact_match_and_stale_peer_evidence(self):
        plan, manifest = self.plan_and_manifest(self.v6)
        created, _ = self.execute(plan, manifest)
        self.assertEqual(created.outcome.value, "created")
        exact = plan_candidate_import(self.v6)
        self.assertEqual(exact.planned_action.value, "no_op_exact_match")
        self.assertEqual(exact.existing_vehicle_definition_id, created.vehicle_definition_id)

        turbo, manifest = self.plan_and_manifest(self.turbo)
        self.assertEqual(turbo.create_basis.value, "mechanical_dimension")
        self.assertEqual(turbo.generation_resolution["engine_distinction"]["candidate_engine"], [2.0, 4, "I"])
        source = Path(self.root) / self.v6.evidence_documents[0]["raw_artifact_reference"]
        source.write_bytes(source.read_bytes() + b" ")
        outcome, _ = self.execute(turbo, manifest)
        self.assertEqual(outcome.outcome.value, "aborted_stale_plan")
        self.assertEqual(VehicleDefinition.objects.count(), 1)

    def test_equivalent_engine_label_stays_in_review(self):
        plan, manifest = self.plan_and_manifest(self.v6)
        self.execute(plan, manifest)
        equivalent = self.make_candidate(None, engine=(3.6, 6, "Alternative 3.6L V6"))
        self.assertEqual(plan_candidate_import(equivalent).planned_action.value, "flag_review")
        unsupported = self.make_candidate(None)
        self.assertEqual(plan_candidate_import(unsupported).planned_action.value, "flag_review")

    def test_unproven_existing_engine_and_occupied_slug_stay_blocked(self):
        legacy = self.make_candidate(None)
        plan, manifest = self.plan_and_manifest(legacy)
        self.execute(plan, manifest)
        VehicleDefinition.objects.create(
            generation=self.jl, model_year=2018, market="US", trim_name="Synthetic Sport",
            engine_name="3.6L V6", drivetrain="2WD",
        )
        self.assertEqual(plan_candidate_import(self.turbo).planned_action.value, "flag_review")
        VehicleDefinition.objects.create(
            generation=self.jl, model_year=2018, market="US", trim_name="Synthetic Sport",
            engine_name="2.0L Turbo I4", drivetrain="4WD", is_active=False,
        )
        self.assertEqual(plan_candidate_import(self.turbo).review_category.value, "slug_conflict")

    def test_ambiguous_or_conflicting_descriptor_stays_in_review(self):
        plan, manifest = self.plan_and_manifest(self.v6)
        self.execute(plan, manifest)
        for engine in ((2.0, 4, "2.0L I4 or 3.6L V6"), (2.0, 6, "2.0L I4")):
            with self.subTest(engine=engine):
                candidate = self.make_candidate(None, engine=engine)
                self.assertEqual(plan_candidate_import(candidate).planned_action.value, "flag_review")

    def _run_dual_engine_matrix(self, ordered, *, expect_rollback=False):
        candidates = {c.candidate_reference: c for c in ordered}
        rows = []
        for index, candidate in enumerate(ordered):
            plan = plan_candidate_import(candidate)
            evidence, correspondence = _references(plan)
            rows.append({
                "row_id": f"engine-{index}", "model_year": 2018, "target_fields": plan.target_vehicle_definition_fields,
                "target_slug": plan.target_slug, "action": "create",
                "permitted_create_bases": ["first_representation", "mechanical_dimension"],
                "candidate_reference": candidate.candidate_reference, "candidate_digest": plan.candidate_hash,
                "evidence": evidence, "correspondence": correspondence, "existing_record": None,
                "generation_binding": {"mode": "unique_deterministic", "strategy": "unique_year_range",
                                       "resolution_version": "1.0"},
            })
        matrix = {
            "matrix_version": "2.0", "model_years": [2018], "market": "US", "rows": rows,
            "parents": {key: {"pk": obj.pk, "uuid": str(obj.uuid), "slug": obj.slug}
                        for key, obj in (("manufacturer", self.make), ("vehicle_model", self.model),
                                         ("generation", self.jl))},
        }
        approval = build_matrix_approval(matrix, operator="test", confirmed=True)
        if expect_rollback:
            with self.assertRaises(MatrixExecutionError):
                execute_matrix_year(matrix, approval, 2018, candidates, self.root, execution_operator="test")
            self.assertFalse(VehicleDefinition.objects.exists())
            self.assertFalse(ImportExecutionReceipt.objects.filter(operation_type="vehicle_definition_import").exists())
            return
        _, report = execute_matrix_year(matrix, approval, 2018, candidates, self.root, execution_operator="test")
        self.assertEqual([r["status"] for r in report["rows"]], ["newly_created", "newly_created"])
        self.assertEqual(set(VehicleDefinition.objects.values_list("engine_name", flat=True)),
                         {"3.6L V6", "2.0L Turbo I4"})

    def test_matrix_creates_v6_then_turbo(self):
        self._run_dual_engine_matrix([self.v6, self.turbo])

    def test_matrix_creates_turbo_then_v6(self):
        self._run_dual_engine_matrix([self.turbo, self.v6])


    def test_unproven_second_engine_rolls_back_year(self):
        self._run_dual_engine_matrix([self.make_candidate(None), self.turbo], expect_rollback=True)
