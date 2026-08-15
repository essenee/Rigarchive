"""
Source Assertion Normalization Package (RA-014 / RA-015).

Provides pure Python source-specific normalizers (NHTSANormalizer, EPANormalizer)
and top-level normalize_source_assertions dispatch function.
"""

from reference.ingestion.normalization.base import (
    BaseSourceNormalizer,
    NormalizationError,
    UnsupportedSourceError,
    get_normalizer_for_source,
    normalize_source_assertions,
    register_normalizer,
)
from reference.ingestion.normalization.epa import EPANormalizer
from reference.ingestion.normalization.manufacturer import ManufacturerNormalizer
from reference.ingestion.normalization.nhtsa import NHTSANormalizer

# Register normalizers
register_normalizer(NHTSANormalizer)
register_normalizer(EPANormalizer)
register_normalizer(ManufacturerNormalizer)

__all__ = [
    "BaseSourceNormalizer",
    "NHTSANormalizer",
    "EPANormalizer",
    "ManufacturerNormalizer",
    "NormalizationError",
    "UnsupportedSourceError",
    "normalize_source_assertions",
    "get_normalizer_for_source",
    "register_normalizer",
]
