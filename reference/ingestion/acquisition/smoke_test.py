"""
Bounded Manual Live Smoke Testing Utility for Acquisition Adapters (RA-013).

Provides explicit functions for testing live connectivity to NHTSA vPIC and EPA FuelEconomy.gov
APIs on demand. This utility is isolated and NOT executed as part of the automated unit test suite.
"""

import logging
from typing import Any, Dict

from reference.ingestion.acquisition.epa import EPAAdapter
from reference.ingestion.acquisition.nhtsa import NHTSAAdapter

logger = logging.getLogger(__name__)


def run_live_nhtsa_smoke_test(make: str = "Toyota", model_year: int = 2020) -> Dict[str, Any]:
    """
    Perform a live HTTP query to NHTSA vPIC REST API.
    Returns status summary dictionary without creating disk artifacts.
    """
    adapter = NHTSAAdapter(timeout_seconds=10)
    try:
        results = adapter.acquire_models_for_make_year(make, model_year, target_model="4Runner")
        if results:
            sas = results[0]
            return {
                "source": "nhtsa_vpic",
                "success": True,
                "endpoint": sas.provenance.source_locator,
                "assertions_count": len(sas.source_assertions),
                "native_record_id": sas.provenance.native_record_id,
                "target_context": sas.provenance.target_context,
            }
        else:
            return {
                "source": "nhtsa_vpic",
                "success": False,
                "error": f"No models found matching make '{make}', year {model_year}.",
            }
    except Exception as e:
        return {
            "source": "nhtsa_vpic",
            "success": False,
            "error": str(e),
        }


def run_live_epa_smoke_test(vehicle_id: str = "42101") -> Dict[str, Any]:
    """
    Perform a live HTTP query to EPA FuelEconomy.gov REST API for vehicle ID 42101 (2020 4Runner 4WD).
    Returns status summary dictionary without creating disk artifacts.
    """
    adapter = EPAAdapter(timeout_seconds=10)
    try:
        sas = adapter.acquire_vehicle_by_id(vehicle_id)
        return {
            "source": "epa_fueleconomy",
            "success": True,
            "endpoint": sas.provenance.source_locator,
            "assertions_count": len(sas.source_assertions),
            "native_record_id": sas.provenance.native_record_id,
            "target_context": sas.provenance.target_context,
        }
    except Exception as e:
        return {
            "source": "epa_fueleconomy",
            "success": False,
            "error": str(e),
        }


def run_all_live_smoke_tests() -> Dict[str, Any]:
    """Execute live smoke tests for both NHTSA and EPA adapters."""
    return {
        "nhtsa": run_live_nhtsa_smoke_test(),
        "epa": run_live_epa_smoke_test(),
    }
