"""Pure approval artifact tests; no Django database required."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from reference.ingestion.matrix_approval import (
    MatrixApprovalError, build_matrix_approval, read_matrix_approval,
    serialize_matrix_approval, validate_matrix_approval,
)
from reference.tests.test_generation_trim_matrix import sample


class MatrixApprovalTests(unittest.TestCase):
    def setUp(self):
        self.matrix = sample()
        self.approval = build_matrix_approval(
            self.matrix, operator="local-reviewer", confirmed=True,
            approved_at=datetime(2026, 11, 5, 20, 30, tzinfo=timezone.utc),
        )

    def test_approval_round_trip(self):
        payload = serialize_matrix_approval(self.matrix, self.approval)
        self.assertEqual(payload, serialize_matrix_approval(self.matrix, self.approval))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "approval.json"
            path.write_bytes(payload)
            self.assertEqual(read_matrix_approval(path, self.matrix), self.approval)

    def test_confirmation_required(self):
        with self.assertRaises(MatrixApprovalError):
            build_matrix_approval(self.matrix, operator="reviewer", confirmed=False)

    def test_matrix_mutation_invalidates_approval(self):
        changed = copy.deepcopy(self.matrix)
        changed["rows"][0]["candidate_digest"] = "sha256:" + "b" * 64
        with self.assertRaises(MatrixApprovalError):
            validate_matrix_approval(changed, self.approval)

    def test_wrong_digest_rejected(self):
        changed = dict(self.approval, matrix_digest="sha256:" + "0" * 64)
        with self.assertRaises(MatrixApprovalError):
            validate_matrix_approval(self.matrix, changed)

    def test_nonaffirmative_or_missing_attribution_rejected(self):
        for change in ({"decision": "rejected"}, {"operator": ""}, {"operator": " * "}):
            with self.subTest(change=change), self.assertRaises(MatrixApprovalError):
                validate_matrix_approval(self.matrix, dict(self.approval, **change))

    def test_malformed_or_extra_fields_rejected(self):
        for change in ({"approved_at_utc": "2026-11-05T12:30:00-08:00"},
                       {"approved_at_utc": "tomorrow"}, {"progress": "done"}):
            with self.subTest(change=change), self.assertRaises(MatrixApprovalError):
                validate_matrix_approval(self.matrix, dict(self.approval, **change))

    def test_naive_and_non_utc_time_rejected(self):
        for when in (datetime(2026, 11, 5), datetime(2026, 11, 5, tzinfo=timezone(timedelta(hours=-8)))):
            with self.subTest(when=when), self.assertRaises(MatrixApprovalError):
                build_matrix_approval(self.matrix, operator="reviewer", confirmed=True, approved_at=when)

    def test_missing_or_invalid_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "approval.json"
            with self.assertRaises(MatrixApprovalError):
                read_matrix_approval(path, self.matrix)
            path.write_text("{bad json", encoding="utf-8")
            with self.assertRaises(MatrixApprovalError):
                read_matrix_approval(path, self.matrix)

    def test_approval_is_not_part_of_matrix_digest(self):
        from reference.ingestion.matrix import compute_matrix_digest
        before = compute_matrix_digest(self.matrix)
        validate_matrix_approval(self.matrix, self.approval)
        self.assertEqual(before, compute_matrix_digest(self.matrix))
        self.assertNotIn("approval", self.matrix)


if __name__ == "__main__":
    unittest.main()
