"""Plan one retained candidate offline; never acquire or create canonical parents."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from reference.ingestion.serialization import deserialize_artifact
from reference.ingestion.contracts import CandidateConfigurationDocument
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.manifest import build_review_manifest, manifest_to_dict


class Command(BaseCommand):
    help = "Plan one retained candidate; optional manifest output, zero database writes."

    def add_arguments(self, parser):
        parser.add_argument("--candidate", required=True)
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        try:
            candidate = deserialize_artifact(Path(options["candidate"]).read_text())
            if not isinstance(candidate, CandidateConfigurationDocument):
                raise ValueError("Expected CandidateConfigurationDocument.")
            if candidate.envelope.schema_version != "2.0.0":
                raise ValueError("Offline execution planning requires candidate v2; legacy inspection remains supported.")
            plan = plan_candidate_import(candidate)
            doc = candidate.evidence_documents[0]
            manifest = build_review_manifest(
                doc["source_id"], doc["raw_artifact_hash"], doc["raw_artifact_reference"], doc,
                [plan], {candidate.candidate_reference: candidate.source_configuration_identities[0].native_identifier
                         if candidate.source_configuration_identities else "not_recorded"},
            )
            # Exclusive creation preserves previously reviewed artifacts.
            with Path(options["output"]).open("x") as output:
                json.dump(manifest_to_dict(manifest), output, indent=2, ensure_ascii=False)
            self.stdout.write(f"{plan.planned_action.value}: {plan.reasons}")
        except Exception as exc:
            raise CommandError(str(exc)) from exc
