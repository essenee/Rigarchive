"""
J.D. Power Configuration Enumeration Extractor & Discovery Strategy Adapters (RA-028 / RA-031).

Extracts Tier 1 SourceAssertionSet artifacts representing factory configuration enumerations
from J.D. Power structured vehicle inventory data (JSON or structured HTML payload).

Implements source-format discovery strategies:
- JDPowerHistoricalDiscoveryStrategy (pre-2010 historical trim/style/engine enumeration)
- JDPowerModernDiscoveryStrategy (2010+ modern trim/style enumeration)

Preserves explicit evidentiary role (configuration_enumeration), third-party source identity (jd_power),
and source authority (third_party_reference) independently without Toyota source conflation.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from reference.ingestion.contracts import (
    ArtifactType,
    Envelope,
    ExtractionProvenance,
    InventoryCompletenessStatus,
    SourceApplicability,
    SourceAssertion,
    SourceAssertionSet,
    SourceMetadata,
)
from reference.ingestion.validation import validate_artifact


class JDPowerExtractorError(ValueError):
    """Raised when J.D. Power extraction payload is invalid or malformed."""
    pass


class BaseJDPowerDiscoveryStrategy(ABC):
    """Abstract base discovery strategy for J.D. Power automotive reference payloads."""

    @abstractmethod
    def evaluate_inventory_completeness(
        self,
        configurations: List[Dict[str, Any]],
        model_year: int,
    ) -> InventoryCompletenessStatus:
        """Evaluate whether discovered configurations represent a complete model-year inventory."""
        pass


class JDPowerHistoricalDiscoveryStrategy(BaseJDPowerDiscoveryStrategy):
    """
    Discovery strategy for historical J.D. Power payloads (pre-2010).
    Verifies multi-engine (V6 / V8) and factory grade (SR5, Sport, Limited) completeness envelope.
    """

    def evaluate_inventory_completeness(
        self,
        configurations: List[Dict[str, Any]],
        model_year: int,
    ) -> InventoryCompletenessStatus:
        if not configurations:
            return InventoryCompletenessStatus.INCOMPLETE

        trims = {str(c.get("trim", "")).strip().upper() for c in configurations}
        engines = {float(c.get("engine_displacement_liters", 0)) for c in configurations if c.get("engine_displacement_liters")}

        # Historical 4Runner expected envelope (2003-2009): SR5, Sport/Sport Edition, Limited + V6 (4.0) & V8 (4.7)
        has_sport = any("SPORT" in t for t in trims)
        has_sr5 = any("SR5" in t for t in trims)
        has_limited = any("LIMITED" in t for t in trims)
        has_v8 = 4.7 in engines or any(c.get("engine_cylinders") == 8 for c in configurations)
        has_v6 = 4.0 in engines or any(c.get("engine_cylinders") == 6 for c in configurations)

        if has_sport and has_sr5 and has_limited and has_v8 and has_v6:
            return InventoryCompletenessStatus.ESTABLISHED
        elif (has_sr5 or has_limited) and (has_v6 or has_v8):
            return InventoryCompletenessStatus.CORROBORATED

        return InventoryCompletenessStatus.INCOMPLETE


class JDPowerModernDiscoveryStrategy(BaseJDPowerDiscoveryStrategy):
    """
    Discovery strategy for modern J.D. Power payloads (2010+).
    """

    def evaluate_inventory_completeness(
        self,
        configurations: List[Dict[str, Any]],
        model_year: int,
    ) -> InventoryCompletenessStatus:
        if not configurations:
            return InventoryCompletenessStatus.INCOMPLETE

        if len(configurations) >= 4:
            return InventoryCompletenessStatus.ESTABLISHED
        return InventoryCompletenessStatus.CORROBORATED


class JDPowerExtractor:
    """
    Extractor strategy for J.D. Power automotive reference configuration enumerations.
    """

    EXTRACTOR_ID = "jd_power_configuration_extractor"
    EXTRACTOR_VERSION = "1.1.0"

    def select_discovery_strategy(self, model_year: int) -> BaseJDPowerDiscoveryStrategy:
        """Select appropriate discovery strategy based on historical model-year boundary."""
        if model_year < 2010:
            return JDPowerHistoricalDiscoveryStrategy()
        return JDPowerModernDiscoveryStrategy()

    def extract(
        self,
        raw_bytes_or_dict: Union[bytes, str, Dict[str, Any]],
        snapshot_meta: SourceMetadata,
    ) -> List[SourceAssertionSet]:
        """
        Extract Tier 1 SourceAssertionSets from J.D. Power payload.
        """
        if isinstance(raw_bytes_or_dict, (bytes, bytearray)):
            try:
                data = json.loads(raw_bytes_or_dict.decode("utf-8"))
            except Exception as e:
                raise JDPowerExtractorError(f"Failed to parse JSON payload bytes: {e}") from e
        elif isinstance(raw_bytes_or_dict, str):
            try:
                data = json.loads(raw_bytes_or_dict)
            except Exception as e:
                raise JDPowerExtractorError(f"Failed to parse JSON payload string: {e}") from e
        elif isinstance(raw_bytes_or_dict, dict):
            data = raw_bytes_or_dict
        else:
            raise JDPowerExtractorError(f"Unsupported payload type: {type(raw_bytes_or_dict)}")

        configs = data.get("configurations")
        if configs is None or not isinstance(configs, list):
            raise JDPowerExtractorError("J.D. Power payload missing 'configurations' array.")

        prov_meta = data.get("_provenance", {})
        pub_scope = prov_meta.get("publication_scope", "US")
        extracted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        content_hash = getattr(snapshot_meta, "content_hash", None) or getattr(snapshot_meta, "raw_artifact_hash", None)
        if not content_hash or not content_hash.startswith("sha256:"):
            from reference.ingestion.acquisition.snapshots import compute_content_hash
            if isinstance(raw_bytes_or_dict, (bytes, bytearray)):
                content_hash = compute_content_hash(raw_bytes_or_dict)
            elif isinstance(raw_bytes_or_dict, str):
                content_hash = compute_content_hash(raw_bytes_or_dict.encode("utf-8"))
            else:
                content_hash = "sha256:" + "0" * 64

        storage_path = getattr(snapshot_meta, "storage_path", None) or getattr(snapshot_meta, "raw_artifact_reference", None) or "storage/jd_power/snapshot_placeholder.json"

        extraction_prov = ExtractionProvenance(
            raw_artifact_hash=content_hash,
            raw_artifact_reference=storage_path,
            extractor_id=self.EXTRACTOR_ID,
            extractor_version=self.EXTRACTOR_VERSION,
            extraction_mode="source_specific_parser",
        )

        assertion_sets: List[SourceAssertionSet] = []

        for idx, item in enumerate(configs):
            if not isinstance(item, dict):
                continue

            native_id = str(item.get("native_trim_id") or f"jdp_cfg_{idx+1}")
            make_name = item.get("make", "Toyota")
            model_name = item.get("model", "4Runner")
            model_year = item.get("model_year", 2019)
            market_str = item.get("market", pub_scope)

            env = Envelope(
                artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
                schema_version="1.1.0",
                created_at=extracted_at,
                generator="rigarchive-acquisition-jdpower/1.1.0",
            )

            applicability = SourceApplicability(
                market=market_str,
                applicability_basis="configuration_enumeration",
                publisher_jurisdiction=f"{market_str}-JDPower",
                applicability_scope="configuration",
            )

            locator = getattr(snapshot_meta, "publisher_locator", None) or getattr(snapshot_meta, "source_locator", f"https://www.jdpower.com/cars/{model_year}/toyota/4runner")
            acq_method = getattr(snapshot_meta, "acquisition_method", None) or "local_file"

            prov = SourceMetadata(
                source_id="jd_power",
                source_type="third_party_reference",
                source_locator=locator,
                retrieved_at=getattr(snapshot_meta, "acquired_at", None) or getattr(snapshot_meta, "retrieved_at", None) or extracted_at,
                native_record_id=native_id,
                acquisition_method=acq_method,
                source_use_notes="Third-party automotive reference configuration enumeration from J.D. Power",
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
                    assertion_id=f"ast_jdp_{native_id}_make_01",
                    attribute_key="make_name",
                    raw_value=make_name,
                    source_context="configurations[].make",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_jdp_{native_id}_model_01",
                    attribute_key="model_name",
                    raw_value=model_name,
                    source_context="configurations[].model",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_jdp_{native_id}_year_01",
                    attribute_key="model_year",
                    raw_value=model_year,
                    source_context="configurations[].model_year",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_jdp_{native_id}_trim_01",
                    attribute_key="trim",
                    raw_value=item.get("trim"),
                    source_context="configurations[].trim",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_jdp_{native_id}_drive_01",
                    attribute_key="drive_descriptor",
                    raw_value=item.get("drivetrain"),
                    source_context="configurations[].drivetrain",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_jdp_{native_id}_displ_01",
                    attribute_key="engine_displacement_liters",
                    raw_value=item.get("engine_displacement_liters"),
                    source_context="configurations[].engine_displacement_liters",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_jdp_{native_id}_cyl_01",
                    attribute_key="engine_cylinders",
                    raw_value=item.get("engine_cylinders"),
                    source_context="configurations[].engine_cylinders",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_jdp_{native_id}_trans_01",
                    attribute_key="transmission_descriptor",
                    raw_value=item.get("transmission"),
                    source_context="configurations[].transmission",
                    extracted_at=extracted_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_jdp_{native_id}_market_01",
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
