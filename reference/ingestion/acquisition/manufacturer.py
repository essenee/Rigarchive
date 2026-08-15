"""
Manufacturer Specification Acquisition Adapter (RA-021).

Acquires structured first-party manufacturer specification assertions from offline
specification datasets or official manufacturer payload structures and constructs Tier 1
SourceAssertionSet artifacts with explicit SourceApplicability metadata.
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reference.ingestion.acquisition.base import BaseSourceAdapter, SourceParseError
from reference.ingestion.contracts import (
    ArtifactType,
    Envelope,
    SourceApplicability,
    SourceAssertion,
    SourceAssertionSet,
    SourceMetadata,
)
from reference.ingestion.validation import validate_artifact


class ManufacturerSpecificationAdapter(BaseSourceAdapter):
    """
    Acquisition adapter for authoritative manufacturer specification datasets.
    Constructs Tier 1 SourceAssertionSet artifacts with explicit SourceApplicability provenance.
    """

    def __init__(self, source_id: str = "toyota_usa", transport=None):
        super().__init__(transport=transport)
        self._source_id = source_id

    @property
    def source_id(self) -> str:
        return self._source_id

    def acquire_from_dict(
        self,
        raw_data: Dict[str, Any],
        source_locator: Optional[str] = "file://toyota_2020_4runner_specs.json",
    ) -> List[SourceAssertionSet]:
        """
        Acquire manufacturer specification records from a structured specification dictionary.
        Returns one Tier 1 SourceAssertionSet artifact per source-native configuration item.
        """
        if not raw_data or not isinstance(raw_data, dict):
            raise SourceParseError("Manufacturer payload is empty or invalid.")

        configs = raw_data.get("configurations")
        if configs is None or not isinstance(configs, list):
            raise SourceParseError("Manufacturer payload missing 'configurations' array.")

        prov_meta = raw_data.get("_provenance", {})
        pub_scope = prov_meta.get("publication_scope", "US")
        publisher = prov_meta.get("publisher", "Toyota Motor Sales, U.S.A., Inc.")

        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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
                schema_version="1.0.0",
                created_at=retrieved_at,
                generator="rigarchive-acquisition-manufacturer/0.1.0",
            )

            # Explicit SourceApplicability provenance metadata
            applicability = SourceApplicability(
                market=market_str,
                applicability_basis="first_party_publisher_scope",
                publisher_jurisdiction=f"{market_str}-TMC",
            )

            prov = SourceMetadata(
                source_id=self.source_id,
                source_type="manufacturer_specification",
                source_locator=source_locator,
                retrieved_at=retrieved_at,
                native_record_id=model_code,
                acquisition_method="structured_dataset",
                source_use_notes=f"First-party manufacturer specification payload from {publisher}",
                review_status="not_reviewed",
                target_context={
                    "make": make_name,
                    "model": model_name,
                    "model_year": model_year,
                    "market": market_str,
                },
                source_applicability=applicability,
            )

            assertions: List[SourceAssertion] = [
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_make_01",
                    attribute_key="make_name",
                    raw_value=make_name,
                    source_context="configurations[].make",
                    extracted_at=retrieved_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_model_01",
                    attribute_key="model_name",
                    raw_value=model_name,
                    source_context="configurations[].model",
                    extracted_at=retrieved_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_year_01",
                    attribute_key="model_year",
                    raw_value=model_year,
                    source_context="configurations[].model_year",
                    extracted_at=retrieved_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_grade_01",
                    attribute_key="manufacturer_grade",
                    raw_value=item.get("grade"),
                    source_context="configurations[].grade",
                    extracted_at=retrieved_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_code_01",
                    attribute_key="model_code",
                    raw_value=model_code,
                    source_context="configurations[].model_code",
                    extracted_at=retrieved_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_drive_01",
                    attribute_key="drive_descriptor",
                    raw_value=item.get("drivetrain"),
                    source_context="configurations[].drivetrain",
                    extracted_at=retrieved_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_displ_01",
                    attribute_key="engine_displacement_liters",
                    raw_value=item.get("engine_displacement_liters"),
                    source_context="configurations[].engine_displacement_liters",
                    extracted_at=retrieved_at,
                ),
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_cyl_01",
                    attribute_key="engine_cylinders",
                    raw_value=item.get("engine_cylinders"),
                    source_context="configurations[].engine_cylinders",
                    extracted_at=retrieved_at,
                ),
            ]

            if item.get("transmission"):
                assertions.append(
                    SourceAssertion(
                        assertion_id=f"ast_mfr_{model_code}_trans_01",
                        attribute_key="transmission_descriptor",
                        raw_value=item.get("transmission"),
                        source_context="configurations[].transmission",
                        extracted_at=retrieved_at,
                    )
                )

            # Provenance-derived market applicability assertion
            assertions.append(
                SourceAssertion(
                    assertion_id=f"ast_mfr_{model_code}_market_01",
                    attribute_key="market",
                    raw_value=market_str,
                    source_context="provenance.source_applicability.market",
                    extracted_at=retrieved_at,
                )
            )

            sas = SourceAssertionSet(
                envelope=env,
                provenance=prov,
                source_assertions=assertions,
            )

            validate_artifact(sas)
            assertion_sets.append(sas)

        return assertion_sets

    def acquire_from_file(self, file_path: str) -> List[SourceAssertionSet]:
        """Load manufacturer specification JSON file and acquire assertion sets."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.acquire_from_dict(data, source_locator=f"file://{file_path}")
