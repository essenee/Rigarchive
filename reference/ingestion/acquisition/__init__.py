"""
Reference Data Ingestion Source Acquisition Adapters Package (RA-013).

Provides acquisition adapters for structured external sources (NHTSA vPIC and EPA FuelEconomy.gov),
isolated HTTP transport interface, and Tier 1 SourceAssertionSet construction.
"""

from reference.ingestion.acquisition.base import (
    AcquisitionError,
    BaseSourceAdapter,
    SourceParseError,
    TransportError,
    default_http_transport,
)
from reference.ingestion.acquisition.epa import EPAAdapter
from reference.ingestion.acquisition.manufacturer import ManufacturerSpecificationAdapter
from reference.ingestion.acquisition.nhtsa import NHTSAAdapter
from reference.ingestion.acquisition.smoke_test import (
    run_all_live_smoke_tests,
    run_live_epa_smoke_test,
    run_live_nhtsa_smoke_test,
)

__all__ = [
    "AcquisitionError",
    "TransportError",
    "SourceParseError",
    "BaseSourceAdapter",
    "default_http_transport",
    "NHTSAAdapter",
    "EPAAdapter",
    "ManufacturerSpecificationAdapter",
    "run_live_nhtsa_smoke_test",
    "run_live_epa_smoke_test",
    "run_all_live_smoke_tests",
]
