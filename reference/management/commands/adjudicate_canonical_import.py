"""
Django Management Command: adjudicate_canonical_import (RA-025 / RA-026).

Operator-invoked CLI command for evaluating flagged candidate import plans,
verifying domain category eligibility, and outputting durable, hashed
CanonicalImportAdjudication JSON artifacts.

GUARANTEE: Human domain finding only. ZERO database writes. ZERO execution authorization.
"""

from datetime import datetime, timezone
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from reference.ingestion.contracts import CanonicalImportAdjudication
from reference.ingestion.manifest import dict_to_manifest
from reference.ingestion.serialization import adjudication_to_dict, compute_adjudication_hash
from reference.ingestion.validation import validate_adjudication


class Command(BaseCommand):
    help = (
        "Evaluates a flagged review plan, verifies domain eligibility, and generates a "
        "durable, content-hashed CanonicalImportAdjudication JSON artifact."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            type=str,
            required=True,
            help="Path to input CanonicalImportReviewManifest JSON file.",
        )
        parser.add_argument(
            "--candidate-ref",
            type=str,
            required=True,
            help="Candidate reference identifier being adjudicated (e.g. cand_ref_...).",
        )
        parser.add_argument(
            "--category",
            type=str,
            required=True,
            choices=["distinct_factory_grade", "special_edition_grade"],
            help="Approved adjudicable category.",
        )
        parser.add_argument(
            "--decision",
            type=str,
            default="approved_distinct_trim",
            help="Adjudication decision string (default: 'approved_distinct_trim').",
        )
        parser.add_argument(
            "--trim-name",
            type=str,
            required=True,
            help="Verified canonical trim name (e.g. 'SR5 Premium').",
        )
        parser.add_argument(
            "--operator",
            type=str,
            default="operator",
            help="Operator identifier for adjudication audit log.",
        )
        parser.add_argument(
            "--notes",
            type=str,
            required=True,
            help="Operator justification and evidence notes.",
        )
        parser.add_argument(
            "--output",
            type=str,
            required=True,
            help="Output JSON file path to save CanonicalImportAdjudication artifact.",
        )

    def handle(self, *args, **options):
        manifest_path = Path(options["manifest"]).resolve()
        cand_ref = options["candidate_ref"]
        category = options["category"]
        decision = options["decision"]
        trim_name = options["trim_name"]
        operator = options["operator"]
        notes = options["notes"]
        output_path = Path(options["output"]).resolve()

        if not manifest_path.exists() or not manifest_path.is_file():
            raise CommandError(f"Review manifest file does not exist: '{manifest_path}'.")

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_dict = json.load(f)
            manifest = dict_to_manifest(manifest_dict)
        except Exception as e:
            raise CommandError(f"Failed to parse and validate review manifest: {str(e)}") from e

        target_plan = None
        for plan in manifest.plans:
            if plan.candidate_reference == cand_ref:
                target_plan = plan
                break

        if not target_plan:
            raise CommandError(f"Candidate reference '{cand_ref}' not found in manifest '{manifest_path}'.")

        if target_plan.planned_action != "flag_review":
            raise CommandError(
                f"Candidate plan '{cand_ref}' has planned_action '{target_plan.planned_action}'. "
                "Adjudication is only permitted for 'flag_review' plans."
            )

        created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        raw_adj_dict = {
            "adjudication_version": "1.0",
            "created_at": created_at,
            "operator_label": operator,
            "original_manifest_hash": manifest.manifest_hash,
            "candidate_reference": cand_ref,
            "source_identity": {
                "source_id": manifest.source_id,
                "source_identity_type": target_plan.source_identity_type,
                "native_identifier": target_plan.native_identifier,
            },
            "original_review_category": target_plan.review_category or "distinct_factory_grade",
            "adjudication_category": category,
            "adjudication_decision": decision,
            "adjudicated_trim_name": trim_name,
            "adjudication_notes": notes,
        }

        adj_hash = compute_adjudication_hash(raw_adj_dict)
        raw_adj_dict["adjudication_hash"] = adj_hash

        adj_obj = CanonicalImportAdjudication(
            adjudication_version=raw_adj_dict["adjudication_version"],
            created_at=raw_adj_dict["created_at"],
            operator_label=raw_adj_dict["operator_label"],
            original_manifest_hash=raw_adj_dict["original_manifest_hash"],
            candidate_reference=raw_adj_dict["candidate_reference"],
            source_identity=raw_adj_dict["source_identity"],
            original_review_category=raw_adj_dict["original_review_category"],
            adjudication_category=raw_adj_dict["adjudication_category"],
            adjudication_decision=raw_adj_dict["adjudication_decision"],
            adjudicated_trim_name=raw_adj_dict["adjudicated_trim_name"],
            adjudication_notes=raw_adj_dict["adjudication_notes"],
            adjudication_hash=adj_hash,
        )

        try:
            validate_adjudication(adj_obj)
        except Exception as e:
            raise CommandError(f"Adjudication artifact contract validation failed: {str(e)}") from e

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(adjudication_to_dict(adj_obj), f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise CommandError(f"Failed to save adjudication artifact to '{output_path}': {str(e)}") from e

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created CanonicalImportAdjudication artifact:\n"
                f"  Candidate Ref:   {cand_ref}\n"
                f"  Category:        {category}\n"
                f"  Adjudicated Trim:{trim_name}\n"
                f"  Adjudication Hash:{adj_hash}\n"
                f"  Saved File:      {output_path}"
            )
        )
