"""
Volkswagen USA Grade Taxonomy & Drivetrain Normalization Rules (RA-036).

Provides empirical, evidence-backed normalization rules for Volkswagen factory grades and
drivetrain descriptors (e.g. 4MOTION) in compliance with RA-020 and ADR-0005.
"""

from typing import Any, Optional, Tuple

VOLKSWAGEN_FACTORY_GRADES = {
    "BASE": "Base",
    "V6": "V6",
    "V8": "V8",
    "V8 X": "V8 X",
    "V10 TDI": "V10 TDI",
    "TDI": "TDI",
    "VR6": "VR6",
    "VR6 SPORT": "VR6 Sport",
    "VR6 LUX": "VR6 Lux",
    "VR6 EXECUTIVE": "VR6 Executive",
    "V8 SPORT": "V8 Sport",
    "V8 LUX": "V8 Lux",
    "V8 EXECUTIVE": "V8 Executive",
    "TDI SPORT": "TDI Sport",
    "TDI LUX": "TDI Lux",
    "TDI EXECUTIVE": "TDI Executive",
    "HYBRID": "Hybrid",
    "SPORT": "Sport",
    "LUX": "Lux",
    "EXECUTIVE": "Executive",
    "WOLFSBURG EDITION": "Wolfsburg Edition",
    "R-LINE": "R-Line",
}


def normalize_volkswagen_grade(raw_grade: Any) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Normalize raw Volkswagen grade descriptor into manufacturer-recognized factory grade/trim.
    Returns (normalized_trim, mapping_status, manufacturer_term).
    """
    if raw_grade is None or not isinstance(raw_grade, str):
        return None, "unmapped", None

    clean_str = raw_grade.strip()
    upper_str = clean_str.upper()

    if upper_str in VOLKSWAGEN_FACTORY_GRADES:
        norm_trim = VOLKSWAGEN_FACTORY_GRADES[upper_str]
        return norm_trim, "mapped", f"Volkswagen Grade '{norm_trim}'"

    for key, norm_trim in VOLKSWAGEN_FACTORY_GRADES.items():
        if key == upper_str:
            return norm_trim, "mapped", f"Volkswagen Grade '{norm_trim}'"

    return None, "unmapped", f"Unrecognized Volkswagen grade: '{clean_str}'"


def normalize_volkswagen_drivetrain(raw_drive: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalize Volkswagen drivetrain descriptor into generic classification and architecture.
    Returns (generic_classification, drivetrain_architecture).
    """
    if not raw_drive or not isinstance(raw_drive, str):
        return None, None

    clean_str = raw_drive.strip().upper()

    if clean_str in ("4MOTION", "4WD", "4X4", "AWD", "ALL-WHEEL DRIVE", "FULL-TIME 4WD", "PERMANENT 4WD"):
        return "AWD", "Full-time 4WD"
    elif clean_str in ("FWD", "FRONT-WHEEL DRIVE", "2WD", "4X2"):
        return "2WD", "2WD"

    return None, None
