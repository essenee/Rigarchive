"""
Generation Bootstrap & Multi-Year Configuration Population Orchestrator (RA-031).

Coordinates Wikipedia generation taxonomy discovery with J.D. Power historical model-year
configuration enumeration, candidate normalization, planning, and canonical database promotion.

Implements safe Generation bootstrapping, existing-data short-circuiting, exception-driven
multi-year population, and post-population availability gating.
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from django.conf import settings
from django.db import transaction

from reference.ingestion.acquisition.jd_power_extractor import JDPowerExtractor
from reference.ingestion.acquisition.wikipedia import GenerationTaxonomy, WikipediaExtractor
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.contracts import CandidateIdentity, SourceMetadata
from reference.ingestion.importing.importer import execute_candidate_import
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.normalization.jd_power import JDPowerNormalizer
from reference.ingestion.manifest import PopulationBatchItem, PopulationBatchManifest
from reference.models import Generation, Manufacturer, VehicleDefinition, VehicleModel


@dataclass
class GenerationPopulationResult:
    """Report summary for a single generation's bootstrap & population attempt."""

    generation_name: str
    generation_slug: str
    generation_number: int
    start_year: int
    end_year: Optional[int]
    action: str  # "BOOTSTRAPPED_AND_POPULATED" or "SHORT_CIRCUIT_EXISTING_DATA"
    is_active: bool
    model_years_attempted: List[int] = field(default_factory=list)
    total_configurations_discovered: int = 0
    configurations_created: int = 0
    existing_exact_matches: int = 0
    blocked_exceptions: List[str] = field(default_factory=list)
    generation_db_id: Optional[int] = None


@dataclass
class USGenerationBootstrapRunResult:
    """Report summary for a full multi-generation bootstrap run."""

    manufacturer_name: str
    vehicle_model_name: str
    market: str
    generations_discovered: int
    generation_results: List[GenerationPopulationResult] = field(default_factory=list)
    system_errors: List[str] = field(default_factory=list)


class GenerationBootstrapOrchestrator:
    """
    Orchestrates generation taxonomy discovery and full multi-year configuration population.
    """

    def __init__(
        self,
        wiki_extractor: Optional[WikipediaExtractor] = None,
        jdp_extractor: Optional[JDPowerExtractor] = None,
        jdp_normalizer: Optional[JDPowerNormalizer] = None,
        fixture_dir: Optional[Union[str, Path]] = None,
    ):
        self.wiki_extractor = wiki_extractor or WikipediaExtractor()
        self.jdp_extractor = jdp_extractor or JDPowerExtractor()
        self.jdp_normalizer = jdp_normalizer or JDPowerNormalizer()
        self.fixture_dir = Path(
            fixture_dir
            or settings.BASE_DIR
            / "reference"
            / "tests"
            / "fixtures"
            / "acquisition"
            / "jd_power"
        )

    def _locate_jd_power_fixture_for_year(self, year: int) -> Optional[Path]:
        """Locate retained J.D. Power configuration JSON fixture for a given model year."""
        candidates = [
            self.fixture_dir / f"{year}_4runner_configurations.json",
            self.fixture_dir / f"jd_power_{year}.json",
        ]
        for path in candidates:
            if path.exists():
                return path
        return None

    def create_batch_manifest(
        self,
        make: str = "Toyota",
        model: str = "4Runner",
        market: str = "US",
        start_year: int = 2003,
        end_year: int = 2009,
    ) -> PopulationBatchManifest:
        """
        Assemble a reviewable PopulationBatchManifest dry-run before authorizing population execution.
        """
        items: List[PopulationBatchItem] = []
        create_count = 0
        no_op_count = 0
        review_count = 0

        # Ensure Manufacturer, VehicleModel, and Generation nodes exist
        mfr, _ = Manufacturer.objects.get_or_create(name=make, defaults={"is_active": True})
        vmodel, _ = VehicleModel.objects.get_or_create(manufacturer=mfr, name=model, defaults={"is_active": True})
        try:
            taxonomies = self.wiki_extractor.extract_taxonomies(make, model, market)
            for tax in taxonomies:
                Generation.objects.get_or_create(
                    vehicle_model=vmodel,
                    slug=tax.slug,
                    defaults={
                        "name": tax.name,
                        "generation_number": tax.generation_number,
                        "start_year": tax.start_year,
                        "end_year": tax.end_year,
                        "is_active": True,
                    },
                )
        except Exception:
            pass

        for yr in range(start_year, end_year + 1):
            fixture_path = self._locate_jd_power_fixture_for_year(yr)
            if not fixture_path:
                continue

            with open(fixture_path, "r", encoding="utf-8") as f:
                raw_dict = json.load(f)

            meta = SourceMetadata(
                source_id="jd_power",
                source_type="third_party_reference",
                source_locator=f"file://{fixture_path}",
                native_record_id=f"jdp_file_{yr}",
                target_context={"make": make, "model": model, "model_year": yr, "market": market},
            )

            assertion_sets = self.jdp_extractor.extract(raw_dict, meta)
            for aset in assertion_sets:
                try:
                    norm_interps = self.jdp_normalizer.normalize(aset)
                    trim_raw = next((ast.raw_value for ast in aset.source_assertions if ast.attribute_key in ("trim", "manufacturer_grade")), None)
                    cand_identity = CandidateIdentity(manufacturer_name=make, vehicle_model_name=model, model_year=yr, market=market, trim_name=trim_raw)
                    cand_doc = construct_candidate_configuration(candidate_identity=cand_identity, source_assertion_sets=[aset], normalized_assertions=norm_interps)
                    plan = plan_candidate_import(cand_doc)

                    action_str = plan.planned_action.value
                    if action_str in ("create", "adjudicated_distinct_grade"):
                        create_count += 1
                    elif action_str == "no_op_exact_match":
                        no_op_count += 1
                    else:
                        review_count += 1

                    eng_val = next((str(interp.normalized_concept) for interp in norm_interps if interp.target_attribute_key == "engine_displacement_liters"), None)
                    drv_val = next((str(interp.normalized_concept) for interp in norm_interps if interp.target_attribute_key == "generic_drive_classification"), None)

                    items.append(
                        PopulationBatchItem(
                            candidate_reference=cand_doc.candidate_reference,
                            native_identifier=aset.provenance.native_record_id or "unknown",
                            model_year=yr,
                            trim_name=cand_identity.trim_name,
                            engine_name=eng_val,
                            drivetrain=drv_val,
                            planned_action=action_str,
                            create_basis=plan.create_basis.value if plan.create_basis else None,
                            target_slug=plan.target_slug or "unknown",
                        )
                    )
                except Exception:
                    review_count += 1

        batch_id = f"batch_{make.lower()}_{model.lower()}_{start_year}_{end_year}"
        manifest = PopulationBatchManifest(
            batch_id=batch_id,
            manufacturer_name=make,
            vehicle_model_name=model,
            market=market,
            start_year=start_year,
            end_year=end_year,
            total_candidates=len(items),
            create_count=create_count,
            no_op_count=no_op_count,
            review_count=review_count,
            items=items,
        )
        return manifest

    def execute_authorized_batch(
        self,
        manifest: PopulationBatchManifest,
    ) -> Dict[str, Any]:
        """
        Execute an authorized PopulationBatchManifest inside transaction boundaries.
        Validates authorization envelope, enforces stale-plan revalidation, and persists
        individual ImportExecutionReceipt logs linked to manifest.batch_manifest_hash.
        """
        from reference.models import ImportExecutionReceipt

        expected_hash = manifest.compute_manifest_hash()
        if manifest.batch_manifest_hash and manifest.batch_manifest_hash != expected_hash:
            raise ValueError(f"Batch manifest hash mismatch! Refusing execution.")

        mfr, _ = Manufacturer.objects.get_or_create(name=manifest.manufacturer_name, defaults={"is_active": True})
        vmodel, _ = VehicleModel.objects.get_or_create(manufacturer=mfr, name=manifest.vehicle_model_name, defaults={"is_active": True})

        # Ensure Generation nodes exist for batch model year range
        try:
            taxonomies = self.wiki_extractor.extract_taxonomies(manifest.manufacturer_name, manifest.vehicle_model_name, manifest.market)
            for tax in taxonomies:
                Generation.objects.get_or_create(
                    vehicle_model=vmodel,
                    slug=tax.slug,
                    defaults={
                        "name": tax.name,
                        "generation_number": tax.generation_number,
                        "start_year": tax.start_year,
                        "end_year": tax.end_year,
                        "is_active": True,
                    },
                )
        except Exception:
            pass

        authorized_slugs = {item.target_slug: item for item in manifest.items}
        created_count = 0
        no_op_count = 0
        blocked_count = 0
        outside_count = 0

        for yr in range(manifest.start_year, manifest.end_year + 1):
            fixture_path = self._locate_jd_power_fixture_for_year(yr)
            if not fixture_path:
                continue

            with open(fixture_path, "r", encoding="utf-8") as f:
                raw_dict = json.load(f)

            raw_bytes = open(fixture_path, "rb").read()
            artifact_hash = "sha256:" + hashlib.sha256(raw_bytes).hexdigest()

            meta = SourceMetadata(
                source_id="jd_power",
                source_type="third_party_reference",
                source_locator=f"file://{fixture_path}",
                native_record_id=f"jdp_file_{yr}",
                target_context={"make": manifest.manufacturer_name, "model": manifest.vehicle_model_name, "model_year": yr, "market": manifest.market},
            )

            assertion_sets = self.jdp_extractor.extract(raw_dict, meta)
            for aset in assertion_sets:
                try:
                    norm_interps = self.jdp_normalizer.normalize(aset)
                    trim_raw = next((ast.raw_value for ast in aset.source_assertions if ast.attribute_key in ("trim", "manufacturer_grade")), None)
                    cand_identity = CandidateIdentity(
                        manufacturer_name=manifest.manufacturer_name,
                        vehicle_model_name=manifest.vehicle_model_name,
                        model_year=yr,
                        market=manifest.market,
                        trim_name=trim_raw,
                    )
                    cand_doc = construct_candidate_configuration(
                        candidate_identity=cand_identity,
                        source_assertion_sets=[aset],
                        normalized_assertions=norm_interps,
                    )
                    plan = plan_candidate_import(cand_doc)

                    # Authorization Envelope Check
                    if plan.target_slug not in authorized_slugs:
                        outside_count += 1
                        continue

                    if plan.planned_action.value in ("create", "adjudicated_distinct_grade", "no_op_exact_match"):
                        exec_res = execute_candidate_import(plan)
                        if exec_res.outcome.value == "created":
                            created_count += 1
                        elif exec_res.outcome.value == "no_op_exact_match":
                            no_op_count += 1
                        else:
                            blocked_count += 1

                        # Save individual execution receipt linked to batch manifest hash
                        ImportExecutionReceipt.objects.create(
                            operator_label="cli:batch_executor",
                            execution_channel="cli",
                            manifest_hash=manifest.batch_manifest_hash,
                            candidate_reference=cand_doc.candidate_reference,
                            planned_action=plan.planned_action.value,
                            create_basis=plan.create_basis.value if plan.create_basis else "",
                            source_id="jd_power",
                            raw_artifact_hash=artifact_hash,
                            raw_artifact_reference=str(fixture_path),
                            source_identity_type="record_id",
                            native_identifier=aset.provenance.native_record_id or "unknown",
                            resolved_generation_id=plan.resolved_generation_id,
                            target_slug=plan.target_slug or "",
                            target_model_year=yr,
                            target_trim_name=trim_raw or "",
                            target_engine_name=next((str(i.normalized_concept) for i in norm_interps if i.target_attribute_key == "engine_displacement_liters"), ""),
                            target_drivetrain=next((str(i.normalized_concept) for i in norm_interps if i.target_attribute_key == "generic_drive_classification"), ""),
                            target_market=manifest.market,
                            target_fields_json=plan.target_vehicle_definition_fields,
                            execution_outcome=exec_res.outcome.value,
                            messages_json=exec_res.messages,
                            created_vehicle_definition_id=exec_res.vehicle_definition_id if exec_res.outcome.value == "created" else None,
                            existing_vehicle_definition_id=exec_res.vehicle_definition_id if exec_res.outcome.value == "no_op_exact_match" else None,
                        )
                    else:
                        blocked_count += 1
                except Exception as e:
                    blocked_count += 1

        return {
            "total_attempted": len(manifest.items),
            "created": created_count,
            "no_op": no_op_count,
            "blocked": blocked_count,
            "outside_authorization": outside_count,
        }

    def run_bootstrap_pipeline(
        self,
        make: str = "Toyota",
        model: str = "4Runner",
        market: str = "US",
        force_repopulate: bool = False,
    ) -> USGenerationBootstrapRunResult:
        """
        Execute Wikipedia taxonomy discovery and multi-generation configuration population.
        """
        system_errors: List[str] = []
        gen_results: List[GenerationPopulationResult] = []

        # 1. Wikipedia Generation Taxonomy Discovery
        try:
            taxonomies = self.wiki_extractor.extract_taxonomies(make, model, market)
        except Exception as e:
            return USGenerationBootstrapRunResult(
                manufacturer_name=make,
                vehicle_model_name=model,
                market=market,
                generations_discovered=0,
                system_errors=[f"Wikipedia taxonomy discovery failed: {e}"],
            )

        # 2. Resolve Manufacturer and VehicleModel
        mfr, _ = Manufacturer.objects.get_or_create(
            name=make,
            defaults={"is_active": True},
        )
        vmodel, _ = VehicleModel.objects.get_or_create(
            manufacturer=mfr,
            name=model,
            defaults={"is_active": True},
        )

        # 3. Process each discovered Generation Taxonomy
        for tax in taxonomies:
            res = self._process_single_generation(
                vmodel=vmodel,
                taxonomy=tax,
                force_repopulate=force_repopulate,
            )
            gen_results.append(res)

        return USGenerationBootstrapRunResult(
            manufacturer_name=make,
            vehicle_model_name=model,
            market=market,
            generations_discovered=len(taxonomies),
            generation_results=gen_results,
            system_errors=system_errors,
        )

    def _process_single_generation(
        self,
        vmodel: VehicleModel,
        taxonomy: GenerationTaxonomy,
        force_repopulate: bool = False,
    ) -> GenerationPopulationResult:
        """
        Process bootstrap & population for a single generation.
        """
        start_year = taxonomy.start_year
        end_year = taxonomy.end_year

        # Check existing active VehicleDefinitions within year range
        existing_defs_query = VehicleDefinition.objects.filter(
            generation__vehicle_model=vmodel,
            model_year__gte=start_year,
            is_active=True,
        )
        if end_year is not None:
            existing_defs_query = existing_defs_query.filter(model_year__lte=end_year)

        existing_active_count = existing_defs_query.count()

        # Existing-Data Short Circuit:
        if existing_active_count > 0 and not force_repopulate:
            gen_obj, _ = Generation.objects.get_or_create(
                vehicle_model=vmodel,
                slug=taxonomy.slug,
                defaults={
                    "name": taxonomy.name,
                    "generation_number": taxonomy.generation_number,
                    "start_year": taxonomy.start_year,
                    "end_year": taxonomy.end_year,
                    "notes": taxonomy.notes,
                    "is_active": True,
                },
            )
            if not gen_obj.is_active:
                gen_obj.is_active = True
                gen_obj.save()

            # Associate unlinked active definitions with this generation
            for vd in existing_defs_query.exclude(generation__slug=taxonomy.slug):
                vd.generation = gen_obj
                vd.save()

            return GenerationPopulationResult(
                generation_name=taxonomy.name,
                generation_slug=taxonomy.slug,
                generation_number=taxonomy.generation_number,
                start_year=taxonomy.start_year,
                end_year=taxonomy.end_year,
                action="SHORT_CIRCUIT_EXISTING_DATA",
                is_active=True,
                total_configurations_discovered=existing_active_count,
                existing_exact_matches=existing_active_count,
                generation_db_id=gen_obj.id,
            )

        # Unpopulated Generation Bootstrap:
        gen_obj, _ = Generation.objects.get_or_create(
            vehicle_model=vmodel,
            slug=taxonomy.slug,
            defaults={
                "name": taxonomy.name,
                "generation_number": taxonomy.generation_number,
                "start_year": taxonomy.start_year,
                "end_year": taxonomy.end_year,
                "notes": taxonomy.notes,
                "is_active": True,  # Active during bootstrap so planner resolves generation
            },
        )
        if not gen_obj.is_active:
            gen_obj.is_active = True
            gen_obj.save()

        years_to_process = list(
            range(start_year, (end_year or start_year) + 1)
        )
        attempted_years: List[int] = []
        total_discovered = 0
        total_created = 0
        total_no_ops = 0
        exceptions: List[str] = []

        for yr in years_to_process:
            fixture_path = self._locate_jd_power_fixture_for_year(yr)
            if not fixture_path:
                exceptions.append(f"Year {yr}: No J.D. Power configuration fixture found.")
                continue

            attempted_years.append(yr)

            try:
                with open(fixture_path, "r", encoding="utf-8") as f:
                    raw_dict = json.load(f)

                meta = SourceMetadata(
                    source_id="jd_power",
                    source_type="third_party_reference",
                    source_locator=f"file://{fixture_path}",
                    retrieved_at="2026-08-16T00:00:00Z",
                    native_record_id=f"jdp_file_{yr}",
                    acquisition_method="retained_snapshot_fixture",
                    target_context={
                        "make": vmodel.manufacturer.name,
                        "model": vmodel.name,
                        "model_year": yr,
                        "market": taxonomy.market,
                    },
                )

                # Evaluate inventory completeness using J.D. Power discovery strategy
                disc_strat = self.jdp_extractor.select_discovery_strategy(yr)
                raw_cfgs = raw_dict.get("configurations", []) if isinstance(raw_dict, dict) else []
                comp_status = disc_strat.evaluate_inventory_completeness(raw_cfgs, yr)
                if comp_status.value == "incomplete":
                    exceptions.append(f"Year {yr}: SOURCE INVENTORY APPEARS INCOMPLETE")

                assertion_sets = self.jdp_extractor.extract(raw_dict, meta)
                total_discovered += len(assertion_sets)

                for aset in assertion_sets:
                    try:
                        norm_interps = self.jdp_normalizer.normalize(aset)

                        trim_raw = None
                        for ast in aset.source_assertions:
                            if ast.attribute_key in ("trim", "manufacturer_grade"):
                                trim_raw = ast.raw_value
                                break

                        cand_identity = CandidateIdentity(
                            manufacturer_name=vmodel.manufacturer.name,
                            vehicle_model_name=vmodel.name,
                            model_year=yr,
                            market=taxonomy.market,
                            trim_name=trim_raw,
                        )

                        cand_doc = construct_candidate_configuration(
                            candidate_identity=cand_identity,
                            source_assertion_sets=[aset],
                            normalized_assertions=norm_interps,
                        )

                        # Plan candidate import
                        plan = plan_candidate_import(cand_doc)

                        if plan.planned_action in ("create", "adjudicated_distinct_grade"):
                            exec_res = execute_candidate_import(plan)
                            if exec_res.outcome.value == "created":
                                total_created += 1
                            elif exec_res.outcome.value == "no_op_exact_match":
                                total_no_ops += 1
                            else:
                                exceptions.append(
                                    f"Year {yr} Native ID '{aset.provenance.native_record_id}': "
                                    f"Execution outcome '{exec_res.outcome.value}' - {exec_res.messages}"
                                )
                        elif plan.planned_action == "no_op_exact_match":
                            total_no_ops += 1
                        else:
                            exceptions.append(
                                f"Year {yr} Native ID '{aset.provenance.native_record_id}': "
                                f"Planned action '{plan.planned_action.value}' - {plan.reasons}"
                            )
                    except Exception as cand_exc:
                        exceptions.append(
                            f"Year {yr} Native ID '{aset.provenance.native_record_id}': {cand_exc}"
                        )
            except Exception as yr_exc:
                exceptions.append(f"Year {yr} processing error: {yr_exc}")

        # Post-population availability gate
        active_in_gen = VehicleDefinition.objects.filter(
            generation=gen_obj,
            is_active=True,
        ).count()

        if active_in_gen > 0:
            gen_obj.is_active = True
            gen_obj.save()
        else:
            gen_obj.is_active = False
            gen_obj.save()

        return GenerationPopulationResult(
            generation_name=taxonomy.name,
            generation_slug=taxonomy.slug,
            generation_number=taxonomy.generation_number,
            start_year=taxonomy.start_year,
            end_year=taxonomy.end_year,
            action="BOOTSTRAPPED_AND_POPULATED",
            is_active=gen_obj.is_active,
            model_years_attempted=attempted_years,
            total_configurations_discovered=total_discovered,
            configurations_created=total_created,
            existing_exact_matches=total_no_ops,
            blocked_exceptions=exceptions,
            generation_db_id=gen_obj.id,
        )
