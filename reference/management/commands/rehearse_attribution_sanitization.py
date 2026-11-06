"""Rehearse known historical attribution changes on an offline SQLite snapshot."""
from collections import Counter
from pathlib import Path
import json
import shutil
import sqlite3
import tempfile
import subprocess
from urllib.parse import quote

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from reference.ingestion.attribution_rehearsal import (
    LEGACY_OPERATOR, apply_receipt_changes, approval_change, check_isolation,
    file_digest, privacy_scan, receipt_changes, summarize,
)
from reference.ingestion.importing.matrix_workflow import MatrixYear
from reference.ingestion.manifest import dict_to_manifest
from reference.ingestion.matrix import compute_matrix_digest
from reference.ingestion.serialization import deserialize_artifact


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def preserve_tables(db, source, changes):
    db.execute("ATTACH DATABASE ? AS baseline", (source.as_uri() + "?mode=ro&immutable=1",))
    expected = {pk: fields for pk, fields, _, _ in changes}
    db.row_factory = sqlite3.Row
    for (table,) in db.execute("SELECT name FROM main.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        if table == "reference_importexecutionreceipt":
            prior = [dict(row) for row in db.execute(f'SELECT * FROM baseline."{table}" ORDER BY id')]
            actual = [dict(row) for row in db.execute(f'SELECT * FROM main."{table}" ORDER BY id')]
            if [row | expected.get(row["id"], {}) for row in prior] != actual:
                raise ValueError("Receipt preservation check failed.")
        else:
            for a, b in (("main", "baseline"), ("baseline", "main")):
                if db.execute(f'SELECT 1 FROM (SELECT * FROM {a}."{table}" EXCEPT '
                              f'SELECT * FROM {b}."{table}") LIMIT 1').fetchone():
                    raise ValueError(f"Unrelated table changed: {table}.")


class Command(BaseCommand):
    help = "Rehearse historical attribution sanitization on an external snapshot and new output tree."

    def add_arguments(self, parser):
        parser.add_argument("--database", required=True)
        parser.add_argument("--review-root", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument("--privacy-input", required=True, help="Private file containing the exact identifying home prefix.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            self.rehearse(options)
        except (ValueError, OSError, sqlite3.Error) as exc:
            raise CommandError(str(exc)) from exc

    def rehearse(self, options):
        original_name, original_base = connection.settings_dict["NAME"], settings.BASE_DIR
        try:
            self._rehearse(options)
        finally:
            if connection.settings_dict["NAME"] != original_name:
                connection.close()
                connection.settings_dict["NAME"] = original_name
                settings.BASE_DIR = original_base

    def _rehearse(self, options):
        repo = Path(settings.BASE_DIR).resolve()
        source = Path(options["database"]).absolute()
        output = Path(options["output"]).absolute()
        review = Path(options["review_root"]).resolve()
        home = Path(Path(options["privacy_input"]).read_text().strip())
        if not home.is_absolute() or not home.name or connection.settings_dict["NAME"] != Path(":memory:"):
            raise ValueError("Explicit home prefix and an in-memory Django bootstrap are required.")
        check_isolation(repo, source, output)
        if not review.is_dir() or output.resolve().is_relative_to(review):
            raise ValueError("Review input must be a directory separate from output.")
        if any(p.is_symlink() for root in (review, repo / "storage") for p in root.rglob("*")):
            raise ValueError("Review and evidence trees must not contain symlinks.")
        source = source.resolve()
        legacy = f"cli:{home.name}"
        crosswalk, replacements, packages = {}, {}, []
        for approval_path in sorted(review.rglob("approval.json")):
            approval = read(approval_path)
            if approval.get("operator") != legacy:
                continue
            folder = approval_path.parent
            matrix_path = folder / ("matrix.json" if (folder / "matrix.json").exists() else "draft-matrix.json")
            matrix = read(matrix_path)
            (old, new), raw = approval_change(matrix, approval, legacy)
            if old in crosswalk and crosswalk[old] != new:
                raise ValueError("Inconsistent approval digest replacement.")
            crosswalk[old] = new
            replacements[approval_path.relative_to(review)] = raw
            if matrix_path.name == "matrix.json":
                packages.append((folder.relative_to(review), matrix, old))
        with sqlite3.connect(source.as_uri() + "?mode=ro&immutable=1", uri=True) as src:
            changes = receipt_changes(src, repo, home, crosswalk)
            pins = Counter(pin for _, _, _, pin in changes if pin)
            package_counts = Counter()
            for _, matrix, old in packages:
                package_counts[old] += len(matrix["rows"])
            if pins != package_counts or not packages:
                raise ValueError("Copied attempts and receipt approval bindings do not reconcile.")
            summary = summarize(changes) | {"approval_crosswalk": crosswalk, "execution_packages": len(packages)}
            if options["dry_run"]:
                self.stdout.write(json.dumps(summary, sort_keys=True))
                return

            output.mkdir(mode=0o700)
            original_digests = {
                "snapshot": file_digest(source),
                "review": {p.relative_to(review).as_posix(): file_digest(p)
                           for p in sorted(review.rglob("*")) if p.is_file()},
                "storage": {p.relative_to(repo / "storage").as_posix(): file_digest(p)
                            for p in sorted((repo / "storage").rglob("*")) if p.is_file()},
            }
            shutil.copytree(review, output / "review")
            shutil.copytree(repo / "storage", output / "storage")
            portable_paths = {
                fields["raw_artifact_reference"] for _, fields, kind, _ in changes if kind == "verified_portable"
            }
            for rel in sorted(portable_paths):
                target = output / rel
                source_file = repo / rel
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source_file, target)
                if file_digest(target) != file_digest(source_file):
                    raise ValueError("Portable evidence copy differs from source.")
            original_digests["portable_sources"] = {rel: file_digest(repo / rel) for rel in sorted(portable_paths)}
            for rel, raw in replacements.items():
                (output / "review" / rel).write_bytes(raw)
            for rel, matrix, old in packages:
                folder = output / "review" / rel
                for name in ("operators.json", "result.json", "preflight.json", "failure.json"):
                    path = folder / name
                    if not path.is_file():
                        continue
                    obj = read(path)
                    for key in ("approval_operator", "execution_operator"):
                        if obj.get(key) == legacy:
                            obj[key] = LEGACY_OPERATOR
                    if obj.get("approval_digest") == old:
                        obj["approval_digest"] = crosswalk[old]
                    write(path, obj)
            for path in (output / "review").rglob("execution-summary.json"):
                obj = read(path)
                for row in obj.get("completed", []):
                    value = row.get("result", "")
                    if value.startswith(str(review) + "/"):
                        row["result"] = str(Path(value).relative_to(review))
                write(path, obj)
            # Text documentation only. Never apply these substitutions to source artifacts.
            tracked = subprocess.check_output(["git", "--no-optional-locks", "-C", str(repo), "ls-files", "-z"])
            for name in sorted(tracked.decode().split("\0")):
                if not name or Path(name).suffix.lower() != ".md":
                    continue
                original = repo / name
                if not original.is_file() or original.is_symlink() or not privacy_scan(original, home):
                    continue
                document = original.read_text(encoding="utf-8")
                document = document.replace("file://" + str(repo) + "/", "repo:/")
                document = document.replace(str(repo) + "/", "repo:/")
                document = document.replace(legacy, LEGACY_OPERATOR).replace(str(home), "[local-home]")
                document = document.replace(quote(str(home), safe=""), "[local-home]")
                copy = output / "documentation-proposals" / name
                copy.parent.mkdir(parents=True, exist_ok=True)
                copy.write_text(document, encoding="utf-8")
            # No generic rewriting of hashed JSON. Unexpected exposure is a blocker.
            for path in (output / "review").rglob("*"):
                if path.is_file() and privacy_scan(path, home):
                    raise ValueError(f"Unexpected identifying bytes in copied review artifact: {path.name}.")
            with tempfile.TemporaryDirectory(dir=output) as scratch:
                with sqlite3.connect(Path(scratch) / "work.sqlite3") as db:
                    src.backup(db)
                    db.execute("PRAGMA foreign_keys=ON")
                    apply_receipt_changes(db, changes)
                    db.commit()
                    db.execute("VACUUM INTO ?", (str(output / "sanitized.sqlite3"),))

        sanitized = output / "sanitized.sqlite3"
        with sqlite3.connect(sanitized.as_uri() + "?mode=ro&immutable=1", uri=True) as db:
            if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)] or db.execute("PRAGMA foreign_key_check").fetchall():
                raise ValueError("Sanitized database integrity verification failed.")
            preserve_tables(db, source, changes)
        if any(privacy_scan(p, home) for p in output.rglob("*") if p.is_file()):
            raise ValueError("Identifying bytes remain in rehearsal output.")

        connection.close()
        connection.settings_dict["NAME"] = sanitized.as_uri() + "?mode=ro&immutable=1"
        settings.BASE_DIR = output
        reconciled = []
        from reference.models import ImportExecutionReceipt
        for rel, matrix, _ in packages:
            folder = output / "review" / rel
            candidates = {}
            for path in sorted(folder.glob("*.candidate.json")):
                candidate = deserialize_artifact(path.read_text())
                if candidate.candidate_reference in candidates:
                    raise ValueError("Duplicate attempt candidate.")
                candidates[candidate.candidate_reference] = candidate
            report = MatrixYear(matrix, read(folder / "approval.json"), matrix["model_years"][0], candidates).status()
            if not report["complete"] or report["counts"] != {"previously_completed": len(matrix["rows"])}:
                raise ValueError("Historical matrix reconciliation failed.")
            manifests = {
                artifact.manifest_hash: artifact
                for path in folder.glob("*.manifest.json")
                for artifact in [dict_to_manifest(read(path))]
            }
            receipts = list(ImportExecutionReceipt.objects.filter(
                pk__in=[row["receipt"]["pk"] for row in report["rows"]],
            ))
            if len(manifests) != len(matrix["rows"]) or set(manifests) != {r.manifest_hash for r in receipts}:
                raise ValueError("Historical manifest bindings failed.")
            for receipt in receipts:
                manifest_plan, = manifests[receipt.manifest_hash].plans
                if (manifest_plan.candidate_hash != receipt.resolution_snapshot_json["candidate_hash"]
                        or manifest_plan.candidate_reference != receipt.candidate_reference
                        or manifest_plan.target_slug != receipt.target_slug):
                    raise ValueError("Historical manifest does not bind the receipt row.")
            reconciled.append({"year": matrix["model_years"][0], "matrix_digest": compute_matrix_digest(matrix),
                               "rows": len(matrix["rows"]), "status": "complete"})
        write(output / "rehearsal-report.json", summary | {"reconciled": sorted(reconciled, key=lambda row: row["year"])})
        files = {p.relative_to(output).as_posix(): file_digest(p) for p in sorted(output.rglob("*")) if p.is_file()}
        write(output / "checksums.json", {"original": original_digests, "sanitized": files})
        if any(privacy_scan(p, home) for p in output.rglob("*") if p.is_file()):
            raise ValueError("Identifying bytes remain in final rehearsal artifacts.")
        self.stdout.write(f"Sanitized rehearsal verified: {len(reconciled)} completed matrix years.")
