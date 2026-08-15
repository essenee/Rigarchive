"""
Ingestion Orchestration Package (RA-023).

Coordinates production acquisition, raw snapshot retention, extraction,
normalization, candidate construction, and dry-run import planning.
"""

from reference.ingestion.orchestration.manufacturer import ProductionManufacturerOrchestrator

__all__ = ["ProductionManufacturerOrchestrator"]
