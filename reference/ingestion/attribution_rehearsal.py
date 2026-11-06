"""One-time rehearsal helpers. Never accept a live database as input."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import re
from urllib.parse import quote

from reference.ingestion.matrix_approval import serialize_matrix_approval

LEGACY_OPERATOR = "legacy_cli_operator"


def file_digest(path):
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def approval_change(matrix, approval, legacy_label):
    original = serialize_matrix_approval(matrix, approval)
    updated = dict(approval)
    if updated["operator"] == legacy_label:
        updated["operator"] = LEGACY_OPERATOR
    replacement = serialize_matrix_approval(matrix, updated)
    return tuple("sha256:" + sha256(raw).hexdigest() for raw in (original, replacement)), replacement


def portable_reference(value, expected_hash, repo):
    repo = repo.resolve()
    path = Path(value)
    if not path.is_file():
        return "unavailable:receipt-source", "missing"
    if not path.resolve().is_relative_to(repo):
        return "unavailable:receipt-source", "outside_managed_root"
    if file_digest(path) != expected_hash:
        return "unavailable:receipt-source", "digest_mismatch"
    return path.resolve().relative_to(repo).as_posix(), "verified_portable"


def check_isolation(repo, source, output):
    repo = repo.resolve()
    if source.resolve().is_relative_to(repo) or output.resolve().is_relative_to(repo):
        raise ValueError("Database input and output must be outside the project tree.")
    if not source.is_file() or source.is_symlink() or source.stat().st_nlink != 1:
        raise ValueError("Input must be a standalone snapshot file.")
    live = repo / "db.sqlite3"
    if live.exists() and source.samefile(live):
        raise ValueError("Input aliases the live database.")
    if any(source.parent.glob(source.name + "-*")):
        raise ValueError("Snapshot has SQLite sidecars.")
    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists.")


def privacy_scan(path, home):
    token = re.escape(home.name.encode())
    pattern = rb"(?<![A-Za-z0-9_])" + token + rb"(?![A-Za-z0-9_])"
    raw = path.read_bytes()
    home_forms = (str(home), str(home).replace("/", r"\/"), quote(str(home), safe=""))
    return any(prefix.encode().lower() in raw.lower() for prefix in home_forms) or re.search(pattern, raw, re.I) is not None


def receipt_changes(conn, repo, home, crosswalk):
    changes = []
    for pk, operator, ref, raw_hash, snapshot in conn.execute(
        "SELECT id, operator_label, raw_artifact_reference, raw_artifact_hash, resolution_snapshot_json "
        "FROM reference_importexecutionreceipt ORDER BY id"
    ):
        fields = {}
        if operator == f"cli:{home.name}":
            fields["operator_label"] = LEGACY_OPERATOR
        classification = None
        if ref.startswith(str(home) + "/"):
            replacement, classification = portable_reference(ref, raw_hash, repo)
            fields["raw_artifact_reference"] = replacement
        data = json.loads(snapshot)
        pin = data.get("matrix", {}).get("approval_digest")
        if pin in crosswalk:
            data["matrix"]["approval_digest"] = crosswalk[pin]
            fields["resolution_snapshot_json"] = json.dumps(data, ensure_ascii=False)
        if fields:
            changes.append((pk, fields, classification, pin if pin in crosswalk else None))
    return changes


def apply_receipt_changes(conn, changes):
    for pk, fields, _, _ in changes:
        assignments = ", ".join(f"{field}=?" for field in fields)
        conn.execute(f"UPDATE reference_importexecutionreceipt SET {assignments} WHERE id=?", (*fields.values(), pk))


def summarize(changes):
    return {
        "receipt_updates": len(changes),
        "operator_replacements": sum("operator_label" in fields for _, fields, _, _ in changes),
        "path_classes": dict(Counter(kind for _, _, kind, _ in changes if kind)),
        "approval_pin_updates": sum(bool(pin) for _, _, _, pin in changes),
        "changed_receipts": [
            {"pk": pk, "fields": sorted(fields), "path_class": kind, "previous_approval_digest": pin}
            for pk, fields, kind, pin in changes
        ],
    }
