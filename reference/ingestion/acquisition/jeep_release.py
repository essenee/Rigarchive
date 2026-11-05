"""Identity-only extraction of the retained 2017 Mopar Wrangler launch release.

The complete HTML remains raw evidence. No accessory catalogue, equipment
offering, engine/transmission association or commercial-market claim is emitted.
"""
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import re

from reference.ingestion.acquisition.base import AcquisitionError
from reference.ingestion.acquisition.snapshots import RawAcquisitionResult
from reference.ingestion.contracts import (
    Envelope, ExtractionProvenance, SourceApplicability, SourceAssertion,
    SourceAssertionSet, SourceMetadata,
)
from reference.ingestion.validation import validate_source_assertion_set


SOURCE_ID = "stellantis_mopar"
SOURCE_URL = "https://www.media.stellantis.com/em-en/stellantis-parts-services/press/mopar-premieres-pair-of-customized-all-new-2018-jeep-wrangler-vehicles-at-la-auto-show"
TITLE = "Mopar Premieres Pair of Customized All-new 2018 Jeep® Wrangler Vehicles at LA Auto Show"


class _PublicationHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonicals = []
        self.metadata = {}
        self.paragraphs = []
        self.current = None
        self.skipped = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.skipped += 1
        if self.skipped:
            return
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))
        if tag == "meta" and attrs.get("property"):
            self.metadata[attrs["property"]] = attrs.get("content")
        if tag == "p":
            self.current = []
        elif tag == "br" and self.current is not None:
            self.current.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skipped = max(0, self.skipped - 1)
        if tag == "p" and self.current is not None:
            self.paragraphs.append(re.sub(r"\s+", " ", "".join(self.current)).strip())
            self.current = None

    def handle_data(self, data):
        if not self.skipped and self.current is not None:
            self.current.append(data)


def _parse(raw):
    if len(raw) > 10 * 1024 * 1024 or b"</html>" not in raw.lower():
        raise AcquisitionError("Expected a bounded complete original HTML publication.")
    parser = _PublicationHTML()
    parser.feed(raw.decode("utf-8"))
    if (not parser.canonicals or set(parser.canonicals) != {SOURCE_URL}
            or parser.metadata.get("og:title") != TITLE):
        raise AcquisitionError("Publication identity does not match the bounded release strategy.")
    matches = [(n, p) for n, p in enumerate(parser.paragraphs, 1)
               if "The FCA US display at the Los Angeles Convention Center includes" in p
               and "a two-door 2018 Jeep Wrangler Sport uniquely customized" in p
               and "all-new 2018 Jeep" in p]
    if len(matches) != 1:
        raise AcquisitionError("A unique, qualified body/grade identity statement is required.")
    if not parser.metadata.get("article:published_time"):
        raise AcquisitionError("Publication date metadata is required.")
    return parser, matches[0]


def acquire_local_release(path):
    raw = Path(path).read_bytes()
    _parse(raw)
    return RawAcquisitionResult(
        SOURCE_ID, SOURCE_URL, datetime.now(timezone.utc).isoformat(),
        "text/html", raw,
        SourceApplicability(market=None, applicability_basis="US_event_vehicle_identity_only",
                            publisher_jurisdiction="FCA US LLC", applicability_scope="configuration"),
        "local_file", original_filename=Path(path).name,
    )


def extract_release_identity(raw, metadata):
    actual = "sha256:" + hashlib.sha256(raw).hexdigest()
    if (metadata.source_id != SOURCE_ID or metadata.publisher_locator != SOURCE_URL
            or metadata.content_hash != actual):
        raise AcquisitionError("Retained release source/hash mismatch.")
    parser, (number, paragraph) = _parse(raw)
    assertions = [
        SourceAssertion("release_generation_section", "generation_section", TITLE,
                        'HTML meta[property="og:title"]; exact manufacturer publication title'),
        SourceAssertion("vehicle_body_grade_identity", "vehicle_body_grade_statement", paragraph,
                        f"HTML p[{number}], unique introductory FCA US display paragraph; full customization qualifier preserved",
                        unknown_fields={"role": "vehicle_identity_only", "door_count": 2,
                                        "accessory_catalogue": "excluded_from_structured_ingestion",
                                        "market_limit": "US event is not independent proof of US commercial availability"}),
        SourceAssertion("release_publication_date", "publication_date",
                        parser.metadata["article:published_time"],
                        'HTML meta[property="article:published_time"]'),
    ]
    provenance = SourceMetadata(
        SOURCE_ID, source_type="manufacturer_press_release", source_locator=SOURCE_URL,
        retrieved_at=metadata.acquired_at, native_record_id="article-intro-fca-us-display",
        acquisition_method="local_file", review_status="pending_review",
        source_applicability=metadata.source_applicability,
        extraction_provenance=ExtractionProvenance(actual, metadata.storage_path,
            "jeep_mopar_release_identity_html", "1.0.0", "source_specific_parser"),
        unknown_fields={"publication_revision": parser.metadata.get("article:modified_time"),
                        "published_time": parser.metadata["article:published_time"],
                        "publisher": "Stellantis Parts & Services / FCA US launch release",
                        "scope": "vehicle identity/applicability only; not stock mechanical evidence",
                        "equipment_policy": "No accessory or optional-equipment catalogue assertions emitted; raw HTML retained intact."},
    )
    result = SourceAssertionSet(Envelope("rigarchive.source_assertion_set.v1", "1.1.0"), provenance, assertions)
    validate_source_assertion_set(result)
    return result
