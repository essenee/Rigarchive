"""Shared RA-044 explicit terminology checks; pure, without ORM/bootstrap imports."""
import re
from decimal import Decimal, InvalidOperation


def supports(raw, key, expected, *, jeep=False):
    """Check a structured claim or explicit source terminology, never code inference.

    A composite configuration assertion can establish multiple attributes. An
    unrelated qualified assertion cannot establish them merely by being retained.
    """
    if isinstance(raw, dict):
        return key in raw and supports(raw[key], key, expected, jeep=jeep)
    if raw is None or isinstance(raw, bool):
        return False
    if key == "engine_displacement_liters":
        try:
            return Decimal(str(raw)) == Decimal(expected)
        except InvalidOperation:
            values = re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?:L\b|liters?\b|litres?\b)", str(raw), re.I)
            return len(values) == 1 and Decimal(values[0]) == Decimal(expected)
    if key == "engine_cylinders":
        if str(raw).isdigit():
            return int(raw) == expected
        values = re.findall(r"\b[VI][- ]?([1-9]\d*)\b", str(raw), re.I)
        return len(values) == 1 and int(values[0]) == expected
    text = re.sub(r"[_-]+", " ", str(raw).lower()).strip()
    if key == "engine_aspiration":
        terms = {"naturally_aspirated": r"\bnaturally aspirated\b", "turbocharged": r"\bturbo(?:charged)?\b",
                 "supercharged": r"\bsupercharged\b", "twincharged": r"\btwincharged\b", "other": r"^other$"}
    elif key == "fuel_type":
        terms = {"gasoline": r"\b(?:gasoline|petrol)\b", "diesel": r"\bdiesel\b"}
    else:
        # Remove compound labels before examining the generic HEV term.
        found = set()
        for token, pattern in (("plug_in_hybrid", r"\b(?:plug in hybrid|phev|4xe)\b"),
                               ("mild_hybrid", r"\b(?:mild hybrid|mhev)\b")):
            if re.search(pattern, text):
                found.add(token)
                text = re.sub(pattern, "", text)
        if jeep and re.search(r"\betorque\b", text):
            found.add("mild_hybrid")
        terms = {"none": r"^(?:none|nonhybrid|non hybrid)$", "hybrid": r"\b(?:hybrid|hev)\b"}
        found.update(token for token, pattern in terms.items() if re.search(pattern, text))
        return found == {expected}
    return {token for token, pattern in terms.items() if re.search(pattern, text)} == {expected}
