"""Pure Stage 6B matrix contract tests; no Django database required."""
import copy
import unittest

from reference.ingestion.matrix import MatrixValidationError, compute_matrix_digest

H = "sha256:" + "a" * 64
U = "12345678-1234-4234-8234-123456789abc"


def sample():
    return {
        "matrix_version": "1.0",
        "parents": {name: {"pk": i, "uuid": U, "slug": name.replace("_", "-")} for i, name in enumerate(("manufacturer", "vehicle_model", "generation"), 1)},
        "market": "US", "model_years": [2007, 2008],
        "rows": [
            {"row_id": "jk-2008-sport", "model_year": 2008,
             "target_fields": {"model_year": 2008, "trim_name": "Sport", "engine_name": "3.8L V6", "drivetrain": "4WD", "market": "US"},
             "target_slug": "2008-sport-v6-4wd-us", "action": "create",
             "permitted_create_bases": ["mechanical_dimension", "first_representation"],
             "candidate_reference": "candidate-2008-sport", "candidate_digest": H,
             "evidence": [{"reference": "brochure", "digest": H}],
             "correspondence": [{"reference": "jk-correspondence", "digest": H}],
             "existing_record": None},
            {"row_id": "jk-2007-sport", "model_year": 2007,
             "target_fields": {"model_year": 2007, "trim_name": "Sport", "engine_name": "3.8L V6", "drivetrain": "4WD", "market": "US"},
             "target_slug": "2007-sport-v6-4wd-us", "action": "reviewed_existing",
             "permitted_create_bases": [], "candidate_reference": "candidate-2007-sport", "candidate_digest": H,
             "evidence": [{"reference": "brochure", "digest": H}],
             "correspondence": [{"reference": "jk-correspondence", "digest": H}],
             "existing_record": {"pk": 100, "uuid": U, "slug": "2007-sport-v6-4wd-us"}},
        ],
    }


class MatrixContractTests(unittest.TestCase):
    def test_deterministic_and_input_unchanged(self):
        matrix = sample()
        before = copy.deepcopy(matrix)
        digest = compute_matrix_digest(matrix)
        self.assertEqual(matrix, before)
        self.assertEqual(digest, compute_matrix_digest(matrix))
        matrix["rows"].reverse()
        matrix["rows"][1]["permitted_create_bases"].reverse()
        self.assertEqual(digest, compute_matrix_digest(matrix))

    def test_material_change_changes_digest(self):
        matrix = sample()
        old = compute_matrix_digest(matrix)
        matrix["rows"][0]["candidate_digest"] = "sha256:" + "b" * 64
        self.assertNotEqual(old, compute_matrix_digest(matrix))

    def test_duplicate_slug_rejected(self):
        matrix = sample()
        matrix["rows"][1]["target_slug"] = matrix["rows"][0]["target_slug"]
        with self.assertRaises(MatrixValidationError):
            compute_matrix_digest(matrix)

    def test_execution_metadata_rejected(self):
        matrix = sample()
        matrix["completed_count"] = 0
        with self.assertRaises(MatrixValidationError):
            compute_matrix_digest(matrix)

    def test_existing_must_be_pinned(self):
        matrix = sample()
        matrix["rows"][1]["existing_record"] = None
        with self.assertRaises(MatrixValidationError):
            compute_matrix_digest(matrix)

    def test_wildcard_rejected(self):
        matrix = sample()
        matrix["rows"][0]["candidate_reference"] = "*"
        with self.assertRaises(MatrixValidationError):
            compute_matrix_digest(matrix)


if __name__ == "__main__":
    unittest.main()
