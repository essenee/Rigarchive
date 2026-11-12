"""RA-044 controlled powertrain vocabulary, wire values and presentation labels."""
from decimal import Decimal, InvalidOperation
import re

from django.core.exceptions import ValidationError

ASPIRATION = {
    "naturally_aspirated": "Naturally aspirated", "turbocharged": "Turbocharged",
    "supercharged": "Supercharged", "twincharged": "Twincharged", "other": "Other",
}
FUEL = {"gasoline": "Gasoline", "diesel": "Diesel"}
ELECTRIFICATION = {
    "none": ("None", ""), "mild_hybrid": ("Mild hybrid (MHEV)", "MHEV"),
    "hybrid": ("Hybrid (HEV)", "HEV"), "plug_in_hybrid": ("Plug-in hybrid (PHEV)", "PHEV"),
}
FIELDS = ("engine_displacement_liters", "engine_cylinders", "engine_aspiration",
          "fuel_type", "electrification_type")
BASE_FIELDS = ("model_year", "trim_name", "engine_name", "drivetrain", "market")
TAXONOMIES = {"engine_aspiration": ASPIRATION, "fuel_type": FUEL,
              "electrification_type": ELECTRIFICATION}


def decimal_string(value):
    """Marketed liters, without rounding or insignificant trailing zeros."""
    if isinstance(value, (bool, float)):
        raise ValidationError("Marketed displacement requires an exact decimal value.")
    try:
        number = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Invalid marketed displacement.")
    if not number.is_finite() or number <= 0 or number >= 1000 or number.as_tuple().exponent < -2:
        raise ValidationError("Marketed displacement must be positive with at most two fractional digits.")
    return format(number.normalize(), "f")


def validate_powertrain(values, *, complete=False):
    if not isinstance(values, dict) or set(values) != set(FIELDS):
        raise ValidationError("Powertrain requires exactly five structured attributes.")
    for key, value in values.items():
        if value is None:
            if complete:
                raise ValidationError(f"Missing evidenced powertrain attribute: {key}.")
            continue
        if key == "engine_displacement_liters":
            if type(value) is not str or decimal_string(value) != value:
                raise ValidationError("Displacement wire value must be a canonical decimal string.")
        elif key == "engine_cylinders":
            if type(value) is not int or not 1 <= value <= 32767:
                raise ValidationError("Cylinder count must be a positive small integer.")
        elif type(value) is not str or value not in TAXONOMIES[key]:
            raise ValidationError(f"Unsupported powertrain token: {key}.")
    if complete and values["engine_aspiration"] == "other":
        raise ValidationError("Other aspiration requires review before canonical creation.")


def record_powertrain(record):
    result = {key: getattr(record, key) for key in FIELDS}
    if result[FIELDS[0]] is not None:
        result[FIELDS[0]] = decimal_string(result[FIELDS[0]])
    return result


def qualified_slug(base, values, engine_name):
    validate_powertrain(values, complete=True)
    liters = re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)\s*L\b", engine_name, re.I)
    cylinders = re.findall(r"\b[VI][- ]?([1-9]\d*)\b", engine_name, re.I)
    if (len(liters) != 1 or len(cylinders) != 1
            or Decimal(liters[0]) != Decimal(values[FIELDS[0]])
            or int(cylinders[0]) != values[FIELDS[1]]):
        raise ValidationError("Engine descriptor does not express the assessed displacement/cylinders.")
    suffixes = [{"turbocharged": "turbo", "supercharged": "supercharged", "twincharged": "twincharged"}.get(values[FIELDS[2]]),
                "diesel" if values["fuel_type"] == "diesel" else None,
                ELECTRIFICATION[values["electrification_type"]][1].lower() or None]
    slug = "-".join([base] + [s for s in suffixes if s])
    if len(slug) > 180:
        raise ValidationError("Structured target slug exceeds 180 characters.")
    return slug


def _clean_engine_name(record, label):
    """Remove redundant standalone turbo and associated fuel/electrification tags from engine descriptor when separately displayed."""
    if getattr(record, "engine_aspiration", None) == "turbocharged":
        cleaned = label
        if getattr(record, "fuel_type", None) == "diesel":
            cleaned = re.sub(r"\b(Turbo\s*[-/]?\s*Diesel|Diesel\s*[-/]?\s*Turbo)\b", "", cleaned, flags=re.IGNORECASE)
        if getattr(record, "electrification_type", None) in ("plug_in_hybrid", "hybrid", "mild_hybrid"):
            cleaned = re.sub(r"\b(Turbo\s*[-/]?\s*PHEV|PHEV\s*[-/]?\s*Turbo)\b", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\b(Turbo\s*[-/]?\s*HEV|HEV\s*[-/]?\s*Turbo)\b", "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\b(Turbo\s*[-/]?\s*MHEV|MHEV\s*[-/]?\s*Turbo)\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bTurbo\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            return cleaned
    return label


def engine_label(record, *, short=False):
    raw_label = record.engine_name or "Engine not specified"
    label = _clean_engine_name(record, raw_label)
    extras = [ASPIRATION.get(record.engine_aspiration) if record.engine_aspiration not in (None, "naturally_aspirated") else None,
              FUEL.get(record.fuel_type) if record.fuel_type == "diesel" else None]
    if short:
        extras.append(ELECTRIFICATION.get(record.electrification_type, ("", ""))[1])
        return " · ".join([label] + [s for s in extras if s])
    if record.electrification_type not in (None, "none"):
        extras.append(ELECTRIFICATION.get(record.electrification_type, ("", ""))[0])
    return ", ".join([label] + [s for s in extras if s])
