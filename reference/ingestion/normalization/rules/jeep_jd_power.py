"""Bounded core Wrangler identity rules for explicit J.D. Power rows."""
import re


def wrangler_grade(year, designation, drive, displacement, cylinders, *, source_locator=None):
    """Map a single source designation, requiring its mechanics to agree."""
    if type(year) is int and year == 2018:
        scopes = {
            "https://www.jdpower.com/cars/2018/jeep/wrangler/trim": ("2D", {"Sport", "Rubicon"}),
            "https://www.jdpower.com/cars/2018/jeep/wrangler-unlimited/trim": ("4D", {"Sport", "Sahara", "Rubicon"}),
        }
        scope = scopes.get(source_locator) if isinstance(source_locator, str) else None
        match = re.fullmatch(r"Utility (2D|4D) (Sport|Sahara|Rubicon) 4WD V6",
                             designation if isinstance(designation, str) else "")
        if (not scope or not match or match[1] != scope[0] or match[2] not in scope[1]
                or drive != "4WD" or type(displacement) not in (int, float)
                or displacement != 3.6 or type(cylinders) is not int or cylinders != 6):
            raise ValueError("Unsupported or incomplete MY2018 Wrangler JL source identity.")
        # The source route scopes normalization only. Generation resolution still
        # requires independently applicable correspondence for overlapping MY2018.
        return ("Unlimited " if match[1] == "4D" else "") + match[2]

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
