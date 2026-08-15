"""
NHTSA vPIC Public Web Services Acquisition Adapter (RA-013).

Acquires vehicle model and vPIC specification assertions from the official NHTSA
vPIC REST API (https://vpic.nhtsa.dot.gov/api/) and constructs Tier 1 SourceAssertionSet artifacts.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from reference.ingestion.acquisition.base import BaseSourceAdapter, SourceParseError
from reference.ingestion.contracts import (
    ArtifactType,
    Envelope,
    SourceAssertion,
    SourceAssertionSet,
    SourceMetadata,
)
from reference.ingestion.validation import validate_artifact


class NHTSAAdapter(BaseSourceAdapter):
    """
    Acquisition adapter for official NHTSA vPIC REST web services.
    Official US DOT NHTSA regulatory web service for Make, Model, and Model Year structure.
    """

    BASE_URL = "https://vpic.nhtsa.dot.gov/api/vehicles"

    @property
    def source_id(self) -> str:
        return "nhtsa_vpic"

    def fetch_models_for_make_year_raw(self, make: str, model_year: int) -> Dict[str, Any]:
        """Fetch raw JSON response payload from NHTSA GetModelsForMakeYear endpoint."""
        encoded_make = quote(make)
        url = f"{self.BASE_URL}/GetModelsForMakeYear/make/{encoded_make}/modelyear/{model_year}?format=json"
        return self._fetch_json(url)

    def acquire_models_for_make_year(
        self, make: str, model_year: int, target_model: Optional[str] = None
    ) -> List[SourceAssertionSet]:
        """
        Acquire model information from NHTSA vPIC for a Make and Model Year.
        Translates raw NHTSA response items into Tier 1 SourceAssertionSet artifacts.
        If target_model is specified, filters results to matching model name.
        """
        raw_data = self.fetch_models_for_make_year_raw(make, model_year)
        results = raw_data.get("Results")

        if results is None or not isinstance(results, list):
            raise SourceParseError(f"NHTSA response missing 'Results' array for make '{make}', year {model_year}.")

        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        encoded_make = quote(make)
        source_locator = f"{self.BASE_URL}/GetModelsForMakeYear/make/{encoded_make}/modelyear/{model_year}?format=json"

        assertion_sets: List[SourceAssertionSet] = []

        for item in results:
            if not isinstance(item, dict):
                continue

            model_name = item.get("Model_Name", "")
            if target_model and model_name.lower() != target_model.lower():
                continue

            make_id = item.get("Make_ID")
            make_name = item.get("Make_Name", make)
            model_id = item.get("Model_ID")

            native_record_id = str(model_id) if model_id is not None else f"{make_id}_{model_name}"

            env = Envelope(
                artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
                schema_version="1.0.0",
                created_at=retrieved_at,
                generator="rigarchive-acquisition-nhtsa/0.1.0",
            )

            prov = SourceMetadata(
                source_id=self.source_id,
                source_type="regulatory_api",
                source_locator=source_locator,
                retrieved_at=retrieved_at,
                native_record_id=native_record_id,
                acquisition_method="rest_api_json",
                source_use_notes="Public REST web service payload; source-use review pending",
                review_status="not_reviewed",
                target_context={
                    "make": make_name,
                    "model": model_name,
                    "model_year": model_year,
                    "market": "US",
                },
            )


            assertions: List[SourceAssertion] = [
                SourceAssertion(
                    assertion_id="ast_nhtsa_make_id_01",
                    attribute_key="make_id",
                    raw_value=make_id,
                    source_context="Results[].Make_ID",
                    extracted_at=retrieved_at,
                ),
                SourceAssertion(
                    assertion_id="ast_nhtsa_make_name_01",
                    attribute_key="make_name",
                    raw_value=make_name,
                    source_context="Results[].Make_Name",
                    extracted_at=retrieved_at,
                ),
                SourceAssertion(
                    assertion_id="ast_nhtsa_model_id_01",
                    attribute_key="model_id",
                    raw_value=model_id,
                    source_context="Results[].Model_ID",
                    extracted_at=retrieved_at,
                ),
                SourceAssertion(
                    assertion_id="ast_nhtsa_model_name_01",
                    attribute_key="model_name",
                    raw_value=model_name,
                    source_context="Results[].Model_Name",
                    extracted_at=retrieved_at,
                ),
            ]

            sas = SourceAssertionSet(
                envelope=env,
                provenance=prov,
                source_assertions=assertions,
            )

            # Validate generated artifact against RA-012 contract validator
            validate_artifact(sas)
            assertion_sets.append(sas)

        return assertion_sets
