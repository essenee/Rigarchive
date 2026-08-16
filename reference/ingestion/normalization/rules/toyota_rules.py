"""
Toyota USA Grade Taxonomy & Drivetrain Normalization Rules (RA-021).

Provides empirical, evidence-backed normalization rules for Toyota factory grades and
drivetrain descriptors in compliance with RA-020 and ADR-0005.
"""

from typing import Any, Optional, Tuple

TOYOTA_FACTORY_GRADES = {
    "SR": "SR",
    "SR5": "SR5",
    "SR5 PREMIUM": "SR5 Premium",
    "SPORT": "Sport Edition",
    "SPORT EDITION": "Sport Edition",
    "TRD SPORT": "TRD Sport",
    "TRD OFF-ROAD": "TRD Off-Road",
    "TRD OFF-ROAD PREMIUM": "TRD Off-Road Premium",
    "VENTURE EDITION": "Venture Edition",
    "VENTURE SPECIAL EDITION": "Venture Special Edition",
    "LIMITED": "Limited",
    "NIGHTSHADE": "Nightshade",
    "NIGHTSHADE SPECIAL EDITION": "Nightshade Special Edition",
    "TRD PRO": "TRD Pro",
    "TRAIL": "Trail Edition",
    "TRAIL EDITION": "Trail Edition",
    "PRERUNNER": "PreRunner",
    "TRD PRERUNNER": "TRD PreRunner",
    "TRAILHUNTER": "Trailhunter",
    "DLX": "DLX",
    "X-RUNNER": "X-Runner",
    "S-RUNNER": "S-Runner",
    "BASE": "Base",
}

TOYOTA_NON_GRADE_PACKAGES = {
    "XP PREDATOR",
    "XP GUNNER",
    "KEEP IT WILD",
    "PREMIUM AUDIO",
    "THIRD-ROW SEATING",
}


def normalize_toyota_grade(raw_grade: Any) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Normalize raw Toyota grade descriptor into manufacturer-recognized factory grade/trim.
    Returns (normalized_trim, mapping_status, manufacturer_term).
    Rejects dealer/accessory packages and unmapped text.
    """
    if raw_grade is None or not isinstance(raw_grade, str):
        return None, "unmapped", None

    clean_str = raw_grade.strip()
    upper_str = clean_str.upper()

    if upper_str in TOYOTA_NON_GRADE_PACKAGES:
        return None, "unmapped", f"Rejected option/accessory package: '{clean_str}'"

    if upper_str in TOYOTA_FACTORY_GRADES:
        norm_trim = TOYOTA_FACTORY_GRADES[upper_str]
        return norm_trim, "mapped", f"Toyota Grade '{norm_trim}'"

    # Case-insensitive / mixed-case matching
    for key, norm_trim in TOYOTA_FACTORY_GRADES.items():
        if key == upper_str:
            return norm_trim, "mapped", f"Toyota Grade '{norm_trim}'"

    return None, "unmapped", f"Unrecognized Toyota grade: '{clean_str}'"


def normalize_toyota_drivetrain(raw_drive: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    Normalize Toyota drivetrain descriptor into generic classification and architecture.
    Returns (generic_classification, drivetrain_architecture).
    Enforces invariant: Full-time 4WD -> generic_drive_classification = 4WD, drivetrain_architecture = Full-time 4WD.
    """
    if not raw_drive or not isinstance(raw_drive, str):
        return None, None

    clean_str = raw_drive.strip().upper()

    if clean_str in ("2WD", "4X2", "REAR-WHEEL DRIVE"):
        return "2WD", "2WD"
    elif clean_str in ("PART-TIME 4WD", "PART-TIME 4X4"):
        return "4WD", "Part-time 4WD"
    elif clean_str in ("FULL-TIME 4WD", "FULL-TIME 4X4"):
        return "4WD", "Full-time 4WD"
    elif clean_str in ("4WD", "4X4"):
        return "4WD", "4WD"
    elif clean_str in ("AWD", "ALL-WHEEL DRIVE"):
        return "AWD", "AWD"

    return None, None
