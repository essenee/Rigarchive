"""Controlled factory configuration designations, independent of hardware identity."""
import re

from django.core.exceptions import ValidationError
DESIGNATION = re.compile(r"(?:[1-9][0-9]?-spd (?:Auto|Man|DCT|AMT)|CVT|eCVT)")
SOURCE_SPEED_TYPE = re.compile(
    r"([1-9][0-9]?)[ -]+(?:speed|spd)\s+(automatic|manual|auto|man|dct|amt)(?: transmission)?",
    re.IGNORECASE,
)


def validate_transmission(value):
    if not isinstance(value, str) or not DESIGNATION.fullmatch(value):
        raise ValidationError(
            "Use a factory designation such as 8-spd Auto, 6-spd Man, CVT, or eCVT.",
            code="invalid_transmission",
        )


def normalize_source_transmission(value):
    """Normalize a documented label only. Never infer a label from another field."""
    if not isinstance(value, str):
        raise ValidationError("Transmission evidence must supply a designation.")
    label = value.strip()
    if label.casefold() in ("cvt", "ecvt"):
        return "CVT" if label.casefold() == "cvt" else "eCVT"
    match = SOURCE_SPEED_TYPE.fullmatch(label)
    if not match:
        raise ValidationError("Unsupported or incomplete source transmission designation.")
    count, kind = match.groups()
    types = {"automatic": "Auto", "manual": "Man", "auto": "Auto", "man": "Man", "dct": "DCT", "amt": "AMT"}
    return f"{count}-spd {types[kind.casefold()]}"
