"""Validate and display proposed matrix scope without granting approval."""
import json

from django.core.management.base import CommandError

from reference.ingestion.importing.matrix_workflow import MatrixYear
from reference.ingestion.matrix import MATRIX_RESOLUTION_VERSION, compute_matrix_digest
from ._matrix import MatrixCommand, load_candidates


class Command(MatrixCommand):
    help = "Validate and display the exact proposed Generation Trim Matrix."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--candidate", action="append", default=[])

    def run_matrix(self, matrix, options):
        result = {"matrix_digest": compute_matrix_digest(matrix), "matrix": matrix}
        if matrix["matrix_version"] == MATRIX_RESOLUTION_VERSION:
            candidates = load_candidates(options["candidate"])
            result["validation"] = [
                MatrixYear(matrix, None, year, candidates, review_only=True).status()
                for year in matrix["model_years"]
            ]
        self.stdout.write(json.dumps(result, indent=2))
        if any(row["status"] in {"blocked", "conflict"}
               for report in result.get("validation", []) for row in report["rows"]):
            raise CommandError("Matrix contains unresolved rows.")
