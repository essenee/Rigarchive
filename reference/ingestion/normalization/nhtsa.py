"""
NHTSA vPIC Source Normalizer Implementation (RA-014 / RA-015).

Normalizes Tier 1 NHTSA vPIC assertions into explicit NormalizedInterpretation objects.
Implements strictly the 4 Category C mappings authorized by RA-014.
"""

from typing import List

from reference.ingestion.contracts import (
    NormalizedInterpretation,
    SourceAssertionSet,
)
from reference.ingestion.normalization.base import (
    BaseSourceNormalizer,
    register_normalizer,
)
from reference.ingestion.normalization.rules.nhtsa_rules import (
    NHTSA_CATEGORY_C_RULES,
)


class NHTSANormalizer(BaseSourceNormalizer):
    """Source normalizer for NHTSA vPIC REST API assertion sets."""

    @property
    def source_id(self) -> str:
        return "nhtsa_vpic"

    def normalize(self, assertion_set: SourceAssertionSet) -> List[NormalizedInterpretation]:
        interpretations: List[NormalizedInterpretation] = []

        for ast in assertion_set.source_assertions:
            key = ast.attribute_key
            if key in NHTSA_CATEGORY_C_RULES:
                rule = NHTSA_CATEGORY_C_RULES[key]
                interp = NormalizedInterpretation(
                    interpretation_id=f"interp_{ast.assertion_id}_{rule.target_attribute_key}",
                    source_assertion_ref=ast.assertion_id,
                    target_attribute_key=rule.target_attribute_key,
                    normalized_concept=ast.raw_value,
                    raw_source_value=ast.raw_value,
                    mapping_status="mapped",
                    normalization_notes=f"rule_id={rule.rule_id} method={rule.transformation_method}",
                    unknown_fields={
                        "rule_id": rule.rule_id,
                        "transformation_method": rule.transformation_method,
                    },
                )
                interpretations.append(interp)
            # Case B: Unknown Target Concept (no NormalizedInterpretation emitted; Tier 1 assertion preserved in SourceAssertionSet)
            pass


        return interpretations


# Register normalizer for dispatch
register_normalizer(NHTSANormalizer)
