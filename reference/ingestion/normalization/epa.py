"""
EPA FuelEconomy.gov Source Normalizer Implementation (RA-014 / RA-015).

Normalizes Tier 1 EPA assertions into explicit NormalizedInterpretation objects.
Implements strictly the Category C mappings authorized by RA-014 for EPA.
"""

from typing import List, Optional

from reference.ingestion.contracts import (
    NormalizedInterpretation,
    SourceAssertionSet,
    TechnicalValue,
)
from reference.ingestion.normalization.base import (
    BaseSourceNormalizer,
    register_normalizer,
)
from reference.ingestion.normalization.rules.epa_rules import (
    EPA_CATEGORY_C_RULES,
    EPA_DEFERRED_KNOWN_TARGETS,
)


class EPANormalizer(BaseSourceNormalizer):
    """Source normalizer for EPA FuelEconomy.gov REST API assertion sets."""

    @property
    def source_id(self) -> str:
        return "epa_fueleconomy"

    def normalize(self, assertion_set: SourceAssertionSet) -> List[NormalizedInterpretation]:
        interpretations: List[NormalizedInterpretation] = []

        for ast in assertion_set.source_assertions:
            key = ast.attribute_key
            raw_val = ast.raw_value

            if key == "model_year":
                parsed_year: Optional[int] = None
                try:
                    parsed_year = int(str(raw_val).strip())
                    status = "mapped"
                    notes = "rule_id=epa.model_year.parse_integer method=parsed"
                except (ValueError, TypeError):
                    status = "unmapped"
                    notes = f"Parsing failure for model_year integer from '{raw_val}'"

                interp = NormalizedInterpretation(
                    interpretation_id=f"interp_{ast.assertion_id}_model_year",
                    source_assertion_ref=ast.assertion_id,
                    target_attribute_key="model_year",
                    normalized_concept=parsed_year,
                    raw_source_value=raw_val,
                    mapping_status=status,
                    normalization_notes=notes,
                    unknown_fields={
                        "rule_id": "epa.model_year.parse_integer",
                        "transformation_method": "parsed",
                    },
                )
                interpretations.append(interp)

            elif key == "make":
                rule = EPA_CATEGORY_C_RULES["make"][0]
                interp = NormalizedInterpretation(
                    interpretation_id=f"interp_{ast.assertion_id}_make",
                    source_assertion_ref=ast.assertion_id,
                    target_attribute_key="make",
                    normalized_concept=raw_val,
                    raw_source_value=raw_val,
                    mapping_status="mapped",
                    normalization_notes=f"rule_id={rule.rule_id} method={rule.transformation_method}",
                    unknown_fields={
                        "rule_id": rule.rule_id,
                        "transformation_method": rule.transformation_method,
                    },
                )
                interpretations.append(interp)

            elif key == "drive_descriptor":
                str_val = str(raw_val).strip() if raw_val is not None else ""
                if str_val == "Part-time 4WD":
                    # Approved Category C mappings for "Part-time 4WD":
                    # 1. generic_drive_classification = "4WD" (exact_mapping)
                    rule1 = EPA_CATEGORY_C_RULES["drive_descriptor"][0]
                    interp1 = NormalizedInterpretation(
                        interpretation_id=f"interp_{ast.assertion_id}_generic_drive",
                        source_assertion_ref=ast.assertion_id,
                        target_attribute_key=rule1.target_attribute_key,
                        normalized_concept=rule1.target_value,
                        raw_source_value=raw_val,
                        mapping_status="mapped",
                        normalization_notes=f"rule_id={rule1.rule_id} method={rule1.transformation_method}",
                        unknown_fields={
                            "rule_id": rule1.rule_id,
                            "transformation_method": rule1.transformation_method,
                        },
                    )
                    interpretations.append(interp1)

                    # 2. drivetrain_architecture = "part_time_4wd" (interpreted)
                    rule2 = EPA_CATEGORY_C_RULES["drive_descriptor"][1]
                    interp2 = NormalizedInterpretation(
                        interpretation_id=f"interp_{ast.assertion_id}_architecture",
                        source_assertion_ref=ast.assertion_id,
                        target_attribute_key=rule2.target_attribute_key,
                        normalized_concept=rule2.target_value,
                        raw_source_value=raw_val,
                        mapping_status="mapped",
                        normalization_notes=f"rule_id={rule2.rule_id} method={rule2.transformation_method}",
                        unknown_fields={
                            "rule_id": rule2.rule_id,
                            "transformation_method": rule2.transformation_method,
                        },
                    )
                    interpretations.append(interp2)
                else:
                    # Case A: Known target concept (generic_drive_classification), unmapped value
                    interp = NormalizedInterpretation(
                        interpretation_id=f"interp_unmapped_{ast.assertion_id}_generic_drive",
                        source_assertion_ref=ast.assertion_id,
                        target_attribute_key="generic_drive_classification",
                        normalized_concept=None,
                        raw_source_value=raw_val,
                        mapping_status="unmapped",
                        normalization_notes=f"Unmapped value '{raw_val}' for generic_drive_classification",
                        unknown_fields={
                            "transformation_method": "unmapped",
                        },
                    )
                    interpretations.append(interp)

            elif key == "engine_displacement_liters":
                tech_val: Optional[TechnicalValue] = None
                try:
                    flt_displ = float(str(raw_val).strip())
                    tech_val = TechnicalValue(
                        normalized_value=flt_displ,
                        normalized_unit="L",
                        raw_source_string=str(raw_val),
                    )
                    status = "mapped"
                    notes = "rule_id=epa.displ.parse_technical_value method=parsed"
                except (ValueError, TypeError):
                    status = "unmapped"
                    notes = f"Parsing failure for displacement float from '{raw_val}'"

                interp = NormalizedInterpretation(
                    interpretation_id=f"interp_{ast.assertion_id}_displacement",
                    source_assertion_ref=ast.assertion_id,
                    target_attribute_key="engine_displacement_liters",
                    normalized_concept=tech_val,
                    raw_source_value=raw_val,
                    mapping_status=status,
                    normalization_notes=notes,
                    unknown_fields={
                        "rule_id": "epa.displ.parse_technical_value",
                        "transformation_method": "parsed",
                    },
                )
                interpretations.append(interp)

            elif key == "engine_cylinders":
                parsed_cyl: Optional[int] = None
                try:
                    parsed_cyl = int(str(raw_val).strip())
                    status = "mapped"
                    notes = "rule_id=epa.cyl.parse_integer method=parsed"
                except (ValueError, TypeError):
                    status = "unmapped"
                    notes = f"Parsing failure for cylinders integer from '{raw_val}'"

                interp = NormalizedInterpretation(
                    interpretation_id=f"interp_{ast.assertion_id}_cylinders",
                    source_assertion_ref=ast.assertion_id,
                    target_attribute_key="engine_cylinders",
                    normalized_concept=parsed_cyl,
                    raw_source_value=raw_val,
                    mapping_status=status,
                    normalization_notes=notes,
                    unknown_fields={
                        "rule_id": "epa.cyl.parse_integer",
                        "transformation_method": "parsed",
                    },
                )
                interpretations.append(interp)

            elif key == "city_mpg_epa_rating":
                parsed_mpg: Optional[int] = None
                try:
                    parsed_mpg = int(str(raw_val).strip())
                    status = "mapped"
                    notes = "rule_id=epa.city_mpg.parse_integer method=parsed"
                except (ValueError, TypeError):
                    status = "unmapped"
                    notes = f"Parsing failure for city MPG rating integer from '{raw_val}'"

                interp = NormalizedInterpretation(
                    interpretation_id=f"interp_{ast.assertion_id}_city_mpg",
                    source_assertion_ref=ast.assertion_id,
                    target_attribute_key="city_mpg_epa_rating",
                    normalized_concept=parsed_mpg,
                    raw_source_value=raw_val,
                    mapping_status=status,
                    normalization_notes=notes,
                    unknown_fields={
                        "rule_id": "epa.city_mpg.parse_integer",
                        "transformation_method": "parsed",
                    },
                )
                interpretations.append(interp)

            elif key == "highway_mpg_epa_rating":
                parsed_hwy: Optional[int] = None
                try:
                    parsed_hwy = int(str(raw_val).strip())
                    status = "mapped"
                    notes = "rule_id=epa.hwy_mpg.parse_integer method=parsed"
                except (ValueError, TypeError):
                    status = "unmapped"
                    notes = f"Parsing failure for highway MPG rating integer from '{raw_val}'"

                interp = NormalizedInterpretation(
                    interpretation_id=f"interp_{ast.assertion_id}_highway_mpg",
                    source_assertion_ref=ast.assertion_id,
                    target_attribute_key="highway_mpg_epa_rating",
                    normalized_concept=parsed_hwy,
                    raw_source_value=raw_val,
                    mapping_status=status,
                    normalization_notes=notes,
                    unknown_fields={
                        "rule_id": "epa.hwy_mpg.parse_integer",
                        "transformation_method": "parsed",
                    },
                )
                interpretations.append(interp)

            elif key in EPA_DEFERRED_KNOWN_TARGETS:
                # Case A: Known target concept (e.g. model, transmission_descriptor), deferred mapping in RA-015
                target_key = EPA_DEFERRED_KNOWN_TARGETS[key]
                interp = NormalizedInterpretation(
                    interpretation_id=f"interp_unmapped_{ast.assertion_id}_{target_key}",
                    source_assertion_ref=ast.assertion_id,
                    target_attribute_key=target_key,
                    normalized_concept=None,
                    raw_source_value=raw_val,
                    mapping_status="unmapped",
                    normalization_notes=f"Mapping deferred for EPA attribute key '{key}'",
                    unknown_fields={
                        "transformation_method": "unmapped",
                    },
                )
                interpretations.append(interp)

            # Case B: Unknown Target Concept (no NormalizedInterpretation emitted; Tier 1 assertion preserved in SourceAssertionSet)
            pass

        return interpretations



# Register normalizer for dispatch
register_normalizer(EPANormalizer)
