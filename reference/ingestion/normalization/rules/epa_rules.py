"""
EPA FuelEconomy.gov Category C Mapping Rules (RA-014 / RA-015).

Contains declarative Category C mapping declarations authorized by RA-014 for EPA assertions.
"""

from typing import Any, Dict, List, NamedTuple, Optional


class MappingRule(NamedTuple):
    rule_id: str
    source_attribute_key: str
    target_attribute_key: str
    transformation_method: str
    raw_value_pattern: Optional[Any] = None
    target_value: Optional[Any] = None


# EPA Category C rules authorized for RA-015
EPA_CATEGORY_C_RULES: Dict[str, List[MappingRule]] = {
    "model_year": [
        MappingRule(
            rule_id="epa.model_year.parse_integer",
            source_attribute_key="model_year",
            target_attribute_key="model_year",
            transformation_method="parsed",
        )
    ],
    "make": [
        MappingRule(
            rule_id="epa.make.direct",
            source_attribute_key="make",
            target_attribute_key="make",
            transformation_method="direct_copy",
        )
    ],
    "drive_descriptor": [
        MappingRule(
            rule_id="epa.drive.part_time_4wd.classification",
            source_attribute_key="drive_descriptor",
            target_attribute_key="generic_drive_classification",
            transformation_method="exact_mapping",
            raw_value_pattern="Part-time 4WD",
            target_value="4WD",
        ),
        MappingRule(
            rule_id="epa.drive.part_time_4wd.architecture",
            source_attribute_key="drive_descriptor",
            target_attribute_key="drivetrain_architecture",
            transformation_method="interpreted",
            raw_value_pattern="Part-time 4WD",
            target_value="part_time_4wd",
        ),
    ],
    "engine_displacement_liters": [
        MappingRule(
            rule_id="epa.displ.parse_technical_value",
            source_attribute_key="engine_displacement_liters",
            target_attribute_key="engine_displacement_liters",
            transformation_method="parsed",
        )
    ],
    "engine_cylinders": [
        MappingRule(
            rule_id="epa.cyl.parse_integer",
            source_attribute_key="engine_cylinders",
            target_attribute_key="engine_cylinders",
            transformation_method="parsed",
        )
    ],
    "city_mpg_epa_rating": [
        MappingRule(
            rule_id="epa.city_mpg.parse_integer",
            source_attribute_key="city_mpg_epa_rating",
            target_attribute_key="city_mpg_epa_rating",
            transformation_method="parsed",
        )
    ],
    "highway_mpg_epa_rating": [
        MappingRule(
            rule_id="epa.hwy_mpg.parse_integer",
            source_attribute_key="highway_mpg_epa_rating",
            target_attribute_key="highway_mpg_epa_rating",
            transformation_method="parsed",
        )
    ],
}

# Known EPA target concepts whose specific values/mappings are Category B or unmapped in RA-015
EPA_DEFERRED_KNOWN_TARGETS: Dict[str, str] = {
    "model": "model",
    "transmission_descriptor": "transmission_descriptor",
    "vehicle_class": "vehicle_class",
    "engine_description": "engine_description",
}
