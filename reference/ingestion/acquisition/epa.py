"""
EPA / FuelEconomy.gov Public Web Services Acquisition Adapter (RA-013).

Acquires powertrain, drivetrain, and vehicle specification assertions from the official
DOE/EPA FuelEconomy.gov REST web services (https://www.fueleconomy.gov/ws/rest/vehicle/)
and constructs Tier 1 SourceAssertionSet artifacts.
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


class EPAAdapter(BaseSourceAdapter):
    """
    Acquisition adapter for official EPA FuelEconomy.gov REST web services.
    Official US DOE/EPA powertrain & fuel economy REST web service source.
    """

    BASE_URL = "https://www.fueleconomy.gov/ws/rest/vehicle"

    @property
    def source_id(self) -> str:
        return "epa_fueleconomy"

    def fetch_vehicle_options_raw(self, make: str, model_year: int, model: str) -> Dict[str, Any]:
        """Fetch matching EPA vehicle options for Make, Year, and Model."""
        encoded_make = quote(make)
        encoded_model = quote(model)
        url = f"{self.BASE_URL}/menu/options?year={model_year}&make={encoded_make}&model={encoded_model}"
        return self._fetch_json(url)

    def fetch_vehicle_by_id_raw(self, vehicle_id: str) -> Dict[str, Any]:
        """Fetch raw EPA vehicle specification record by native EPA vehicle ID."""
        url = f"{self.BASE_URL}/{vehicle_id}"
        return self._fetch_json(url)

    def acquire_vehicle_by_id(
        self,
        vehicle_id: str,
        make: Optional[str] = None,
        model: Optional[str] = None,
        model_year: Optional[int] = None,
    ) -> SourceAssertionSet:
        """
        Acquire EPA vehicle specification record by native vehicle ID (e.g. '42101')
        and translate raw EPA payload fields into a Tier 1 SourceAssertionSet artifact.
        """
        raw_data = self.fetch_vehicle_by_id_raw(vehicle_id)

        if not raw_data or not isinstance(raw_data, dict):
            raise SourceParseError(f"EPA response for vehicle_id '{vehicle_id}' is empty or invalid.")

        retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        source_locator = f"{self.BASE_URL}/{vehicle_id}"

        res_make = raw_data.get("make") or make or "Unknown"
        res_model = raw_data.get("model") or model or "Unknown"
        res_year = raw_data.get("year") or model_year

        try:
            parsed_year = int(res_year) if res_year is not None else None
        except (ValueError, TypeError):
            parsed_year = None

        env = Envelope(
            artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
            schema_version="1.0.0",
            created_at=retrieved_at,
            generator="rigarchive-acquisition-epa/0.1.0",
        )

        prov = SourceMetadata(
            source_id=self.source_id,
            source_type="powertrain_database",
            source_locator=source_locator,
            retrieved_at=retrieved_at,
            native_record_id=str(vehicle_id),
            acquisition_method="rest_api_json",
            source_use_notes="Public REST web service payload; source-use review pending",
            review_status="not_reviewed",
            target_context={
                "make": res_make,
                "model": res_model,
                "model_year": parsed_year,
                "market": "US",
            },
        )


        assertions: List[SourceAssertion] = []

        field_mappings = [
            ("year", "model_year", "ast_epa_year_01"),
            ("make", "make", "ast_epa_make_01"),
            ("model", "model", "ast_epa_model_01"),
            ("drive", "drive_descriptor", "ast_epa_drive_01"),
            ("displ", "engine_displacement_liters", "ast_epa_displ_01"),
            ("cyl", "engine_cylinders", "ast_epa_cyl_01"),
            ("trany", "transmission_descriptor", "ast_epa_trans_01"),
            ("vClass", "vehicle_class", "ast_epa_class_01"),
            ("eng_dscr", "engine_description", "ast_epa_eng_dscr_01"),
            ("city08", "city_mpg_epa_rating", "ast_epa_city_mpg_01"),
            ("highway08", "highway_mpg_epa_rating", "ast_epa_hwy_mpg_01"),

        ]

        for source_key, attr_key, ast_id in field_mappings:
            val = raw_data.get(source_key)
            if val is not None and val != "":
                assertions.append(
                    SourceAssertion(
                        assertion_id=ast_id,
                        attribute_key=attr_key,
                        raw_value=val,
                        source_context=f"payload.{source_key}",
                        extracted_at=retrieved_at,
                    )
                )

        sas = SourceAssertionSet(
            envelope=env,
            provenance=prov,
            source_assertions=assertions,
        )

        # Validate generated artifact against RA-012 contract validator
        validate_artifact(sas)
        return sas
