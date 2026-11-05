"""Evidence-scoped Jeep Wrangler rules and legacy W1 normalization."""
import re

from reference.ingestion.acquisition.jeep import (
    JK_REMAINING_GRADES_EXTRACTOR, JK_UNLIMITED_SPORT_HASH, JK_UNLIMITED_SPORT_REVISION, PUBLICATIONS,
)
from reference.ingestion.contracts import NormalizedInterpretation, TechnicalValue
from reference.ingestion.generation_correspondence import digest
from reference.ingestion.serialization import source_assertion_to_dict
from reference.ingestion.validation import validate_source_assertion_set


_STAGE1_SET = "pdf-page-10-sport-unlimited"
_STAGE1_EXTRACTOR = "jeep_2018_jk_unlimited_sport_pdf"
# Each set binds its exact reviewed assertion IDs, values and locations.
_REVIEWED_JK_ROWS = {
    _STAGE1_SET: (_STAGE1_EXTRACTOR, "sha256:e2e9c37056417b1879e7098f6aa54dbb6c775b3befe0560a2dfcc7cc1fb7267c"),
    "pdf-page-9-sahara": (JK_REMAINING_GRADES_EXTRACTOR, "sha256:13dacaa1d13ca20b4446fee5d89d3ff8dbee399ddef5b43c25d0d9d8ce3199f0"),
    "pdf-page-9-unlimited-sahara": (JK_REMAINING_GRADES_EXTRACTOR, "sha256:7d53ab4d57f763c2683062618a301d257960b460971eeb101193ab86865967b2"),
    "pdf-page-9-rubicon": (JK_REMAINING_GRADES_EXTRACTOR, "sha256:238a086803b5413aa9638b96b7591e7acb7e40df4dbb9f73146e57c0226846ea"),
    "pdf-page-9-unlimited-rubicon": (JK_REMAINING_GRADES_EXTRACTOR, "sha256:52a52c489bcff20be62de2a68b3340d46a599df98409a4c1d60601228fb3e766"),
}


def _reviewed_2018_jk_row(assertions):
    provenance = assertions.provenance
    ep = provenance.extraction_provenance
    app = provenance.source_applicability
    reviewed = _REVIEWED_JK_ROWS.get(provenance.native_record_id)
    rows = sorted(assertions.source_assertions, key=lambda row: row.assertion_id)
    if (
        assertions.envelope.schema_version != "1.1.0"
        or reviewed is None
        or provenance.source_locator != PUBLICATIONS["jk"]["url"]
        or provenance.unknown_fields.get("publication_revision") != JK_UNLIMITED_SPORT_REVISION
        or provenance.unknown_fields.get("publisher") != "FCA US LLC"
        or app is None or app.market != "US" or app.publisher_jurisdiction != "FCA US LLC"
        or app.applicability_basis != "official_jeep_en_us_publication"
        or app.applicability_scope != "model_year"
        or ep is None or ep.extractor_id != reviewed[0]
        or ep.extractor_version != "1.0.0" or ep.extraction_mode != "manually_verified_transcription"
        or ep.raw_artifact_hash != JK_UNLIMITED_SPORT_HASH
        or ep.raw_artifact_reference != f"storage/raw_source_artifacts/jeep_usa/{JK_UNLIMITED_SPORT_HASH[7:]}.pdf"
        or digest([source_assertion_to_dict(row) for row in rows]) != reviewed[1]
    ):
        raise ValueError("Exact reviewed 2018 US JK configuration evidence required.")
    return rows


def _normalize_reviewed_jk_row(rows):
    """Map one already reviewed configuration row. Admission happens upstream."""
    by_key = {row.attribute_key: row for row in rows}
    required = {
        "make_name", "model_name", "model_year", "market", "generation_designation",
        "body_designation", "manufacturer_grade", "engine_descriptor", "drive_descriptor",
    }
    if (len(rows) != len(required) or set(by_key) != required
            or any(not isinstance(row.raw_value, str) for row in rows)):
        raise ValueError("One complete, nonconflicting JK configuration row required.")

    def raw(key):
        return by_key[key].raw_value

    if (raw("make_name"), raw("model_name"), raw("market"), raw("generation_designation")) != (
        "Jeep", "Wrangler", "US", "JK",
    ):
        raise ValueError("Jeep Wrangler JK US configuration required.")
    year = raw("model_year")
    if year not in {str(value) for value in range(2007, 2019)}:
        raise ValueError("Unsupported JK model year.")
    year = int(year)
    base_grade = "X" if year <= 2009 else "Sport"
    grade = raw("manufacturer_grade").replace("®", "").casefold()
    unlimited = raw("body_designation") == "Wrangler Unlimited"
    if not unlimited and raw("body_designation") != "Wrangler":
        raise ValueError("Reviewed Wrangler body designation required.")

    trim = None
    for core_grade in (base_grade, "Sahara", "Rubicon"):
        spellings = {core_grade.casefold()}
        if unlimited:
            spellings.update(name.casefold() for name in (
                f"Unlimited {core_grade}", f"{core_grade} Unlimited", f"Wrangler Unlimited {core_grade}",
            ))
        if grade in spellings:
            trim = f"Unlimited {core_grade}" if unlimited else core_grade
            break
    if trim is None:
        raise ValueError("Unsupported JK grade for this model year and body.")

    engine = re.sub(r"\s*®\s*", "® ", raw("engine_descriptor"))
    engines = {"3.8L V6", "3.8L V6 SMPI", "3.8L V6 SMPI engine"} if year <= 2011 else {
        "3.6L Pentastar® V6", "3.6L Pentastar V6",
    }
    if engine not in engines:
        raise ValueError("Unsupported JK model-year engine descriptor.")
    displacement = 3.8 if year <= 2011 else 3.6
    drive = re.sub(r"\s*®\s*", "® ", raw("drive_descriptor"))
    if drive == "2WD":
        if not (unlimited and year <= 2010 and trim in (f"Unlimited {base_grade}", "Unlimited Sahara")):
            raise ValueError("Unsupported JK 2WD configuration.")
        classification = "2WD"
    elif drive == "4WD" or (
        trim.endswith("Rubicon") and drive == "Rock-Trac® 4x4 system"
    ) or (
        not trim.endswith("Rubicon") and drive == "Command-Trac® 4x4 system"
    ):
        classification = "4WD"
    else:
        raise ValueError("Unsupported JK drivetrain applicability.")

    mappings = (
        ("make_name", "make", "Jeep"), ("model_name", "model", "Wrangler"),
        ("model_year", "model_year", year), ("market", "market", "US"),
        ("manufacturer_grade", "trim", trim),
        ("engine_descriptor", "engine_displacement_liters",
         TechnicalValue(displacement, "L", raw("engine_descriptor"))),
        ("engine_descriptor", "engine_cylinders", 6),
        ("drive_descriptor", "generic_drive_classification", classification),
    )
    return [
        NormalizedInterpretation(
            f"{by_key[source].assertion_id}_{key}", by_key[source].assertion_id, key, value,
            raw_source_value=raw(source), manufacturer_term=raw(source),
            normalization_notes="jeep_jk_reviewed_row/1.0.0; scoped to the reviewed configuration assertion set",
        )
        for source, key, value in mappings
    ]


def normalize_jeep(assertions):
    validate_source_assertion_set(assertions)
    if assertions.provenance.source_id != "jeep_usa":
        raise ValueError("Jeep manufacturer assertions required.")
    provenance = assertions.provenance
    ep = provenance.extraction_provenance
    if provenance.native_record_id in _REVIEWED_JK_ROWS or (
        ep and ep.extractor_id in {_STAGE1_EXTRACTOR, JK_REMAINING_GRADES_EXTRACTOR}
    ):
        return _normalize_reviewed_jk_row(_reviewed_2018_jk_row(assertions))
    if any(
        row.attribute_key == "body_designation"
        for row in assertions.source_assertions
    ):
        raise ValueError("No reviewed JK normalization rule for this assertion set.")
    result = []
    for ast in assertions.source_assertions:
        mappings = {
            ("make_name", "Jeep"): [("make", "Jeep")],
            ("model_name", "Wrangler"): [("model", "Wrangler")],
            ("model_year", "2018"): [("model_year", 2018)],
            ("engine_descriptor", "3.6L Pentastar® V6"): [
                ("engine_displacement_liters", TechnicalValue(3.6, "L", str(ast.raw_value))),
                ("engine_cylinders", 6)],
            ("drive_descriptor", "Command-Trac"): [("generic_drive_classification", "4WD")],
        }
        rule_value = re.sub(r"\s*®\s*", "® ", str(ast.raw_value))
        values = mappings.get((ast.attribute_key, rule_value), [])
        if ast.attribute_key == "manufacturer_grade":
            result.append(NormalizedInterpretation(
                f"{ast.assertion_id}_trim", ast.assertion_id, "trim", None,
                raw_source_value=ast.raw_value, manufacturer_term=str(ast.raw_value),
                mapping_status="unmapped",
                normalization_notes="Sport is a source grade; its specific two-door baseline association requires review. Do not promote a body-ambiguous baseline.",
            ))
        app = assertions.provenance.source_applicability
        if ast.attribute_key == "market" and ast.raw_value == "US" and app and app.market == "US" and app.applicability_basis == "official_jeep_en_us_publication":
            values = [("market", "US")]
        for key, value in values:
            result.append(NormalizedInterpretation(
                f"{ast.assertion_id}_{key}", ast.assertion_id, key, value,
                raw_source_value=ast.raw_value,
                normalization_notes="jeep_2018_pilot/1.0.0; exact source rule; body applicability remains unresolved",
            ))
    return result
