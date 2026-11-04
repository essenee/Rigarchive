"""Publish one exact reviewed correspondence revision, with independent confirmation."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from reference.ingestion.generation_correspondence import (
    digest, require, validate_review_payload, publish_correspondence,
)


class Command(BaseCommand):
    help = "Publish one reviewed correspondence; this does not authorize a vehicle import."

    def add_arguments(self, parser):
        parser.add_argument("--review", required=True)
        parser.add_argument("--operator", default="")

    def handle(self, *args, **options):
        try:
            artifact = json.loads(Path(options["review"]).read_text())
            require(set(artifact) == {"review", "content_hash"}, "Expected exact review and content_hash fields.")
            payload = artifact["review"]
            validate_review_payload(payload)
            require(digest(payload) == artifact["content_hash"], "Review hash mismatch.")
            self.stdout.write(json.dumps(artifact, indent=2, ensure_ascii=False))
            try:
                confirmed = input("Authorize publishing this exact correspondence revision? [y/N]: ")
            except (EOFError, KeyboardInterrupt):
                return
            if confirmed.strip().lower() not in ("y", "yes"):
                return
            revision, receipt = publish_correspondence(
                payload, artifact["content_hash"], authorized=True, operator_label=options["operator"],
            )
            self.stdout.write(f"{receipt.execution_outcome}; receipt {receipt.uuid}")
        except Exception as exc:
            raise CommandError(str(exc)) from exc
