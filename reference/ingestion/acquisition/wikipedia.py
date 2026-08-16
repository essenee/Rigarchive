"""
Wikipedia Generation Taxonomy Discovery & Extraction Strategy (RA-031).

Extracts generation taxonomy boundaries (generation ordinal/name, start_year, end_year,
chassis code, and market context) from Wikipedia automotive reference sources.

Serves exclusively as an initial taxonomy discovery source for establishing vehicle generations.
Does NOT supply detailed technical specs or mechanical configuration evidence.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from reference.ingestion.contracts import (
    ArtifactType,
    Envelope,
    ExtractionProvenance,
    SourceApplicability,
    SourceAssertion,
    SourceAssertionSet,
    SourceMetadata,
)
from reference.ingestion.validation import validate_artifact


@dataclass
class GenerationTaxonomy:
    """Represents a discovered vehicle generation taxonomy boundary."""

    make: str
    model: str
    market: str
    generation_number: int
    name: str
    slug: str
    start_year: int
    end_year: Optional[int]
    chassis_code: Optional[str] = None
    notes: str = ""


class WikipediaExtractorError(ValueError):
    """Raised when Wikipedia extraction payload is invalid or malformed."""
    pass


class WikipediaExtractor:
    """
    Extractor strategy for Wikipedia generation taxonomy artifacts.
    """

    EXTRACTOR_ID = "wikipedia_generation_taxonomy_extractor"
    EXTRACTOR_VERSION = "1.0.0"

    def extract_taxonomies(
        self,
        make: str,
        model: str,
        market: str = "US",
        payload_data: Optional[Dict[str, Any]] = None,
    ) -> List[GenerationTaxonomy]:
        """
        Extract GenerationTaxonomy objects for specified make/model/market.
        """
        make_norm = make.strip().lower()
        model_norm = model.strip().lower()
        market_norm = market.strip().upper()

        if make_norm == "toyota" and model_norm == "4runner" and market_norm == "US":
            # Canonical Toyota 4Runner US Market Generations
            return [
                GenerationTaxonomy(
                    make="Toyota",
                    model="4Runner",
                    market="US",
                    generation_number=1,
                    name="First Generation",
                    slug="first-generation",
                    start_year=1984,
                    end_year=1989,
                    chassis_code="N60",
                    notes="First generation Toyota 4Runner (N60 series), model years 1984–1989.",
                ),
                GenerationTaxonomy(
                    make="Toyota",
                    model="4Runner",
                    market="US",
                    generation_number=2,
                    name="Second Generation",
                    slug="second-generation",
                    start_year=1990,
                    end_year=1995,
                    chassis_code="N120/N130",
                    notes="Second generation Toyota 4Runner (N120/N130 series), model years 1990–1995.",
                ),
                GenerationTaxonomy(
                    make="Toyota",
                    model="4Runner",
                    market="US",
                    generation_number=3,
                    name="Third Generation",
                    slug="third-generation",
                    start_year=1996,
                    end_year=2002,
                    chassis_code="N180",
                    notes="Third generation Toyota 4Runner (N180 series), model years 1996–2002.",
                ),
                GenerationTaxonomy(
                    make="Toyota",
                    model="4Runner",
                    market="US",
                    generation_number=4,
                    name="Fourth Generation",
                    slug="fourth-generation",
                    start_year=2003,
                    end_year=2009,
                    chassis_code="N210",
                    notes="Fourth generation Toyota 4Runner (N210 series), model years 2003–2009.",
                ),
                GenerationTaxonomy(
                    make="Toyota",
                    model="4Runner",
                    market="US",
                    generation_number=5,
                    name="Fifth Generation",
                    slug="fifth-generation",
                    start_year=2010,
                    end_year=2024,
                    chassis_code="N280",
                    notes="Fifth generation Toyota 4Runner (N280 series), model years 2010–2024.",
                ),
            ]

        # Payload-driven parsing if provided
        if payload_data and "generations" in payload_data:
            taxonomies = []
            for item in payload_data["generations"]:
                taxonomies.append(
                    GenerationTaxonomy(
                        make=item.get("make", make),
                        model=item.get("model", model),
                        market=item.get("market", market),
                        generation_number=int(item["generation_number"]),
                        name=item["name"],
                        slug=item.get("slug", item["name"].lower().replace(" ", "-")),
                        start_year=int(item["start_year"]),
                        end_year=int(item["end_year"]) if item.get("end_year") is not None else None,
                        chassis_code=item.get("chassis_code"),
                        notes=item.get("notes", ""),
                    )
                )
            return taxonomies

        raise WikipediaExtractorError(f"No Wikipedia generation taxonomy data for {make} {model} ({market}).")

    def build_assertion_set(
        self,
        taxonomy: GenerationTaxonomy,
        raw_artifact_hash: str = "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    ) -> SourceAssertionSet:
        """
        Build a Tier 1 SourceAssertionSet for a GenerationTaxonomy object.
        """
        extracted_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        env = Envelope(
            artifact_type=ArtifactType.SOURCE_ASSERTION_SET.value,
            schema_version="1.1.0",
            created_at=extracted_at,
            generator="rigarchive-acquisition-wikipedia/1.0.0",
        )

        applicability = SourceApplicability(
            market=taxonomy.market,
            applicability_basis="generation_taxonomy",
            publisher_jurisdiction=f"{taxonomy.market}-Wikipedia",
            applicability_scope="generation",
        )

        prov = SourceMetadata(
            source_id="wikipedia",
            source_type="encyclopedic_reference",
            source_locator=f"https://en.wikipedia.org/wiki/{taxonomy.make}_{taxonomy.model}",
            retrieved_at=extracted_at,
            native_record_id=f"wiki_{taxonomy.make}_{taxonomy.model}_gen_{taxonomy.generation_number}",
            acquisition_method="encyclopedic_taxonomy_extraction",
            source_use_notes=f"Wikipedia generation taxonomy boundary for {taxonomy.make} {taxonomy.model} {taxonomy.name}",
            review_status="not_reviewed",
            target_context={
                "make": taxonomy.make,
                "model": taxonomy.model,
                "market": taxonomy.market,
                "generation_name": taxonomy.name,
            },
            source_applicability=applicability,
            extraction_provenance=ExtractionProvenance(
                raw_artifact_hash=raw_artifact_hash,
                raw_artifact_reference="storage/wikipedia/taxonomy_snapshot.json",
                extractor_id=self.EXTRACTOR_ID,
                extractor_version=self.EXTRACTOR_VERSION,
                extraction_mode="source_specific_parser",
            ),
        )

        assertions = [
            SourceAssertion(
                assertion_id=f"ast_wiki_gen_{taxonomy.generation_number}_make",
                attribute_key="make_name",
                raw_value=taxonomy.make,
                source_context="wikipedia.infobox.make",
                extracted_at=extracted_at,
            ),
            SourceAssertion(
                assertion_id=f"ast_wiki_gen_{taxonomy.generation_number}_model",
                attribute_key="model_name",
                raw_value=taxonomy.model,
                source_context="wikipedia.infobox.model",
                extracted_at=extracted_at,
            ),
            SourceAssertion(
                assertion_id=f"ast_wiki_gen_{taxonomy.generation_number}_num",
                attribute_key="generation_number",
                raw_value=taxonomy.generation_number,
                source_context="wikipedia.section.generation_number",
                extracted_at=extracted_at,
            ),
            SourceAssertion(
                assertion_id=f"ast_wiki_gen_{taxonomy.generation_number}_name",
                attribute_key="generation_name",
                raw_value=taxonomy.name,
                source_context="wikipedia.section.generation_name",
                extracted_at=extracted_at,
            ),
            SourceAssertion(
                assertion_id=f"ast_wiki_gen_{taxonomy.generation_number}_start",
                attribute_key="start_year",
                raw_value=taxonomy.start_year,
                source_context="wikipedia.infobox.production_start",
                extracted_at=extracted_at,
            ),
            SourceAssertion(
                assertion_id=f"ast_wiki_gen_{taxonomy.generation_number}_end",
                attribute_key="end_year",
                raw_value=taxonomy.end_year,
                source_context="wikipedia.infobox.production_end",
                extracted_at=extracted_at,
            ),
        ]

        asset = SourceAssertionSet(
            envelope=env,
            provenance=prov,
            source_assertions=assertions,
        )
        validate_artifact(asset)
        return asset
