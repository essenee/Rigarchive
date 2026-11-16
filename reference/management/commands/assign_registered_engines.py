"""Execute only the pinned owner-approved reconciliation artifact, locally."""
import json
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from reference.engine_assignment import canonical_state, execute_assignments, validate_assignments


class Command(BaseCommand):
    help = 'Preview or explicitly execute the approved 507 registry associations; local SQLite only.'

    def add_arguments(self, parser):
        parser.add_argument('--execute', action='store_true')
        parser.add_argument('--receipt', type=Path)

    def handle(self, *args, **options):
        path = settings.BASE_DIR / 'docs/research/engine_registry_reconciliation_20261115/assignment_preview.json'
        plan = json.loads(path.read_text())
        try:
            pending, completed = validate_assignments(plan)
            if not options['execute']:
                self.stdout.write(json.dumps(dict(assign=len(pending), skip=len(completed), block=0)))
                return
            db = settings.DATABASES['default']
            if (not settings.DEBUG or db['ENGINE'] != 'django.db.backends.sqlite3'
                    or Path(db['NAME']).resolve() != (settings.BASE_DIR / 'db.sqlite3').resolve()
                    or os.environ.get('RIGARCHIVE_TEST_DB_PATH')):
                raise CommandError('Execution is restricted to the local development db.sqlite3.')
            receipt_path = options['receipt']
            if receipt_path is None:
                raise CommandError('--receipt is required for execution (a new file).')
            # Reserve the receipt before any data write; never overwrite a prior receipt.
            with receipt_path.open('x') as output:
                stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                review = settings.BASE_DIR / 'backups/review/engine_assignments' / stamp
                review.mkdir(parents=True, exist_ok=False)
                baseline = canonical_state()
                (review / 'baseline.json').write_text(json.dumps(baseline, indent=2, sort_keys=True))
                backup = settings.BASE_DIR / 'backups/snapshots' / f'engine_assignments_{stamp}.sqlite3'
                call_command('snapshot_db', output=str(backup), stdout=self.stderr)
                with sqlite3.connect(f'file:{backup}?mode=ro', uri=True) as snapshot:
                    if snapshot.execute('pragma integrity_check').fetchall() != [('ok',)]:
                        raise CommandError('Backup integrity check failed.')
                    if snapshot.execute('pragma foreign_key_check').fetchall():
                        raise CommandError('Backup has foreign-key violations.')
                    with sqlite3.connect(f'file:{db["NAME"]}?mode=ro', uri=True) as live:
                        for table in ('reference_engine', 'reference_vehicledefinition'):
                            query = f'SELECT * FROM {table} ORDER BY id'
                            if snapshot.execute(query).fetchall() != live.execute(query).fetchall():
                                raise CommandError('Canonical rows changed across the backup.')
                # Persist the receipt before outer commit. I/O failure rolls back the batch.
                with transaction.atomic():
                    receipt = execute_assignments(plan, baseline=baseline)
                    with connection.cursor() as cursor:
                        if cursor.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                            raise CommandError('Post-assignment integrity check failed.')
                        if cursor.execute('PRAGMA foreign_key_check').fetchall():
                            raise CommandError('Post-assignment foreign-key check failed.')
                    receipt.update(executed_at=datetime.now(timezone.utc).isoformat(),
                                   authorization='Owner-approved 485 exact + 22 JL ESS aliases',
                                   backup=str(backup), baseline=str(review / 'baseline.json'),
                                   backup_integrity='ok', backup_foreign_keys=[])
                    output.write(json.dumps(receipt, indent=2, sort_keys=True))
                    output.flush()
                    os.fsync(output.fileno())
            self.stdout.write(json.dumps({k: v for k, v in receipt.items() if k != 'changes'}, indent=2))
        except (ValidationError, OSError, ValueError) as exc:
            raise CommandError(str(exc)) from exc
