"""Read-only registry reconciliation inventory; deliberately no execute option."""
import json
from django.core.management.base import BaseCommand
from reference.engine_reconciliation import preview_engine_assignments


class Command(BaseCommand):
    help = 'Print a complete read-only Engine assignment preview; never assigns records.'

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(preview_engine_assignments(),indent=2,sort_keys=True,default=str))
