"""Bounded local intake and lossless-source retention for the 2018 Jeep pilot.

Page text is retained pending semantic/table review, not a Full Specifications
schema or a claim that PDF text extraction captures artwork and reading order.
"""
import hashlib
import io
import re
from datetime import datetime, timezone
from pathlib import Path

from pypdf import PdfReader

from reference.ingestion.acquisition.base import AcquisitionError
from reference.ingestion.acquisition.snapshots import RawAcquisitionResult
from reference.ingestion.contracts import (
    Envelope, ExtractionProvenance, SourceApplicability, SourceAssertion,
    SourceAssertionSet, SourceMetadata,
)
from reference.ingestion.validation import validate_source_assertion_set


PUBLICATIONS = {
    "jk": {
        "filename": "2018_wrangler_jk_brochure.pdf", "pages": 13,
        "form": "74-383-3802", "sport_page": 10,
        "url": "https://www.jeep.com/content/dam/fca-brands/na/jeep/en_us/global/pdf/brochure/eBrochure%20-%20Jeep%20Wrangler%20JK%20%282018%29_ver01.pdf",
    },
    "jl": {
        "filename": "2018_wrangler_jl_reveal_brochure.pdf", "pages": 8,
        "form": "74-383-3871", "sport_page": 6,
        "url": "https://www.jeep.com/content/dam/fca-brands/na/jeep/en_us/global/pdf/brochure/Jeep_Wrangler_JL_Reveal_Brochure_2018.pdf",
    },
}
EXTRACTOR_ID = "jeep_2018_brochure_pdf"
EXTRACTOR_VERSION = "1.0.0"


def acquire_local(path, publication):
    spec = PUBLICATIONS[publication]
    raw = Path(path).read_bytes()
    if not raw.startswith(b"%PDF-") or len(raw) > 20 * 1024 * 1024:
        raise AcquisitionError("Expected a bounded original PDF publication.")
    return RawAcquisitionResult(
        source_id="jeep_usa", source_locator=spec["url"],
        acquired_at=datetime.now(timezone.utc).isoformat(),
        content_type="application/pdf", raw_bytes=raw,
        source_applicability=SourceApplicability(
            market="US", applicability_basis="official_jeep_en_us_publication",
            publisher_jurisdiction="FCA US LLC", applicability_scope="model_year",
        ),
        acquisition_method="local_file", original_filename=Path(path).name,
    )


def extract_brochure(raw, metadata, publication):
    spec = PUBLICATIONS[publication]
    actual = "sha256:" + hashlib.sha256(raw).hexdigest()
    if metadata.source_id != "jeep_usa" or actual != metadata.content_hash:
        raise AcquisitionError("Snapshot source/hash mismatch.")
    if metadata.publisher_locator != spec["url"]:
        raise AcquisitionError("Unexpected publication locator.")
    reader = PdfReader(io.BytesIO(raw))
    pages = [page.extract_text() or "" for page in reader.pages]
    if len(pages) != spec["pages"] or spec["form"] not in pages[-1] or "2018" not in pages[0]:
        raise AcquisitionError("Unsupported publication layout/revision; review required.")
    sport = pages[spec["sport_page"] - 1]
    compact = re.sub(r"\s+", " ", sport)
    engine = re.search(r"3\.6L Pentastar\s*®?\s*V6", compact)
    if "SPORT" not in sport or engine is None:
        raise AcquisitionError("Sport powertrain section not established.")
    if "Command-Trac" not in sport:
        raise AcquisitionError("Sport transfer-case evidence missing.")
    assertions = []
    for number, (page, text) in enumerate(zip(reader.pages, pages), 1):
        assertions.append(SourceAssertion(
            assertion_id=f"page_{number:02d}", attribute_key="published_page_content",
            raw_value={"plain_text": text, "layout_text": page.extract_text(extraction_mode="layout") or ""},
            source_context=f"PDF page {number}; original bytes preserve artwork, tables, footnotes and rotations",
            unknown_fields={
                "accounting": "retained_pending_representation", "pdf_page": number,
                "limitations": "Text is not a semantic table parser or complete visual transcription.",
            },
        ))
    def add(key, value, location):
        assertions.append(SourceAssertion(f"identity_{key}", key, value, location))
    add("make_name", "Jeep", "Publisher colophon and Jeep branding")
    add("model_name", "Wrangler", "Publication body/branding")
    add("model_year", "2018", "PDF cover")
    add("manufacturer_grade", "Sport", f"PDF page {spec['sport_page']}; SPORT section")
    add("engine_descriptor", engine.group(0), f"PDF page {spec['sport_page']}; Sport standard equipment")
    add("drive_descriptor", "Command-Trac", f"PDF page {spec['sport_page']}; Sport standard equipment")
    add("market", "US", "Official Jeep en_us publication; FCA US LLC colophon")
    if publication == "jl":
        if "ALL-NEW 2018 WRANGLER" not in re.sub(r"\s+", " ", pages[0]):
            raise AcquisitionError("All-new source section identity missing.")
        add("generation_section", "ALL-NEW 2018 WRANGLER", "PDF page 1; source title, not a canonical generation code")
    # Never manufacture JK/JL codes, source order codes or a two-door grade join.
    provenance = SourceMetadata(
        source_id="jeep_usa", source_type="manufacturer_specification",
        source_locator=metadata.publisher_locator, retrieved_at=metadata.acquired_at,
        native_record_id=f"pdf-page-{spec['sport_page']}-sport-section",
        acquisition_method="local_file", review_status="not_reviewed",
        source_applicability=metadata.source_applicability,
        extraction_provenance=ExtractionProvenance(
            actual, metadata.storage_path, EXTRACTOR_ID, EXTRACTOR_VERSION, "source_specific_parser",
        ),
        unknown_fields={"publication_revision": spec["form"], "publisher": "FCA US LLC",
                        "generation_code_status": "not_present_in_text_layer",
                        "two_door_grade_applicability": "unresolved_pending_visual_or_explicit_matrix_review"},
    )
    result = SourceAssertionSet(Envelope("rigarchive.source_assertion_set.v1", "1.1.0"), provenance, assertions)
    validate_source_assertion_set(result)
    return result


JK_UNLIMITED_SPORT_HASH = "sha256:800f8ecd964e4df584cf6c382216f8401c5b273b85befa686faf93f92841a158"
JK_UNLIMITED_SPORT_REVISION = "74-383-3802 (9/17 143M)"


def _extract_reviewed_jk_row(raw, metadata, *, record_id, extractor_id, prefix, rows):
    """Bind a reviewed transcription to the retained 2018 US JK publication."""
    spec = PUBLICATIONS["jk"]
    actual = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual != JK_UNLIMITED_SPORT_HASH or actual != metadata.content_hash:
        raise AcquisitionError("Unsupported JK publication bytes/revision; review required.")
    applicability = metadata.source_applicability
    if (metadata.source_id != "jeep_usa" or metadata.publisher_locator != spec["url"]
            or metadata.content_type != "application/pdf" or not metadata.storage_path
            or applicability is None or applicability.market != "US"
            or applicability.applicability_basis != "official_jeep_en_us_publication"
            or applicability.publisher_jurisdiction != "FCA US LLC"
            or applicability.applicability_scope != "model_year"
            or metadata.unknown_fields.get("publication_revision", JK_UNLIMITED_SPORT_REVISION)
            != JK_UNLIMITED_SPORT_REVISION):
        raise AcquisitionError("Unexpected JK publication provenance.")

    provenance = SourceMetadata(
        source_id=metadata.source_id, source_type="manufacturer_specification",
        source_locator=metadata.publisher_locator, retrieved_at=metadata.acquired_at,
        native_record_id=record_id,
        acquisition_method=metadata.acquisition_method,
        source_applicability=applicability,
        extraction_provenance=ExtractionProvenance(
            actual, metadata.storage_path, extractor_id,
            "1.0.0", "manually_verified_transcription",
        ),
        unknown_fields={"publication_revision": JK_UNLIMITED_SPORT_REVISION,
                        "publisher": "FCA US LLC"},
    )
    result = SourceAssertionSet(
        Envelope("rigarchive.source_assertion_set.v1", "1.1.0"),
        provenance,
        [SourceAssertion(f"{prefix}_{key}", key, value, context)
         for key, value, context in rows],
    )
    validate_source_assertion_set(result)
    return result


def extract_jk_unlimited_sport(raw, metadata):
    """Extract one configuration from the reviewed US JK brochure revision."""
    # Transcription reviewed against this exact snapshot. The base SPORT
    # column establishes the shared mechanics and explicitly scopes Unlimited.
    rows = (
        ("make_name", "Jeep", "PDF page 1 cover branding; page 13 FCA US LLC colophon"),
        ("model_name", "Wrangler", "PDF page 10 SPORT available column; air conditioning row"),
        ("model_year", "2018", "PDF page 1 cover"),
        ("generation_designation", "JK", "PDF page 1 cover artwork; visually reviewed W1 source identity"),
        ("market", "US", "Official Jeep en_us publication locator; PDF page 13 FCA US LLC colophon"),
        ("manufacturer_grade", "SPORT", "PDF page 10 SPORT heading; base grade, separate from Sport “S” qualifiers"),
        ("body_designation", "Wrangler Unlimited", "PDF page 10 SPORT available column; air conditioning standard on Wrangler Unlimited; Max Tow Package qualified 4-door only"),
        ("engine_descriptor", "3.6L Pentastar® V6", "PDF page 10 SPORT standard column; first powertrain row"),
        ("drive_descriptor", "Command-Trac® 4x4 system", "PDF page 10 SPORT standard column; Command-Trac row"),
    )
    return _extract_reviewed_jk_row(
        raw, metadata, record_id="pdf-page-10-sport-unlimited",
        extractor_id="jeep_2018_jk_unlimited_sport_pdf", prefix="sport_unlimited", rows=rows,
    )


JK_REMAINING_GRADES_EXTRACTOR = "jeep_2018_jk_sahara_rubicon_pdf"

# Four reviewed grade/body relationships, each tied to its own standard
# equipment column and body qualification on PDF page 9.
_JK_REMAINING_ROWS = {
    "sahara": (
        "SAHARA®", "Wrangler", "SAHARA", "Command-Trac® 4x4 system",
        "PDF page 9 SAHARA heading and STANDARD column",
        "PDF page 9 SAHARA STANDARD removable rear seat (2-door only)",
    ),
    "unlimited-sahara": (
        "Sahara Unlimited", "Wrangler Unlimited", "SAHARA", "Command-Trac® 4x4 system",
        "PDF page 6 Sahara Unlimited caption; page 7 Sahara® Unlimited caption; page 9 SAHARA heading",
        "PDF page 9 SAHARA Max Tow Package (4-door only); pages 6–7 Sahara Unlimited captions",
    ),
    "rubicon": (
        "RUBICON®", "Wrangler", "RUBICON", "Rock-Trac® 4x4 system",
        "PDF page 9 RUBICON heading and STANDARD column",
        "PDF page 9 RUBICON STANDARD removable rear bench seat (2-door only); page 11 two-door Rubicon exterior dimensions",
    ),
    "unlimited-rubicon": (
        "Rubicon® Unlimited", "Wrangler Unlimited", "RUBICON", "Rock-Trac® 4x4 system",
        "PDF page 3 Rubicon® Unlimited caption; page 9 RUBICON heading; page 11 Unlimited Rubicon ramp travel row",
        "PDF page 9 RUBICON STANDARD Power Convenience Group (4-door models only); page 11 four-door Rubicon exterior dimensions",
    ),
}


def extract_jk_remaining_grade(raw, metadata, configuration):
    """Extract one of four reviewed Sahara/Rubicon baseline configurations."""
    if configuration not in _JK_REMAINING_ROWS:
        raise AcquisitionError("Unsupported reviewed JK Sahara/Rubicon configuration.")
    grade, body, column, drive, grade_context, body_context = _JK_REMAINING_ROWS[configuration]
    rows = (
        ("make_name", "Jeep", "PDF page 1 cover branding; page 13 FCA US LLC colophon"),
        ("model_name", "Wrangler", "PDF page 1 cover and page 9 grade equipment sections"),
        ("model_year", "2018", "PDF page 1 cover"),
        ("generation_designation", "JK", "PDF page 1 cover artwork; visually reviewed W1 source identity"),
        ("market", "US", "Official Jeep en_us publication locator; PDF page 13 FCA US LLC colophon"),
        ("manufacturer_grade", grade, grade_context),
        ("body_designation", body, body_context),
        ("engine_descriptor", "3.6L Pentastar® V6", f"PDF page 9 {column} STANDARD column; first powertrain row"),
        ("drive_descriptor", drive, f"PDF page 9 {column} STANDARD column; 4x4 system row; page 11 transfer case specifications"),
    )
    return _extract_reviewed_jk_row(
        raw, metadata, record_id=f"pdf-page-9-{configuration}",
        extractor_id=JK_REMAINING_GRADES_EXTRACTOR, prefix=configuration.replace("-", "_"), rows=rows,
    )
