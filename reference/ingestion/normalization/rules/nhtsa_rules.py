"""
NHTSA vPIC Category C Mapping Rules (RA-014 / RA-015).

Contains declarative Category C mapping declarations authorized by RA-014 for NHTSA vPIC assertions.
"""

from typing import Any, Dict, NamedTuple, Optional


class MappingRule(NamedTuple):
    rule_id: str
    source_attribute_key: str
    target_attribute_key: str
    transformation_method: str
    raw_value_pattern: Optional[Any] = None


NHTSA_CATEGORY_C_RULES: Dict[str, MappingRule] = {
    "make_id": MappingRule(
        rule_id="nhtsa.make_id.direct",
        source_attribute_key="make_id",
        target_attribute_key="nhtsa_make_id",
        transformation_method="direct_copy",
    ),
    "make_name": MappingRule(
        rule_id="nhtsa.make_name.direct",
        source_attribute_key="make_name",
        target_attribute_key="make",
        transformation_method="direct_copy",
    ),
    "model_id": MappingRule(
        rule_id="nhtsa.model_id.direct",
        source_attribute_key="model_id",
        target_attribute_key="nhtsa_model_id",
        transformation_method="direct_copy",
    ),
    "model_name": MappingRule(
        rule_id="nhtsa.model_name.direct",
        source_attribute_key="model_name",
        target_attribute_key="model",
        transformation_method="direct_copy",
    ),
}
