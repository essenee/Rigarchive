"""
Publication Source Profile Implementation for Toyota USA (RA-023).

Defines Toyota USA Pressroom source profile for local and live acquisition,
security controls, and raw-snapshot-bound extraction.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from reference.ingestion.acquisition.base import (
    AcquisitionError,
    BaseSourceAdapter,
    TransportCallable,
    TransportError,
    default_http_transport,
)
from reference.ingestion.acquisition.snapshots import (
    RawAcquisitionResult,
    RawSourceSnapshotMetadata,
    compute_content_hash,
)
from reference.ingestion.contracts import (
    ArtifactType,
    Envelope,
    ExtractionProvenance,
    SourceApplicability,
    SourceAssertion,
    SourceAssertionSet,
    SourceMetadata,
)
from reference.ingestion.validation import validate_artifact


class TranscriptionHashMismatchError(AcquisitionError):
    """Raised when stored raw snapshot hash does not match transcription expected hash."""

    pass


class ProfileSecurityError(AcquisitionError):
    """Raised when URL or payload violates profile safety bounds."""

    pass


class ToyotaUSAPressroomProfile:
    """
    Concrete publication source profile for official Toyota USA Pressroom specifications.
    Encapsulates fetch locators, transport constraints, security limits, and snapshot-bound extraction.
    """

    SOURCE_ID = "toyota_usa"
    DEFAULT_PUBLISHER_LOCATOR = "https://pressroom.toyota.com/album/2020-toyota-4runner-specs/"
    ALLOWLISTED_HOSTS = {"pressroom.toyota.com"}
    EXPECTED_CONTENT_TYPE = "text/html"
    MAX_PAYLOAD_BYTES = 10 * 1024 * 1024  # 10 MB limit for Toyota specification pages

    def __init__(self, transport: Optional[TransportCallable] = None):
        self.transport = transport or default_http_transport

    @property
    def source_id(self) -> str:
        return self.SOURCE_ID

    @property
    def default_applicability(self) -> SourceApplicability:
        return SourceApplicability(
            market="US",
            applicability_basis="first_party_publisher_scope",
            publisher_jurisdiction="US-TMC",
        )

    def acquire_from_file(
        self,
        file_path: Path,
        publisher_locator: Optional[str] = None,
    ) -> RawAcquisitionResult:
        """Acquire raw payload bytes from a local authoritative source file."""
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            raise AcquisitionError(f"Local source file does not exist: {path}")

        try:
            raw_bytes = path.read_bytes()
        except OSError as e:
            raise AcquisitionError(f"Failed to read local source file '{path}': {str(e)}") from e

        if len(raw_bytes) > self.MAX_PAYLOAD_BYTES:
            raise ProfileSecurityError(
                f"Source payload size ({len(raw_bytes)} bytes) exceeds profile limit ({self.MAX_PAYLOAD_BYTES} bytes)."
            )

        content_type = "text/html" if path.suffix.lower() in {".html", ".htm"} else "application/json"
        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        locator = publisher_locator or self.DEFAULT_PUBLISHER_LOCATOR

        return RawAcquisitionResult(
            source_id=self.source_id,
            source_locator=locator,
            acquired_at=retrieved_at,
            content_type=content_type,
            raw_bytes=raw_bytes,
            source_applicability=self.default_applicability,
            acquisition_method="local_file",
            original_filename=path.name,
        )

    def acquire_from_url(
        self,
        url: str,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> RawAcquisitionResult:
        """Acquire raw payload bytes from an official Toyota USA pressroom URL."""
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise ProfileSecurityError(f"Profile requires HTTPS scheme for URL '{url}'.")

        init_host = (parsed.hostname or "").lower()
        if init_host not in self.ALLOWLISTED_HOSTS:
            raise ProfileSecurityError(
                f"Host '{init_host}' is not in profile allowlisted hosts {sorted(self.ALLOWLISTED_HOSTS)}."
            )

        headers = {
            "User-Agent": "RigArchive-Ingestion/0.1.0 (+https://github.com/rigarchive)",
            "Accept": "text/html,application/xhtml+xml,application/json",
        }
        if extra_headers:
            headers.update(extra_headers)

        res = self.transport(url, headers, timeout_seconds=10)
        if len(res) == 4:
            status_code, body_bytes, resp_headers, final_url = res
        else:
            status_code, body_bytes, resp_headers = res
            final_url = url

        # Final effective URL validation after HTTP redirects
        final_parsed = urlparse(final_url)
        final_host = (final_parsed.hostname or "").lower()
        if final_parsed.scheme != "https" or final_host not in self.ALLOWLISTED_HOSTS:
            raise ProfileSecurityError(
                f"Final redirected URL host '{final_host}' is not in profile allowlisted hosts {sorted(self.ALLOWLISTED_HOSTS)}."
            )

        if status_code != 200:
            raise TransportError(f"Toyota Pressroom returned HTTP {status_code} for URL '{url}'.")

        if not body_bytes:
            raise AcquisitionError(f"Toyota Pressroom returned empty payload for URL '{url}'.")

        if len(body_bytes) > self.MAX_PAYLOAD_BYTES:
            raise ProfileSecurityError(
                f"Response payload size ({len(body_bytes)} bytes) exceeds limit ({self.MAX_PAYLOAD_BYTES} bytes)."
            )

        ct_header = resp_headers.get("Content-Type", "text/html")
        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        return RawAcquisitionResult(
            source_id=self.source_id,
            source_locator=final_url,
            acquired_at=retrieved_at,
            content_type=ct_header,
            raw_bytes=body_bytes,
            source_applicability=self.default_applicability,
            acquisition_method="live_http",
            http_status=status_code,
            http_headers=resp_headers,
        )


    def extract(
        self,
        snapshot_meta: RawSourceSnapshotMetadata,
        transcription_data: Optional[Dict[str, Any]] = None,
        override_expected_hash: Optional[str] = None,
        raw_bytes: Optional[bytes] = None,
        auxiliary_inputs: Optional[List[Any]] = None,
    ) -> List[SourceAssertionSet]:
        """
        Extract Tier 1 SourceAssertionSets directly from retained raw publisher snapshots (PDF/HTML),
        or from verified structured derivative transcriptions for test benchmarks.
        """
        from pathlib import Path
        from reference.ingestion.acquisition.toyota_extractor import ToyotaPricingMasterPdfStrategy

        # 1. Production Runtime Extraction Path (from authentic raw PDF/HTML snapshot bytes)
        bytes_to_extract = raw_bytes
        if not bytes_to_extract and snapshot_meta and snapshot_meta.storage_path:
            p = Path(snapshot_meta.storage_path)
            if p.exists() and p.is_file():
                bytes_to_extract = p.read_bytes()

        if bytes_to_extract and (bytes_to_extract.startswith(b"%PDF") or snapshot_meta.storage_path.endswith(".pdf")):
            from reference.ingestion.acquisition.toyota_extractor import ToyotaProductInformationPdfStrategy
            pricing_strategy = ToyotaPricingMasterPdfStrategy()
            sets = pricing_strategy.extract(bytes_to_extract, snapshot_meta)

            # Discover or extract auxiliary inputs (e.g. Product Information specs PDF)
            aux_specs: List[Tuple[bytes, str, str]] = []

            if auxiliary_inputs:
                for item in auxiliary_inputs:
                    if isinstance(item, (str, Path)):
                        p = Path(item)
                        if p.exists() and p.is_file():
                            aux_specs.append((p.read_bytes(), str(p), "https://pressroom.toyota.com/vehicle/2020-toyota-4runner/"))
                    elif isinstance(item, bytes):
                        aux_specs.append((item, "auxiliary_bytes.pdf", "https://pressroom.toyota.com/vehicle/2020-toyota-4runner/"))
            else:
                specs_path = Path(snapshot_meta.storage_path).parent / "2020_4runner_specs.pdf"
                if specs_path.exists() and specs_path.is_file():
                    aux_specs.append((specs_path.read_bytes(), str(specs_path), "https://pressroom.toyota.com/vehicle/2020-toyota-4runner/"))

            for specs_bytes, specs_storage_path, locator in aux_specs:
                from reference.ingestion.acquisition.snapshots import compute_content_hash
                specs_hash = compute_content_hash(specs_bytes)
                specs_meta = RawSourceSnapshotMetadata(
                    source_id=snapshot_meta.source_id,
                    publisher_locator=locator,
                    acquired_at=snapshot_meta.acquired_at,
                    content_type="application/pdf",
                    content_hash=specs_hash,
                    storage_path=specs_storage_path,
                    source_applicability=snapshot_meta.source_applicability,
                    acquisition_method=snapshot_meta.acquisition_method,
                )
                info_strategy = ToyotaProductInformationPdfStrategy()
                tech_sets = info_strategy.extract(specs_bytes, specs_meta)
                sets.extend(tech_sets)

            return sets

        # 2. Benchmark / Transcription Extraction Path
        if not transcription_data or not isinstance(transcription_data, dict):
            raise AcquisitionError("No raw PDF bytes or transcription payload provided for extraction.")

        configs = transcription_data.get("configurations")
        if configs is None or not isinstance(configs, list):
            raise AcquisitionError("Transcription payload missing 'configurations' array.")

        prov_meta = transcription_data.get("_provenance", {})
        expected_hash = override_expected_hash or prov_meta.get("expected_raw_artifact_hash")

        # Mechanical binding rule enforcement
        if expected_hash and expected_hash != snapshot_meta.content_hash:
            raise TranscriptionHashMismatchError(
                f"Current stored raw snapshot hash '{snapshot_meta.content_hash}' does not match "
                f"derivative transcription expected hash '{expected_hash}'. Extraction requires reverification."
            )


        pub_scope = prov_meta.get("publication_scope", "US")
        publisher = prov_meta.get("publisher", "Toyota Motor Sales, U.S.A., Inc.")
        extracted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        extraction_prov = ExtractionProvenance(
            raw_artifact_hash=snapshot_meta.content_hash,
            raw_artifact_reference=snapshot_meta.storage_path,
            extractor_id="toyota_pressroom_extractor",
            extractor_version="0.1.0",
            extraction_mode="manually_verified_transcription",
        )

        assertion_sets: List[SourceAssertionSet] = []

        for idx, item in enumerate(configs):
            if not isinstance(item, dict):
                continue

            model_code = str(item.get("model_code") or f"row_{idx+1}")
            make_name = item.get("make", "Toyota")
            model_name = item.get("model", "4Runner")
            model_year = item.get("model_year", 2020)
            market_str = item.get("market", pub_scope)

            env = Envelope(
                artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
                schema_version="1.1.0",  # Emitted schema 1.1.0 with ExtractionProvenance
                created_at=extracted_at,
                generator="rigarchive-acquisition-toyota/0.1.0",
            )

            applicability = SourceApplicability(
                market=market_str,
                applicability_basis="first_party_publisher_scope",
                publisher_jurisdiction=f"{market_str}-TMC",
            )

            prov = SourceMetadata(
                source_id=self.source_id,
                source_type="manufacturer_specification",
                source_locator=snapshot_meta.publisher_locator,
                retrieved_at=snapshot_meta.acquired_at,
                native_record_id=model_code,
                acquisition_method=snapshot_meta.acquisition_method,
                source_use_notes=f"First-party manufacturer specification from {publisher}",
                review_status="not_reviewed",
                target_context={
                    "make": make_name,
                    "model": model_name,
                    "model_year": model_year,
                    "market": market_str,
                },
                source_applicability=applicability,
                extraction_provenance=extraction_prov,
            )

            assertions: List[SourceAssertion] = [
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_make_01",
                    attribute_key="make_name",
                    raw_value=make_name,
                    source_context="configurations[].make",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_model_01",
                    attribute_key="model_name",
                    raw_value=model_name,
                    source_context="configurations[].model",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_year_01",
                    attribute_key="model_year",
                    raw_value=model_year,
                    source_context="configurations[].model_year",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_grade_01",
                    attribute_key="manufacturer_grade",
                    raw_value=item.get("grade"),
                    source_context="configurations[].grade",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_code_01",
                    attribute_key="model_code",
                    raw_value=model_code,
                    source_context="configurations[].model_code",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_drive_01",
                    attribute_key="drive_descriptor",
                    raw_value=item.get("drivetrain"),
                    source_context="configurations[].drivetrain",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_displ_01",
                    attribute_key="engine_displacement_liters",
                    raw_value=item.get("engine_displacement_liters"),
                    source_context="configurations[].engine_displacement_liters",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_cyl_01",
                    attribute_key="engine_cylinders",
                    raw_value=item.get("engine_cylinders"),
                    source_context="configurations[].engine_cylinders",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_trans_01",
                    attribute_key="transmission_descriptor",
                    raw_value=item.get("transmission"),
                    source_context="configurations[].transmission",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_market_01",
                    attribute_key="market",
                    raw_value=market_str,
                    source_context="provenance.source_applicability.market",
                    extracted_at=extracted_at,
                ),
            ]

            asset = SourceAssertionSet(
                envelope=env,
                provenance=prov,
                source_assertions=assertions,
            )
            validate_artifact(asset)
            assertion_sets.append(asset)

        return assertion_sets
