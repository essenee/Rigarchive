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
    Enforces proven completeness semantics: ESTABLISHED requires SOURCE_ASSERTED or
    EVIDENCE_ESTABLISHED completeness provenance. CORROBORATED requires independent
    corroborating evidence. Internal fixture flags and count heuristics yield UNVERIFIED.
    """

    def evaluate_inventory_completeness(
        self,
        configurations: List[Dict[str, Any]],
        model_year: int,
        raw_source_metadata: Optional[Dict[str, Any]] = None,
    ) -> InventoryCompletenessStatus:
        meta = raw_source_metadata or {}
        if not configurations:
            if meta.get("is_known_incomplete") or meta.get("missing_inventory_evidence"):
                return InventoryCompletenessStatus.INCOMPLETE
            return InventoryCompletenessStatus.UNVERIFIED

        comp_prov = str(meta.get("completeness_provenance", "")).lower()
        is_corroborated = meta.get("is_independently_corroborated", False) or bool(meta.get("corroborating_sources"))

        if comp_prov in ("source_asserted", "evidence_established"):
            return InventoryCompletenessStatus.ESTABLISHED

        if is_corroborated:
            return InventoryCompletenessStatus.CORROBORATED

        if meta.get("is_known_incomplete"):
            return InventoryCompletenessStatus.INCOMPLETE

        return InventoryCompletenessStatus.UNVERIFIED


class JDPowerModernDiscoveryStrategy(BaseJDPowerDiscoveryStrategy):
    """
    Discovery strategy for modern J.D. Power payloads (2010+).
    """

    def evaluate_inventory_completeness(
        self,
        configurations: List[Dict[str, Any]],
        model_year: int,
        raw_source_metadata: Optional[Dict[str, Any]] = None,
    ) -> InventoryCompletenessStatus:
        meta = raw_source_metadata or {}
        if not configurations:
            if meta.get("is_known_incomplete") or meta.get("missing_inventory_evidence"):
                return InventoryCompletenessStatus.INCOMPLETE
            return InventoryCompletenessStatus.UNVERIFIED

        comp_prov = str(meta.get("completeness_provenance", "")).lower()
        is_corroborated = meta.get("is_independently_corroborated", False) or bool(meta.get("corroborating_sources"))

        if comp_prov in ("source_asserted", "evidence_established"):
            return InventoryCompletenessStatus.ESTABLISHED

        if is_corroborated:
            return InventoryCompletenessStatus.CORROBORATED

        if meta.get("is_known_incomplete"):
            return InventoryCompletenessStatus.INCOMPLETE

        return InventoryCompletenessStatus.UNVERIFIED


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
        default_extracted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

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

            extracted_at = default_extracted_at
            target_ctx = getattr(snapshot_meta, "target_context", {}) or {}
            if any(str(make).strip().lower() == "jeep" for make in (
                item.get("make"), data.get("make"), target_ctx.get("make"),
            )):
                # Bind the reviewed JSON inventory, independent of webpage retention.
                from reference.ingestion.acquisition.snapshots import compute_content_hash
                from reference.ingestion.normalization.rules.jeep_jd_power import wrangler_grade

                extracted_at = getattr(snapshot_meta, "acquired_at", None)
                year = item.get("model_year")
                locator = getattr(snapshot_meta, "publisher_locator", None)
                allowed = {f"https://www.jdpower.com/cars/{year}/jeep/{model}/trim"
                           for model in ("wrangler", "wrangler-unlimited")}
                if (item.get("make") != "Jeep" or item.get("model") not in ("Wrangler", "Wrangler Unlimited")
                        or item.get("market") != "US"
                        or getattr(snapshot_meta, "source_id", None) != "jd_power"
                        or locator not in allowed
                        or not isinstance(extracted_at, str) or not extracted_at
                        or not isinstance(raw_bytes_or_dict, bytes)
                        or getattr(snapshot_meta, "content_hash", None) != compute_content_hash(raw_bytes_or_dict)
                        or not getattr(snapshot_meta, "storage_path", None)
                        or prov_meta.get("publisher") != "J.D. Power"
                        or prov_meta.get("source_id") != "jd_power"
                        or prov_meta.get("publication_scope") != "US"
                        or ("native_trim_id" in item and (
                            not isinstance(item["native_trim_id"], str)
                            or not item["native_trim_id"].strip() or "|" in item["native_trim_id"]
                        ))):
                    raise JDPowerExtractorError("Wrangler requires explicit row identity and verified structured-inventory provenance.")
                wrangler_grade(year, item.get("trim"), item.get("drivetrain"),
                               item.get("engine_displacement_liters"), item.get("engine_cylinders"),
                               source_locator=locator)
                if (item["model"] == "Wrangler Unlimited" or "wrangler-unlimited" in locator) and not item["trim"].startswith("Utility 4D "):
                    raise JDPowerExtractorError("Unlimited source scope contradicts the row body.")
                if any(asset.provenance.native_record_id == (item.get("native_trim_id") or f"jdp_cfg_{idx+1}") for asset in assertion_sets):
                    raise JDPowerExtractorError("Duplicate Wrangler source selector.")

            native_id = str(item.get("native_trim_id") or f"jdp_cfg_{idx+1}")
            target_ctx = getattr(snapshot_meta, "target_context", {}) or {}
            make_name = item.get("make") or data.get("make") or target_ctx.get("make") or "Toyota"
            model_name = item.get("model") or data.get("model") or target_ctx.get("model") or "4Runner"
            model_year = item.get("model_year") or data.get("model_year") or target_ctx.get("model_year") or 2019
            market_str = item.get("market") or data.get("market") or pub_scope

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

            s_id = getattr(snapshot_meta, "source_id", None) or "jd_power"
            s_type = getattr(snapshot_meta, "source_type", None) or "third_party_reference"

            prov = SourceMetadata(
                source_id=s_id,
                source_type=s_type,
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

            if make_name == "Jeep" and "source_model_code" in item:
                code = item["source_model_code"]
                if not isinstance(code, str) or not code.strip():
                    raise JDPowerExtractorError("Invalid explicit Wrangler source model code.")
                assertions.append(SourceAssertion(
                    assertion_id=f"ast_jdp_{native_id}_model_code_01",
                    attribute_key="source_model_code",
                    raw_value=code,
                    source_context=f"configurations[{idx}].source_model_code",
                    extracted_at=extracted_at,
                ))

            if item.get("engine_name"):
                assertions.append(
                    SourceAssertion(
                        assertion_id=f"ast_jdp_{native_id}_engname_01",
                        attribute_key="engine_name",
                        raw_value=item.get("engine_name"),
                        source_context="configurations[].engine_name",
                        extracted_at=extracted_at,
                    )
                )

            if make_name == "Jeep":
                specifications = item.get("specifications_url")
                if specifications is not None:
                    if not isinstance(specifications, str):
                        raise JDPowerExtractorError("Invalid Wrangler specifications citation.")
                    from urllib.parse import urlsplit

                    location = urlsplit(specifications)
                    if (location.scheme != "https" or location.netloc != "www.jdpower.com"
                            or not location.path.startswith(f"/cars/{model_year}/jeep/")
                            or not location.path.endswith("/specs")):
                        raise JDPowerExtractorError("Invalid Wrangler specifications citation.")
                for assertion in assertions:
                    if assertion.source_context.startswith("configurations[]"):
                        assertion.source_context = assertion.source_context.replace("[]", f"[{idx}]", 1)
                    if specifications and assertion.attribute_key in {
                        "engine_displacement_liters", "engine_cylinders", "engine_name", "drive_descriptor",
                    }:
                        assertion.source_context += f"; {specifications}"

            asset = SourceAssertionSet(
                envelope=env,
                provenance=prov,
                source_assertions=assertions,
            )
            validate_artifact(asset)
            assertion_sets.append(asset)

        return assertion_sets
