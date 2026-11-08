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
from reference.ingestion.attribution import cli_attribution
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
            required=False,
            help="Path to input CanonicalImportReviewManifest JSON file.",
        )
        parser.add_argument(
            "--candidate-ref",
            type=str,
            required=False,
            help="Candidate reference identifier being adjudicated (e.g. cand_ref_...).",
        )
        parser.add_argument(
            "--category",
            type=str,
            required=False,
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
            required=False,
            help="Verified canonical trim name (e.g. 'SR5 Premium').",
        )
        parser.add_argument("--operator", help="Declared human director role override.")
        parser.add_argument(
            "--notes",
            type=str,
            required=False,
            help="Operator justification and evidence notes.",
        )
        parser.add_argument(
            "--output",
            type=str,
            required=True,
            help="Output JSON file path to save CanonicalImportAdjudication artifact.",
        )
        parser.add_argument("--classification-review", help="Retained proposed classification adjudication 1.1.")
        parser.add_argument("--candidate-output", help="New candidate revision path after explicit classification approval.")

    def handle(self, *args, **options):
        if options.get("classification_review"):
            return self._classification_review(options)
        if not all(options.get(k) for k in ("manifest", "candidate_ref", "category", "trim_name", "notes")):
            raise CommandError("Grade adjudication requires --manifest, --candidate-ref, --category, --trim-name and --notes.")
        manifest_path = Path(options["manifest"]).resolve()
        cand_ref = options["candidate_ref"]
        category = options["category"]
        decision = options["decision"]
        trim_name = options["trim_name"]
        operator = cli_attribution(options).director
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

    def _classification_review(self, options):
        """Affirm a human finding only; no import or database authorization."""
        from django.conf import settings
        from reference.ingestion.classification_adjudication import (
            retained_path, validate_classification_adjudication, apply_classification_adjudication,
        )
        from reference.ingestion.serialization import adjudication_from_dict, serialize_artifact
        try:
            if not options.get("operator") or not options["operator"].strip():
                raise ValueError("Classification approval requires an explicit human --operator.")
            reviewer = cli_attribution(options).director
            if not options.get("candidate_output"):
                raise ValueError("Classification approval requires --candidate-output for a separate revision.")
            root = Path(settings.BASE_DIR).resolve()
            proposal = adjudication_from_dict(json.loads(retained_path(options["classification_review"]).read_text()))
            validate_classification_adjudication(proposal)
            if proposal.adjudication_decision != "proposed_classifications":
                raise ValueError("Expected an unapproved classification proposal.")
            output = Path(options["output"]).resolve()
            candidate_output = Path(options["candidate_output"]).resolve()
            if output == candidate_output or any(not p.is_relative_to(root) or p.exists() for p in (output, candidate_output)):
                raise ValueError("Outputs must be distinct new paths within the repository.")
            self.stdout.write(json.dumps(adjudication_to_dict(proposal), indent=2))
            self.stdout.write("Declared human reviewer: " + reviewer)
            self.stdout.write("Human classification finding only. This does not authorize imports or correspondence publication.")
            try:
                confirmed = input("Type APPROVE CLASSIFICATIONS to approve these exact conclusions: ")
            except EOFError:
                confirmed = ""
            if confirmed != "APPROVE CLASSIFICATIONS":
                self.stdout.write("Declined; no artifacts or database records written.")
                return
            proposal.adjudication_decision = "approved_classifications"
            proposal.operator_label = reviewer
            proposal.created_at = datetime.now(timezone.utc).isoformat()
            proposal.adjudication_hash = compute_adjudication_hash(adjudication_to_dict(proposal))
            validate_classification_adjudication(proposal, require_approved=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x") as stream:
                json.dump(adjudication_to_dict(proposal), stream, indent=2, ensure_ascii=False)
            # The approved artifact remains retained if a subsequent output fails;
            # never roll back a human finding by silently deleting it.
            candidate = apply_classification_adjudication(str(output.relative_to(root)))
            serialized_candidate = serialize_artifact(candidate) + "\n"
            candidate_output.parent.mkdir(parents=True, exist_ok=True)
            with candidate_output.open("x") as stream:
                stream.write(serialized_candidate)
            self.stdout.write("Approved classification artifact and separate candidate revision saved; no database writes.")
        except Exception as exc:
            raise CommandError(f"Classification review failed: {exc}") from exc
