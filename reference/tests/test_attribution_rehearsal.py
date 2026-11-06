from pathlib import Path
import json
import sqlite3
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from reference.ingestion.attribution_rehearsal import (
    apply_receipt_changes, approval_change, check_isolation, file_digest,
    portable_reference, privacy_scan, receipt_changes,
)
from reference.ingestion.matrix import compute_matrix_digest
from reference.ingestion.matrix_approval import build_matrix_approval
from reference.tests.test_generation_trim_matrix import sample


class AttributionRehearsalTests(SimpleTestCase):
    def test_approval_hash_changes_without_matrix_change(self):
        matrix = sample()
        before = compute_matrix_digest(matrix)
        approval = build_matrix_approval(matrix, operator="cli:synthetic_person", confirmed=True)
        (old, new), raw = approval_change(matrix, approval, "cli:synthetic_person")
        self.assertNotEqual(old, new)
        self.assertEqual(json.loads(raw)["operator"], "legacy_cli_operator")
        self.assertEqual(json.loads(raw)["approved_at_utc"], approval["approved_at_utc"])
        self.assertEqual(compute_matrix_digest(matrix), before)
        self.assertEqual(approval["operator"], "cli:synthetic_person")

    def test_reference_classes(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "fixture.json"
            path.write_bytes(b"{}")
            self.assertEqual(portable_reference(str(path), file_digest(path), root), ("fixture.json", "verified_portable"))
            self.assertEqual(portable_reference(str(path), "wrong", root), ("unavailable:receipt-source", "digest_mismatch"))
            self.assertEqual(portable_reference(str(root / "absent"), "wrong", root), ("unavailable:receipt-source", "missing"))
            self.assertEqual(portable_reference(str(path), file_digest(path), root / "elsewhere")[1], "outside_managed_root")

    def test_isolation_rejects_live_input_alias_and_existing_output(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            repo = root / "repo"
            repo.mkdir()
            live = repo / "db.sqlite3"
            live.touch()
            snap = root / "snapshot.sqlite3"
            snap.touch()
            check_isolation(repo, snap, root / "new")
            for source, output in ((live, root / "new"), (snap, repo / "new"), (snap, snap)):
                with self.subTest(source=source.name, output=output.name), self.assertRaises(ValueError):
                    check_isolation(repo, source, output)
            alias = root / "alias.sqlite3"
            alias.hardlink_to(live)
            with self.assertRaises(ValueError):
                check_isolation(repo, alias, root / "new")

    def test_receipt_pin_and_compaction_preserve_other_fields(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            home = root / "synthetic_person"
            work, compact = root / "work.sqlite3", root / "compact.sqlite3"
            with sqlite3.connect(work) as db:
                db.execute("CREATE TABLE reference_importexecutionreceipt (id INTEGER PRIMARY KEY, "
                           "operator_label TEXT, raw_artifact_reference TEXT, raw_artifact_hash TEXT, "
                           "resolution_snapshot_json TEXT, manifest_hash TEXT)")
                db.execute("INSERT INTO reference_importexecutionreceipt VALUES (?,?,?,?,?,?)",
                           (1, "cli:synthetic_person", str(home / "missing"), "source-digest",
                            json.dumps({"matrix": {"approval_digest": "old", "matrix_digest": "matrix"},
                                        "candidate_hash": "candidate"}), "manifest"))
                changes = receipt_changes(db, root, home, {"old": "new"})
                self.assertEqual(changes, receipt_changes(db, root, home, {"old": "new"}))
                apply_receipt_changes(db, changes)
                db.commit()
                db.execute("VACUUM INTO ?", (str(compact),))
                self.assertEqual(receipt_changes(db, root, home, {"old": "new"}), [])
            self.assertFalse(privacy_scan(compact, home))
            with sqlite3.connect(compact) as db:
                _, operator, ref, source, snapshot, manifest = db.execute(
                    "SELECT * FROM reference_importexecutionreceipt",
                ).fetchone()
            self.assertEqual((operator, ref, source, manifest),
                             ("legacy_cli_operator", "unavailable:receipt-source", "source-digest", "manifest"))
            self.assertEqual(json.loads(snapshot), {"matrix": {"approval_digest": "new", "matrix_digest": "matrix"},
                                                   "candidate_hash": "candidate"})
