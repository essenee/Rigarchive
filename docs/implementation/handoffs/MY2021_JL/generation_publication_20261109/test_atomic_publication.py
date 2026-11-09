"""Synthetic isolated regressions for the task-local outer transaction driver."""
import json
import sqlite3

from django.core.management import CommandError
from django.db import transaction
from django.test import TestCase

from reference.ingestion.generation_correspondence import digest
from reference.models import GenerationCorrespondenceRevision as Revision, ImportExecutionReceipt
from reference.tests.test_generation_correspondence import SyntheticWranglerSetup
from .publish_atomic import publish_with_cli, snapshot


class AtomicPublicationTests(SyntheticWranglerSetup, TestCase):
    def test_snapshot_matches_plain_and_declared_type_converting_connections(self):
        path = self.root / 'typed-snapshot.sqlite3'
        plain = sqlite3.connect(path)
        plain.execute('CREATE TABLE sample (id INTEGER PRIMARY KEY AUTOINCREMENT, active bool, day date, note TEXT)')
        plain.execute('INSERT INTO sample (active,day,note) VALUES (1,?,?)',
                      ('2026-11-09', 'synthetic'))
        plain.commit()
        typed = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.assertIs(type(typed.execute('SELECT active FROM sample').fetchone()[0]), bool)
        self.assertEqual(snapshot(plain), snapshot(typed))
        typed.close()
        plain.close()

    def entries(self):
        candidates = [self.candidate, self.make_candidate('JL')]
        entries = []
        for n, candidate in enumerate(candidates):
            p = self.review(candidate, generation=self.jk if n == 0 else self.jl)
            path = self.root / f'review-{n}.json'
            path.write_text(json.dumps({'review': p, 'content_hash': digest(p)}))
            entries.append({'proposal': str(path), 'content_hash': digest(p)})
        return entries, candidates

    def assert_empty(self):
        self.assertEqual(Revision.objects.count(), 0)
        self.assertEqual(ImportExecutionReceipt.objects.count(), 0)

    def test_success_creates_each_revision_and_receipt(self):
        entries, _ = self.entries()
        with transaction.atomic():
            results = publish_with_cli(entries, operator='synthetic_owner')
        self.assertEqual(len(results), 2)
        self.assertEqual(Revision.objects.count(), 2)
        self.assertEqual(ImportExecutionReceipt.objects.filter(execution_outcome='created').count(), 2)

    def test_second_cli_failure_rolls_back_first_publication(self):
        entries, _ = self.entries()
        path = self.root / 'review-1.json'
        broken = json.loads(path.read_text())
        broken['content_hash'] = 'sha256:' + '0' * 64
        path.write_text(json.dumps(broken))
        with self.assertRaises(CommandError):
            with transaction.atomic():
                publish_with_cli(entries, operator='synthetic_owner')
        self.assert_empty()

    def test_service_rejection_and_its_failure_receipt_roll_back_batch(self):
        entries, candidates = self.entries()
        raw = self.root / candidates[1].evidence_documents[0]['raw_artifact_reference']
        raw.write_bytes(b'synthetic changed source')
        with self.assertRaises(Revision.DoesNotExist):
            with transaction.atomic():
                publish_with_cli(entries, operator='synthetic_owner')
        self.assert_empty()

    def test_precommit_verification_failure_rolls_back_successful_batch(self):
        entries, _ = self.entries()
        with self.assertRaisesRegex(RuntimeError, 'synthetic precommit failure'):
            with transaction.atomic():
                results = publish_with_cli(entries, operator='synthetic_owner')
                self.assertEqual(len(results), 2)
                raise RuntimeError('synthetic precommit failure')
        self.assert_empty()
