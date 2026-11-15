"""Preview or explicitly execute the approved local MY2026 family."""
import json

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from reference import my2026_wrangler_import as service


class Command(BaseCommand):
    help = 'Read-only MY2026 preview by default; --execute requires its exact --approved-plan-hash.'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true')
        parser.add_argument('--approved-plan-hash')
        parser.add_argument('--operator', default='project_owner')
        parser.add_argument('--agent', default='codex')

    def handle(self, *args, **options):
        try:
            if options['execute']:
                if not options['approved_plan_hash']:
                    raise CommandError('--execute requires --approved-plan-hash from the reviewed preview.')
                result = service.execute(options['approved_plan_hash'], operator=options['operator'], agent=options['agent'])
            else:
                result = service.preview()
            self.stdout.write(json.dumps(result, indent=2, default=str))
        except (ValidationError, ObjectDoesNotExist, OSError, ValueError, KeyError) as exc:
            raise CommandError(str(exc)) from exc
