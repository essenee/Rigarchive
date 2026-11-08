"""Explicit Candidate 2.1 value normalization, independent of source acquisition."""
from copy import deepcopy

from reference.ingestion.contracts import TechnicalValue
from reference.powertrain import decimal_string


def normalize_powertrain_interpretations(interpretations):
    """Preserve source mappings and raw lexemes; normalize only marketed liters.

    The caller must already have evidence-backed mappings for each classification.
    No engine-name, code, ESS or missing-label inference is performed here.
    """
    result = deepcopy(interpretations)
    for item in result:
        if item.target_attribute_key != "engine_displacement_liters" or item.mapping_status != "mapped":
            continue
        value = item.normalized_concept
        if isinstance(value, TechnicalValue):
            if value.normalized_value is not None:
                value.normalized_value = decimal_string(str(value.normalized_value))
        elif value is not None:
            item.normalized_concept = decimal_string(str(value))
    return result
