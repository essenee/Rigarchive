"""Execute one explicitly selected year after operator confirmation."""
from reference.ingestion.attribution import add_attribution_arguments, cli_attribution
from reference.ingestion.importing.matrix_workflow import MatrixYear, execute_matrix_year
from ._matrix import confirm
from .reconcile_generation_trim_matrix import Command as ReconcileCommand


class Command(ReconcileCommand):
    help = "Execute one approved matrix year and retain its reconciliation artifacts."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        add_attribution_arguments(parser)
        parser.add_argument("--output-dir", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def run_year(self, matrix, approval, year, candidates, options):
        if options["dry_run"]:
            super().run_year(matrix, approval, year, candidates, options)
            return
        batch = MatrixYear(matrix, approval, year, candidates)
        self.stdout.write(f"Approved matrix {batch.digest}, model year {year}, {len(batch.rows)} rows.")
        attribution = cli_attribution(options)
        self.stdout.write(attribution.describe_cli())
        if not confirm("Execute this approved matrix year? [y/N]: "):
            self.stdout.write("Execution declined.")
            return
        attempt, report = execute_matrix_year(
            matrix, approval, year, candidates, options["output_dir"],
            execution_operator=attribution.director, execution_agent=attribution.agent,
        )
        self.stdout.write(f"Year complete: {attempt / 'result.json'} ({report['authorized_count']} rows)")
