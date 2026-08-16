"""
J.D. Power Automotive Reference Normalizer (RA-028).

Normalizes Tier 1 SourceAssertionSet artifacts acquired from J.D. Power
configuration enumeration datasets into Tier 2 NormalizedInterpretation arrays.
"""

from typing import List, Optional

from reference.ingestion.contracts import (
    NormalizedInterpretation,
    SourceAssertionSet,
    TechnicalValue,
)
from reference.ingestion.normalization.base import BaseSourceNormalizer
from reference.ingestion.normalization.rules.toyota_rules import (
    normalize_toyota_drivetrain,
    normalize_toyota_grade,
)
from reference.ingestion.validation import validate_source_assertion_set


class JDPowerNormalizer(BaseSourceNormalizer):
    """
    Source-specific normalizer for J.D. Power automotive reference configuration enumerations.
    Maps raw trim, drivetrain, engine, and provenance-derived market assertions into Tier 2 concepts.
    """

    @property
    def source_id(self) -> str:
        return "jd_power"

    def normalize(self, assertion_set: SourceAssertionSet) -> List[NormalizedInterpretation]:
        """Normalize a J.D. Power SourceAssertionSet into NormalizedInterpretation objects."""
        validate_source_assertion_set(assertion_set)

        interpretations: List[NormalizedInterpretation] = []
        source_app = assertion_set.provenance.source_applicability
        native_id = assertion_set.provenance.native_record_id or "unknown"

        interp_counter = 1

        def _next_id() -> str:
            nonlocal interp_counter
            res = f"interp_jdp_{native_id}_{interp_counter:02d}"
            interp_counter += 1
            return res

        for ast in assertion_set.source_assertions:
            key = ast.attribute_key
            val = ast.raw_value

            if key == "make_name" and val is not None:
                interpretations.append(
                    NormalizedInterpretation(
                        interpretation_id=_next_id(),
                        source_assertion_ref=ast.assertion_id,
                        target_attribute_key="make",
                        normalized_concept=str(val).strip(),
                        raw_source_value=val,
                        mapping_status="mapped",
                    )
                )

            elif key == "model_name" and val is not None:
                interpretations.append(
                    NormalizedInterpretation(
                        interpretation_id=_next_id(),
                        source_assertion_ref=ast.assertion_id,
                        target_attribute_key="model",
                        normalized_concept=str(val).strip(),
                        raw_source_value=val,
                        mapping_status="mapped",
                    )
                )

            elif key == "model_year" and val is not None:
                try:
                    parsed_year = int(val)
                    interpretations.append(
                        NormalizedInterpretation(
                            interpretation_id=_next_id(),
                            source_assertion_ref=ast.assertion_id,
                            target_attribute_key="model_year",
                            normalized_concept=parsed_year,
                            raw_source_value=val,
                            mapping_status="mapped",
                        )
                    )
                except (ValueError, TypeError):
                    pass

            elif key in ("manufacturer_grade", "trim") and val is not None:
                norm_trim, status, mfr_term = normalize_toyota_grade(val)
                interpretations.append(
                    NormalizedInterpretation(
                        interpretation_id=_next_id(),
                        source_assertion_ref=ast.assertion_id,
                        target_attribute_key="trim",
                        normalized_concept=norm_trim,
                        raw_source_value=val,
                        manufacturer_term=mfr_term or f"J.D. Power Trim ({val})",
                        mapping_status=status,
                    )
                )

            elif key == "drive_descriptor" and val is not None:
                generic_drive, drive_arch = normalize_toyota_drivetrain(val)
                if generic_drive:
                    interpretations.append(
                        NormalizedInterpretation(
                            interpretation_id=_next_id(),
                            source_assertion_ref=ast.assertion_id,
                            target_attribute_key="generic_drive_classification",
                            normalized_concept=generic_drive,
                            raw_source_value=val,
                            mapping_status="mapped",
                        )
                    )
                if drive_arch:
                    interpretations.append(
                        NormalizedInterpretation(
                            interpretation_id=_next_id(),
                            source_assertion_ref=ast.assertion_id,
                            target_attribute_key="drivetrain_architecture",
                            normalized_concept=drive_arch,
                            raw_source_value=val,
                            mapping_status="mapped",
                        )
                    )

            elif key == "engine_displacement_liters" and val is not None:
                try:
                    displ_float = float(val)
                    tech_val = TechnicalValue(
                        normalized_value=displ_float,
                        normalized_unit="L",
                        raw_source_string=str(val),
                    )
                    interpretations.append(
                        NormalizedInterpretation(
                            interpretation_id=_next_id(),
                            source_assertion_ref=ast.assertion_id,
                            target_attribute_key="engine_displacement_liters",
                            normalized_concept=tech_val,
                            raw_source_value=val,
                            mapping_status="mapped",
                        )
                    )
                except (ValueError, TypeError):
                    pass

            elif key == "engine_cylinders" and val is not None:
                try:
                    parsed_cyls = int(val)
                    interpretations.append(
                        NormalizedInterpretation(
                            interpretation_id=_next_id(),
                            source_assertion_ref=ast.assertion_id,
                            target_attribute_key="engine_cylinders",
                            normalized_concept=parsed_cyls,
                            raw_source_value=val,
                            mapping_status="mapped",
                        )
                    )
                except (ValueError, TypeError):
                    pass

            elif key == "market" and val is not None:
                if source_app is not None and source_app.market == str(val).strip():
                    interpretations.append(
                        NormalizedInterpretation(
                            interpretation_id=_next_id(),
                            source_assertion_ref=ast.assertion_id,
                            target_attribute_key="market",
                            normalized_concept=str(val).strip(),
                            raw_source_value=val,
                            manufacturer_term=f"Reference Commercial Market ({source_app.market})",
                            mapping_status="mapped",
                        )
                    )
                else:
                    interpretations.append(
                        NormalizedInterpretation(
                            interpretation_id=_next_id(),
                            source_assertion_ref=ast.assertion_id,
                            target_attribute_key="market",
                            normalized_concept=None,
                            raw_source_value=val,
                            normalization_notes="Market assertion rejected under Source-Independence Test: missing source_applicability metadata.",
                            mapping_status="unmapped",
                        )
                    )

        return interpretations
