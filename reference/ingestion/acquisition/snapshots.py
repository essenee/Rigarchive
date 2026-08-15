"""
Raw Source Artifact Snapshot Manager and Storage (RA-023).

Retains acquired raw manufacturer source payloads immutably in managed storage
with full SHA-256 byte-content hashing and metadata sidecar JSON files.
"""

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from django.conf import settings
from reference.ingestion.contracts import SourceApplicability
from reference.ingestion.serialization import (
    source_applicability_from_dict,
    source_applicability_to_dict,
)


@dataclass
class RawAcquisitionResult:
    """Transient result of acquiring raw source content before storage."""

    source_id: str
    source_locator: str
    acquired_at: str
    content_type: str
    raw_bytes: bytes
    source_applicability: SourceApplicability
    acquisition_method: str  # "live_http" or "local_file"
    http_status: Optional[int] = None
    http_headers: Dict[str, str] = field(default_factory=dict)
    original_filename: Optional[str] = None


@dataclass
class RawSourceSnapshotMetadata:
    """Durable metadata envelope describing a stored raw source artifact snapshot."""

    source_id: str
    publisher_locator: str
    acquired_at: str
    content_type: str
    content_hash: str  # Format: "sha256:<64_hex_chars>"
    storage_path: str  # Relative or absolute path to raw artifact file
    source_applicability: SourceApplicability
    acquisition_method: str
    transport_metadata: Dict[str, Any] = field(default_factory=dict)
    unknown_fields: Dict[str, Any] = field(default_factory=dict)


def compute_content_hash(raw_bytes: bytes) -> str:
    """Compute full 64-character SHA-256 hex digest formatted as 'sha256:<hash>'."""
    digest = hashlib.sha256(raw_bytes).hexdigest()
    return f"sha256:{digest}"


def to_managed_storage_reference(path: Path) -> str:
    """
    Convert an absolute or relative file path into a stable, portable managed relative reference string
    formatted as 'storage/raw_source_artifacts/<source_id>/<hash>.<ext>'.
    """
    path_obj = Path(path)
    parts = path_obj.parts
    if "storage" in parts and "raw_source_artifacts" in parts:
        idx = parts.index("storage")
        return "/".join(parts[idx:])
    elif "raw_source_artifacts" in parts:
        idx = parts.index("raw_source_artifacts")
        return "storage/" + "/".join(parts[idx:])
    return f"storage/raw_source_artifacts/{path_obj.parent.name}/{path_obj.name}"


def resolve_managed_storage_reference(storage_reference: str, storage_root: Optional[Path] = None) -> Path:
    """
    Safely resolve a durable managed storage reference string back to an internal filesystem Path object,
    preventing path traversal escaping outside the managed storage root.
    """
    ref_path = Path(storage_reference)
    if ".." in ref_path.parts:
        raise ValueError(f"Path traversal detected in storage reference '{storage_reference}'.")

    root = (storage_root or Path(settings.BASE_DIR) / "storage" / "raw_source_artifacts").resolve()
    parts = ref_path.parts

    if "storage" in parts and "raw_source_artifacts" in parts:
        idx = parts.index("raw_source_artifacts")
        rel_parts = parts[idx + 1:]
        resolved = root.joinpath(*rel_parts).resolve()
    elif "raw_source_artifacts" in parts:
        idx = parts.index("raw_source_artifacts")
        rel_parts = parts[idx + 1:]
        resolved = root.joinpath(*rel_parts).resolve()
    else:
        resolved = root.joinpath(ref_path).resolve()

    if not str(resolved).startswith(str(root)):
        raise ValueError(f"Storage reference '{storage_reference}' escapes managed storage root '{root}'.")

    return resolved


def snapshot_metadata_to_dict(meta: RawSourceSnapshotMetadata) -> Dict[str, Any]:
    """Serialize RawSourceSnapshotMetadata to a dictionary for JSON sidecar storage."""
    res = {
        "source_id": meta.source_id,
        "publisher_locator": meta.publisher_locator,
        "acquired_at": meta.acquired_at,
        "content_type": meta.content_type,
        "content_hash": meta.content_hash,
        "storage_path": meta.storage_path,
        "source_applicability": source_applicability_to_dict(meta.source_applicability),
        "acquisition_method": meta.acquisition_method,
        "transport_metadata": meta.transport_metadata,
    }
    res.update(meta.unknown_fields)
    return res


def snapshot_metadata_from_dict(d: Dict[str, Any]) -> RawSourceSnapshotMetadata:
    """Deserialize RawSourceSnapshotMetadata from a dictionary."""
    known_keys = {
        "source_id", "publisher_locator", "acquired_at", "content_type",
        "content_hash", "storage_path", "source_applicability",
        "acquisition_method", "transport_metadata"
    }
    unknown = {k: v for k, v in d.items() if k not in known_keys}
    sa_dict = d.get("source_applicability", {})
    sa_obj = source_applicability_from_dict(sa_dict) if isinstance(sa_dict, dict) else SourceApplicability()
    return RawSourceSnapshotMetadata(
        source_id=d.get("source_id", ""),
        publisher_locator=d.get("publisher_locator", ""),
        acquired_at=d.get("acquired_at", ""),
        content_type=d.get("content_type", ""),
        content_hash=d.get("content_hash", ""),
        storage_path=d.get("storage_path", ""),
        source_applicability=sa_obj,
        acquisition_method=d.get("acquisition_method", "local_file"),
        transport_metadata=d.get("transport_metadata", {}),
        unknown_fields=unknown,
    )


class RawSnapshotManager:
    """
    Manages content-addressed storage of raw source payload snapshots and sidecar JSON metadata.
    Enforces immutable write-once storage and atomic file creation.
    """

    DEFAULT_STORAGE_ROOT = Path(settings.BASE_DIR) / "storage" / "raw_source_artifacts"

    def __init__(self, storage_root: Optional[Path] = None):
        self.storage_root = storage_root or self.DEFAULT_STORAGE_ROOT

    def get_extension(self, content_type: str) -> str:
        """Map content-type to standard file extension."""
        ct = content_type.lower().split(";")[0].strip()
        if "html" in ct:
            return "html"
        elif "json" in ct:
            return "json"
        elif "pdf" in ct:
            return "pdf"
        elif "xml" in ct:
            return "xml"
        return "bin"

    def store_snapshot(
        self, acquisition_result: RawAcquisitionResult
    ) -> Tuple[str, RawSourceSnapshotMetadata]:
        """
        Store acquired raw bytes immutably.
        Returns ('CREATED', metadata) or ('ALREADY_PRESENT', metadata).
        """
        raw_bytes = acquisition_result.raw_bytes
        content_hash = compute_content_hash(raw_bytes)
        raw_hex = content_hash.split(":")[1]
        ext = self.get_extension(acquisition_result.content_type)

        source_dir = self.storage_root / acquisition_result.source_id
        source_dir.mkdir(parents=True, exist_ok=True)

        artifact_file = source_dir / f"{raw_hex}.{ext}"
        sidecar_file = source_dir / f"{raw_hex}.meta.json"

        portable_ref = to_managed_storage_reference(artifact_file)

        meta = RawSourceSnapshotMetadata(
            source_id=acquisition_result.source_id,
            publisher_locator=acquisition_result.source_locator,
            acquired_at=acquisition_result.acquired_at,
            content_type=acquisition_result.content_type,
            content_hash=content_hash,
            storage_path=portable_ref,
            source_applicability=acquisition_result.source_applicability,
            acquisition_method=acquisition_result.acquisition_method,
            transport_metadata={
                "http_status": acquisition_result.http_status,
                "original_filename": acquisition_result.original_filename,
            },
        )


        if artifact_file.exists() and sidecar_file.exists():
            # Already present — return existing snapshot metadata without overwriting
            try:
                with open(sidecar_file, "r", encoding="utf-8") as f:
                    existing_meta_dict = json.load(f)
                return "ALREADY_PRESENT", snapshot_metadata_from_dict(existing_meta_dict)
            except Exception:
                return "ALREADY_PRESENT", meta

        # Atomic write for raw content bytes
        with tempfile.NamedTemporaryFile(dir=source_dir, delete=False) as tf:
            tf.write(raw_bytes)
            tf.flush()
            temp_bytes_path = tf.name

        os.replace(temp_bytes_path, artifact_file)

        # Atomic write for metadata sidecar JSON
        meta_dict = snapshot_metadata_to_dict(meta)
        meta_json_bytes = json.dumps(meta_dict, indent=2, sort_keys=True).encode("utf-8")

        with tempfile.NamedTemporaryFile(dir=source_dir, delete=False, mode="wb") as tf:
            tf.write(meta_json_bytes)
            tf.flush()
            temp_meta_path = tf.name

        os.replace(temp_meta_path, sidecar_file)

        return "CREATED", meta
