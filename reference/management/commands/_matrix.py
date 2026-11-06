"""Shared CLI input handling for the matrix commands."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from reference.ingestion.matrix import canonical_matrix_payload
from reference.ingestion.matrix_approval import read_matrix_approval
from reference.ingestion.serialization import deserialize_artifact


def confirm(prompt):
    try:
        return input(prompt).strip().lower() in {"y", "yes"}
    except (EOFError, KeyboardInterrupt):
        return False


class MatrixCommand(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--matrix", required=True)

    def handle(self, *args, **options):
        try:
            matrix = canonical_matrix_payload(json.loads(Path(options["matrix"]).read_text(encoding="utf-8")))
            self.run_matrix(matrix, options)
        except (ValueError, OSError) as exc:
            raise CommandError(str(exc)) from exc


class MatrixYearCommand(MatrixCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--approval", required=True)
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument("--candidate", action="append", default=[])

    def run_matrix(self, matrix, options):
        approval = read_matrix_approval(options["approval"], matrix)
        self.run_year(matrix, approval, options["year"], load_candidates(options["candidate"]), options)


def load_candidates(paths):
    candidates = {}
    for path in paths:
        candidate = deserialize_artifact(Path(path).read_text(encoding="utf-8"))
        reference = getattr(candidate, "candidate_reference", None)
        if not reference or reference in candidates:
            raise CommandError("Expected distinct candidate documents.")
        candidates[reference] = candidate
    return candidates
