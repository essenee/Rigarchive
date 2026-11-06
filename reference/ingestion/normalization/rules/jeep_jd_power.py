"""Bounded core Wrangler identity rules for explicit J.D. Power rows."""
import re


def wrangler_grade(year, designation, drive, displacement, cylinders):
    """Map a single source designation, requiring its mechanics to agree."""
    match = re.fullmatch(
        r"Utility (2D|4D) ((?:Unlimited )?(?:X|Sport|Sahara|Rubicon)) (2WD|4WD)(?: V6)?",
        designation if isinstance(designation, str) else "",
    )
    if type(year) is not int or not 2007 <= year <= 2017 or not match:
        raise ValueError("Unsupported J.D. Power Wrangler year or core designation.")
    body, trim, listed_drive = match.groups()
    unlimited = trim.startswith("Unlimited ")
    grade = trim.removeprefix("Unlimited ")
    if ((body == "4D") != unlimited or drive != listed_drive
            or (grade == "X" and year > 2009) or (grade == "Sport" and year < 2010)
            or (drive == "2WD" and (not unlimited or year > 2010 or grade == "Rubicon"))
            or type(displacement) not in (int, float)
            or displacement != (3.8 if year <= 2011 else 3.6)
            or type(cylinders) is not int or cylinders != 6):
        raise ValueError("Incomplete or contradictory J.D. Power Wrangler identity.")
    return trim
