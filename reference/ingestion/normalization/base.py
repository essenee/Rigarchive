"""
Base Source Normalization Infrastructure (RA-014 / RA-015).

Defines the BaseSourceNormalizer interface, exception classes, and top-level
dispatch entry point for converting Tier 1 SourceAssertionSet artifacts into
NormalizedInterpretation arrays.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Type

from reference.ingestion.contracts import (
    NormalizedInterpretation,
    SourceAssertionSet,
)
from reference.ingestion.validation import validate_source_assertion_set


class NormalizationError(ValueError):
    """Base exception raised for normalization failures or contract violations."""
    pass


class UnsupportedSourceError(NormalizationError):
    """Raised when no normalizer is registered for a given source_id."""
    pass


class BaseSourceNormalizer(ABC):
    """
    Abstract base class for source-specific normalizers.

    Each concrete normalizer owns the mapping logic and rule definitions
    for a specific source (e.g. NHTSA vPIC, EPA FuelEconomy.gov).
    """

    @property
    @abstractmethod
    def source_id(self) -> str:
        """The source_id handled by this normalizer (e.g. 'nhtsa_vpic')."""
        pass

    @abstractmethod
    def normalize(self, assertion_set: SourceAssertionSet) -> List[NormalizedInterpretation]:
        """
        Normalize a valid SourceAssertionSet into a list of NormalizedInterpretation objects.
        """
        pass


_NORMALIZER_REGISTRY: Dict[str, Type[BaseSourceNormalizer]] = {}


def register_normalizer(normalizer_cls: Type[BaseSourceNormalizer]) -> None:
    """Register a normalizer class for its declared source_id."""
    instance = normalizer_cls()
    _NORMALIZER_REGISTRY[instance.source_id] = normalizer_cls


def get_normalizer_for_source(source_id: str) -> BaseSourceNormalizer:
    """Instantiate and return the normalizer registered for source_id."""
    if source_id not in _NORMALIZER_REGISTRY:
        raise UnsupportedSourceError(
            f"No normalizer registered for source_id '{source_id}'. Supported sources: {list(_NORMALIZER_REGISTRY.keys())}"
        )
    return _NORMALIZER_REGISTRY[source_id]()


def normalize_source_assertions(assertion_set: SourceAssertionSet) -> List[NormalizedInterpretation]:
    """
    Top-level normalization entry point.

    Validates input SourceAssertionSet against Tier 1 contract, dispatches to the
    registered source normalizer, and returns normalized interpretations.
    """
    validate_source_assertion_set(assertion_set)
    normalizer = get_normalizer_for_source(assertion_set.provenance.source_id)
    return normalizer.normalize(assertion_set)
