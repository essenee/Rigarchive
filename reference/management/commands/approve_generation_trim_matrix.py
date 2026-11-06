"""Capture affirmative local operator approval for an exact matrix."""
from pathlib import Path

from reference.ingestion.attribution import add_attribution_arguments, cli_attribution
from reference.ingestion.matrix_approval import build_matrix_approval, serialize_matrix_approval
from ._matrix import confirm
from .review_generation_trim_matrix import Command as ReviewCommand


class Command(ReviewCommand):
    help = "Review and explicitly approve an exact Generation Trim Matrix."

    def add_arguments(self, parser):
        super().add_arguments(parser)
        add_attribution_arguments(parser)
        parser.add_argument("--output", required=True)

    def run_matrix(self, matrix, options):
        super().run_matrix(matrix, options)
        attribution = cli_attribution(options)
        self.stdout.write(attribution.describe_cli())
        if not confirm("Approve this exact matrix digest? [y/N]: "):
            self.stdout.write("Approval declined.")
            return
        approval = build_matrix_approval(matrix, operator=attribution.director, confirmed=True)
        with Path(options["output"]).open("xb") as stream:
            stream.write(serialize_matrix_approval(matrix, approval))
        self.stdout.write(f"Approval written to {options['output']}")
