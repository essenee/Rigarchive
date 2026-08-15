"""
Reference Data Ingestion Candidate Construction Package (RA-016 / RA-017).

Provides pure Python candidate configuration construction and aggregation entry points,
transforming caller-supplied CandidateIdentity workflow context and normalized source evidence
into validated CandidateConfigurationDocument artifacts.
"""

from reference.ingestion.candidate.builder import (
    CandidateConstructionError,
    construct_candidate_configuration,
)

__all__ = [
    "CandidateConstructionError",
    "construct_candidate_configuration",
]
