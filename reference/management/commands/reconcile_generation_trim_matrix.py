"""Report verified matrix-year progress without executing a plan."""
import json

from reference.ingestion.importing.matrix_workflow import MatrixYear
from ._matrix import MatrixYearCommand


class Command(MatrixYearCommand):
    help = "Report current status of one approved matrix year without writes."

    def run_year(self, matrix, approval, year, candidates, options):
        self.stdout.write(json.dumps(MatrixYear(matrix, approval, year, candidates).status(), indent=2))
