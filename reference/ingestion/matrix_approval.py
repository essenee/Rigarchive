"""Stage 6B matrix approval artifacts (pure Python; no database writes).

An approval record is evidence of an explicit operator action, not a signature or
proof of identity. The future CLI must obtain affirmative confirmation itself.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .matrix import compute_matrix_digest

APPROVAL_VERSION = "1.0"
_SHA = re.compile(r"^sha256:[0-9a-f]{64}$")
_ALLOWED = frozenset({"approval_version", "matrix_digest", "decision", "operator", "approved_at_utc"})


class MatrixApprovalError(ValueError):
    """Invalid, missing, or non-matching explicit approval."""


def _utc_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise MatrixApprovalError("approved_at_utc must be an explicit UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MatrixApprovalError("Invalid approved_at_utc timestamp") from exc
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise MatrixApprovalError("approved_at_utc must be UTC")
    # Require canonical seconds or microseconds; disallow ambiguous offsets/formatting.
    canonical = parsed.isoformat(timespec="microseconds" if parsed.microsecond else "seconds").replace("+00:00", "Z")
    if value != canonical:
        raise MatrixApprovalError("approved_at_utc must use canonical ISO-8601 UTC format")
    return value


def validate_matrix_approval(matrix: Mapping[str, Any], approval: Mapping[str, Any]) -> None:
    """Verify a standalone approval's scope and form against exact matrix content.

    No approval is inferred from a digest, file presence, or successful validation.
    """
    digest = compute_matrix_digest(matrix)
    if not isinstance(approval, dict) or set(approval) != _ALLOWED:
        raise MatrixApprovalError(f"Approval must have exactly {sorted(_ALLOWED)}")
    if approval["approval_version"] != APPROVAL_VERSION:
        raise MatrixApprovalError("Unsupported approval version")
    if not isinstance(approval["matrix_digest"], str) or not _SHA.fullmatch(approval["matrix_digest"]):
        raise MatrixApprovalError("Invalid matrix digest")
    if approval["matrix_digest"] != digest:
        raise MatrixApprovalError("Approval does not match this matrix")
    if approval["decision"] != "approved":
        raise MatrixApprovalError("An explicit affirmative approval is required")
    operator = approval["operator"]
    if not isinstance(operator, str) or not operator.strip() or operator != operator.strip() or "*" in operator:
        raise MatrixApprovalError("Explicit nonempty operator attribution is required")
    _utc_timestamp(approval["approved_at_utc"])


def build_matrix_approval(
    matrix: Mapping[str, Any], *, operator: str, confirmed: bool,
    approved_at: datetime | None = None,
) -> dict[str, str]:
    """Construct only after caller obtained explicit human confirmation.

    `confirmed` must be the affirmative result of a real operator interaction;
    calling this function does not itself perform that interaction.
    """
    if confirmed is not True:
        raise MatrixApprovalError("Human confirmation is required")
    when = approved_at if approved_at is not None else datetime.now(timezone.utc)
    if not isinstance(when, datetime) or when.tzinfo is None or when.utcoffset() != timezone.utc.utcoffset(when):
        raise MatrixApprovalError("Approval time must be timezone-aware UTC")
    stamp = when.isoformat(timespec="microseconds" if when.microsecond else "seconds").replace("+00:00", "Z")
    result = {
        "approval_version": APPROVAL_VERSION,
        "matrix_digest": compute_matrix_digest(matrix),
        "decision": "approved",
        "operator": operator,
        "approved_at_utc": stamp,
    }
    validate_matrix_approval(matrix, result)
    return result


def serialize_matrix_approval(matrix: Mapping[str, Any], approval: Mapping[str, Any]) -> bytes:
    """Validate and serialize an approval as deterministic UTF-8 JSON bytes."""
    validate_matrix_approval(matrix, approval)
    return (json.dumps(approval, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def read_matrix_approval(path: str | Path, matrix: Mapping[str, Any]) -> dict[str, Any]:
    """Load a local approval artifact; fail closed on malformed or missing files."""
    try:
        with open(path, "r", encoding="utf-8") as stream:
            approval = json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MatrixApprovalError(f"Cannot read approval artifact: {exc}") from exc
    validate_matrix_approval(matrix, approval)
    return approval
