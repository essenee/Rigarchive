"""
Repository-versioned mapping rule declarations for NHTSA and EPA (RA-014 / RA-015).
"""

from reference.ingestion.normalization.rules.epa_rules import (
    EPA_CATEGORY_C_RULES,
    EPA_DEFERRED_KNOWN_TARGETS,
)
from reference.ingestion.normalization.rules.nhtsa_rules import (

    NHTSA_CATEGORY_C_RULES,
)

__all__ = [
    "NHTSA_CATEGORY_C_RULES",
    "EPA_CATEGORY_C_RULES",
    "EPA_DEFERRED_KNOWN_TARGETS",
]
