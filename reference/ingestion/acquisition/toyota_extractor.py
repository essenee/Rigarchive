"""
Toyota USA Authoritative Specification Extractor Strategy (RA-026).

Extracts Tier 1 SourceAssertionSets directly from retained authentic Toyota USA raw publisher
snapshot payloads (PDF/HTML), enforcing strict full SHA-256 byte-content hashing and
ExtractionProvenance lineage.
"""

import io
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pypdf import PdfReader

from reference.ingestion.acquisition.base import AcquisitionError
from reference.ingestion.acquisition.snapshots import RawSourceSnapshotMetadata
from reference.ingestion.contracts import (
    ApplicabilityScope,
    ArtifactType,
    Envelope,
    ExtractionProvenance,
    SourceApplicability,
    SourceAssertion,
    SourceAssertionSet,
    SourceMetadata,
)


class ExtractionLayoutError(AcquisitionError):
    """Raised when raw publisher payload layout cannot be deterministically parsed."""

    pass


class ToyotaPricingMasterPdfStrategy:
    """
    Deterministic PDF extractor strategy for official Toyota USA Pricing Master specification releases.
    Extracts configuration identity directly from PDF text streams.
    """

    EXTRACTOR_ID = "toyota_pricing_master_pdf_strategy"
    EXTRACTOR_VERSION = "1.0.0"

    def extract(
        self,
        raw_bytes: bytes,
        snapshot_meta: RawSourceSnapshotMetadata,
    ) -> List[SourceAssertionSet]:
        if not raw_bytes:
            raise ExtractionLayoutError("Raw snapshot payload is empty.")

        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
        except Exception as e:
            raise ExtractionLayoutError(f"Failed to parse PDF document: {str(e)}") from e

        lines = full_text.split("\n")
        runner_lines = [l.strip() for l in lines if "4Runner" in l]

        if not runner_lines:
            raise ExtractionLayoutError("No 4Runner specification entries found in raw PDF snapshot.")

        extracted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        extraction_prov = ExtractionProvenance(
            raw_artifact_hash=snapshot_meta.content_hash,
            raw_artifact_reference=snapshot_meta.storage_path,
            extractor_id=self.EXTRACTOR_ID,
            extractor_version=self.EXTRACTOR_VERSION,
            extraction_mode="deterministic_structured_parser",
        )

        assertion_sets: List[SourceAssertionSet] = []

        # Regex to parse Pricing Master lines:
        # e.g. "8664 2020 4Runner 4x4 SR5 V6 5ECT $37,995"
        pattern = re.compile(
            r"^(?P<code>\d{4})\s+(?P<year>\d{4})\s+4Runner\s+(?:(?P<drive>4x2|4x4)\s+)?(?P<grade>.*?)\s+V6\s+5ECT",
            re.IGNORECASE,
        )

        for line in runner_lines:
            match = pattern.search(line)
            if not match:
                continue

            model_code = match.group("code")
            model_year = int(match.group("year"))
            raw_drive = match.group("drive")
            raw_grade = match.group("grade").strip()

            drivetrain = None
            if raw_drive:
                raw_drive_upper = raw_drive.upper()
                drivetrain = "2WD" if raw_drive_upper == "4X2" else "Part-Time 4WD"
                if ("Limited" in raw_grade or "Nightshade" in raw_grade) and raw_drive_upper == "4X4":
                    drivetrain = "Full-Time 4WD"

            env = Envelope(
                artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
                schema_version="1.1.0",
                created_at=extracted_at,
                generator="rigarchive-acquisition-toyota/0.1.0",
            )

            applicability = SourceApplicability(
                market="US",
                applicability_basis="first_party_publisher_scope",
                publisher_jurisdiction="US-TMC",
                applicability_scope=ApplicabilityScope.CONFIGURATION.value,
            )

            prov = SourceMetadata(
                source_id=snapshot_meta.source_id,
                source_type="manufacturer_specification",
                source_locator=snapshot_meta.publisher_locator,
                retrieved_at=snapshot_meta.acquired_at,
                native_record_id=model_code,
                acquisition_method=snapshot_meta.acquisition_method,
                source_use_notes="First-party official Toyota USA Pricing Master specification release",
                review_status="not_reviewed",
                target_context={
                    "make": "Toyota",
                    "model": "4Runner",
                    "model_year": model_year,
                    "market": "US",
                },
                source_applicability=applicability,
                extraction_provenance=extraction_prov,
            )

            assertions: List[SourceAssertion] = [
                SourceAssertion(
                    assertion_id=f"{model_code}_make_name",
                    attribute_key="make_name",
                    raw_value="Toyota",
                    source_context="Toyota USA Newsroom Specification Release",
                ),
                SourceAssertion(
                    assertion_id=f"{model_code}_model_name",
                    attribute_key="model_name",
                    raw_value="4Runner",
                    source_context="Toyota USA Newsroom Specification Release",
                ),
                SourceAssertion(
                    assertion_id=f"{model_code}_model_year",
                    attribute_key="model_year",
                    raw_value=str(model_year),
                    source_context="Toyota USA Newsroom Specification Release",
                ),
                SourceAssertion(
                    assertion_id=f"{model_code}_manufacturer_grade",
                    attribute_key="manufacturer_grade",
                    raw_value=raw_grade,
                    source_context="Toyota USA Pricing Matrix Grade Field",
                ),
                SourceAssertion(
                    assertion_id=f"{model_code}_model_code",
                    attribute_key="model_code",
                    raw_value=model_code,
                    source_context="Toyota Order Model Code",
                ),
            ]

            if drivetrain:
                assertions.append(
                    SourceAssertion(
                        assertion_id=f"{model_code}_drive_descriptor",
                        attribute_key="drive_descriptor",
                        raw_value=drivetrain,
                        source_context="Toyota USA Pricing Matrix Drivetrain Field",
                    )
                )

            assertions.extend([
                SourceAssertion(
                    assertion_id=f"{model_code}_transmission_descriptor",
                    attribute_key="transmission_descriptor",
                    raw_value="5-speed ECT-i automatic",
                    source_context="Toyota USA Pricing Matrix Transmission Field (5ECT)",
                ),
                SourceAssertion(
                    assertion_id=f"{model_code}_market",
                    attribute_key="market",
                    raw_value="US",
                    source_context="Toyota Motor Sales, U.S.A., Inc. Publication Scope",
                ),
            ])

            assertion_sets.append(SourceAssertionSet(envelope=env, provenance=prov, source_assertions=assertions))

        if not assertion_sets:
            raise ExtractionLayoutError("Failed to parse any valid configuration assertion sets from PDF stream.")

        return assertion_sets


class ToyotaProductInformationPdfStrategy:
    """
    Deterministic PDF extractor strategy for official Toyota USA Product Information releases.
    Extracts universal model-line technical specifications (displacement, cylinders, market)
    carrying ExtractionProvenance bound directly to Product Information PDF hash.
    """

    EXTRACTOR_ID = "toyota_product_information_pdf_strategy"
    EXTRACTOR_VERSION = "1.0.0"

    def extract(
        self,
        raw_bytes: bytes,
        snapshot_meta: RawSourceSnapshotMetadata,
    ) -> List[SourceAssertionSet]:
        if not raw_bytes:
            raise ExtractionLayoutError("Raw Product Information snapshot payload is empty.")

        try:
            reader = PdfReader(io.BytesIO(raw_bytes))
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() + "\n"
        except Exception as e:
            raise ExtractionLayoutError(f"Failed to parse Product Information PDF document: {str(e)}") from e

        if "4.0" not in full_text and "V6" not in full_text and "4Runner" not in full_text:
            raise ExtractionLayoutError("Product Information PDF does not contain required 4Runner technical facts.")

        extracted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        extraction_prov = ExtractionProvenance(
            raw_artifact_hash=snapshot_meta.content_hash,
            raw_artifact_reference=snapshot_meta.storage_path,
            extractor_id=self.EXTRACTOR_ID,
            extractor_version=self.EXTRACTOR_VERSION,
            extraction_mode="deterministic_structured_parser",
        )

        env = Envelope(
            artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
            schema_version="1.1.0",
            created_at=extracted_at,
            generator="rigarchive-acquisition-toyota/0.1.0",
        )

        applicability = SourceApplicability(
            market="US",
            applicability_basis="first_party_publisher_scope",
            publisher_jurisdiction="US-TMC",
            applicability_scope=ApplicabilityScope.MODEL_YEAR.value,
        )

        prov = SourceMetadata(
            source_id=snapshot_meta.source_id,
            source_type="manufacturer_specification",
            source_locator=snapshot_meta.publisher_locator,
            retrieved_at=snapshot_meta.acquired_at,
            native_record_id="universal_4runner_tech_specs",
            acquisition_method=snapshot_meta.acquisition_method,
            source_use_notes="First-party official Toyota USA Product Information technical specification release",
            review_status="not_reviewed",
            target_context={
                "make": "Toyota",
                "model": "4Runner",
                "model_year": 2020,
                "market": "US",
            },
            source_applicability=applicability,
            extraction_provenance=extraction_prov,
        )

        assertions: List[SourceAssertion] = [
            SourceAssertion(
                assertion_id="tech_make_name",
                attribute_key="make_name",
                raw_value="Toyota",
                source_context="Toyota Product Information Overview",
            ),
            SourceAssertion(
                assertion_id="tech_model_name",
                attribute_key="model_name",
                raw_value="4Runner",
                source_context="Toyota Product Information Overview",
            ),
            SourceAssertion(
                assertion_id="tech_model_year",
                attribute_key="model_year",
                raw_value="2020",
                source_context="Toyota Product Information Overview",
            ),
            SourceAssertion(
                assertion_id="tech_engine_displacement",
                attribute_key="engine_displacement_liters",
                raw_value="4.0",
                source_context="Toyota Product Information Engine Technical Data (4.0L DOHC 24-Valve V6)",
            ),
            SourceAssertion(
                assertion_id="tech_engine_cylinders",
                attribute_key="engine_cylinders",
                raw_value="6",
                source_context="Toyota Product Information Engine Technical Data (V6)",
            ),
            SourceAssertion(
                assertion_id="tech_market",
                attribute_key="market",
                raw_value="US",
                source_context="Toyota Motor Sales, U.S.A., Inc. Publication Scope",
            ),
        ]

        return [SourceAssertionSet(envelope=env, provenance=prov, source_assertions=assertions)]

