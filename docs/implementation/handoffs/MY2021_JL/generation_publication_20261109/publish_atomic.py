"""Exact owner-authorized publication with one outer Django transaction.

preflight: live SQLite read-only; verify reviewed artifacts and physical backup.
publish: existing human-confirmed CLI/service, 95 nested calls in one transaction.
verify: live SQLite read-only, reconcile committed rows and actual resolution.
No application/contract change, canonical plan/import, migration or backfill.
"""
import hashlib
import importlib.metadata
import json
import os
import sqlite3
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
REVIEW = BASE / 'generation_correspondence_review_20261109'
LATEST = BASE / 'fuel_completion_20261109'
ROOT = next(p for p in HERE.parents if (p / 'manage.py').is_file())


def load(p):
    return json.loads(p.read_text())


def rel(p):
    return str(p.relative_to(ROOT))


def sha(p):
    return 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as stream:
        json.dump(obj, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def initialise(readonly):
    sys.path.insert(0, str(ROOT))
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    assert not os.environ.get('RIGARCHIVE_TEST_DB_PATH'), 'Production driver must not target a test database'
    from django.conf import settings
    if readonly:
        settings.DATABASES['default']['NAME'] = 'file:' + str(ROOT / 'db.sqlite3') + '?mode=ro'
        settings.DATABASES['default']['OPTIONS'] = {'uri': True}
    else:
        assert Path(settings.DATABASES['default']['NAME']) == ROOT / 'db.sqlite3'
    import django
    django.setup()
    from django.db import connection
    if readonly:
        connection.cursor().execute('PRAGMA query_only=ON')


def ro(path):
    c = sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True)
    c.execute('PRAGMA query_only=ON')
    return c


def snapshot(c):
    """Hash all rows, including private tables, without reporting their values."""
    from reference.ingestion.generation_correspondence import digest
    schema = c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_autoindex%' ORDER BY type,name").fetchall()
    tables = {}
    for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
        quoted = '"' + name.replace('"', '""') + '"'
        info = c.execute('PRAGMA table_info(' + quoted + ')').fetchall()
        columns = [r[1] for r in info]
        positions = [n for n, r in enumerate(info) if r[5]]
        assert positions, 'Table without primary key: ' + name
        # Django registers declared-type converters (notably bool/date), while
        # the independent read-only backup reader returns native SQLite values.
        # Unary + is a SQLite no-op expression: it preserves the stored value
        # but removes declared-column metadata, so both readers hash identical
        # native values. Never mistake Python conversion for a database change.
        expressions = ','.join('+"' + column.replace('"', '""') + '"' for column in columns)
        data = c.execute('SELECT ' + expressions + ' FROM ' + quoted).fetchall()
        rows = {hashlib.sha256(json.dumps([r[n] for n in positions], default=str, separators=(',', ':')).encode()).hexdigest():
                hashlib.sha256(json.dumps(list(r), default=str, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest() for r in data}
        assert len(rows) == len(data)
        tables[name] = {'count': len(data), 'columns': columns, 'rows': rows}
    return {'schema_digest': digest(schema), 'tables': tables,
            'sequences': dict(c.execute('SELECT name,seq FROM sqlite_sequence').fetchall())}


def reconcile(before, after, additions):
    assert before['schema_digest'] == after['schema_digest'], 'Schema changed'
    assert set(before['tables']) == set(after['tables'])
    results = {}
    for table, old in before['tables'].items():
        new = after['tables'][table]
        assert old['columns'] == new['columns']
        assert all(new['rows'].get(k) == h for k, h in old['rows'].items()), 'Preexisting row changed: ' + table
        assert new['count'] == old['count'] + additions.get(table, 0), 'Unexpected row count: ' + table
        results[table] = {'before': old['count'], 'after': new['count'], 'all_preexisting_rows_unchanged': True,
                          'new_rows': new['count'] - old['count']}
    assert set(before['sequences']) == set(after['sequences'])
    for table, value in before['sequences'].items():
        assert after['sequences'][table] == value + additions.get(table, 0), 'Unexpected sequence change: ' + table
    return results


def counts():
    from reference.models import VehicleDefinition, ImportExecutionReceipt, GenerationCorrespondenceRevision
    return {'VehicleDefinitions': VehicleDefinition.objects.count(), 'audit_receipts': ImportExecutionReceipt.objects.count(),
            'correspondences': GenerationCorrespondenceRevision.objects.count()}


def verify_files():
    baseline = load(HERE / 'preservation_baseline.json')
    for p, h in baseline['preexisting_handoff_files'].items():
        assert sha(ROOT / p) == h, p
    for p, h in baseline['code_and_contract_hashes'].items():
        assert sha(ROOT / p) == h, p
    assert sha(ROOT / baseline['backup']['path']) == baseline['backup']['sha256']


def key(identity):
    return tuple(identity[n] for n in ('source_id', 'source_namespace', 'identity_type', 'native_identifier'))


def candidates():
    from reference.ingestion.serialization import deserialize_artifact, serialize_artifact, candidate_config_doc_to_dict
    from reference.ingestion.generation_correspondence import digest, validate_generation_evidence
    from reference.ingestion.importing.powertrain_identity import candidate_powertrain
    rows = load(LATEST / 'current_candidate_index.json')['rows']
    assert len(rows) == 73 and Counter(r['body_style'] for r in rows) == {'2-door': 23, '4-door': 50}
    assert len({r['marketed_trim_proposal'] for r in rows}) == 24
    result = {}; required = defaultdict(set)
    for row in rows:
        c = deserialize_artifact((ROOT / row['candidate_artifact']).read_text())
        candidate_powertrain(c, complete=True, verify_bytes=True)
        validate_generation_evidence(c.generation_evidence, c.evidence_documents)
        assert digest(candidate_config_doc_to_dict(c)) == row['candidate_hash']
        assert sha(ROOT / row['candidate_artifact']) == row['artifact_sha256']
        assert serialize_artifact(deserialize_artifact(serialize_artifact(c))) == serialize_artifact(c)
        assert (c.candidate_identity.model_year, c.candidate_identity.market) == (2021, 'US')
        assert row['model_code'] != 'JLUL74' and row['research_row_id'] != 'JL21-71'
        result[row['research_row_id']] = c
        for identity in c.generation_evidence:
            assert identity['native_identifier'] == row['model_code']
            required[key(identity)].add(row['research_row_id'])
    assert len(required) == 95
    from reference.ingestion.serialization import adjudication_from_dict
    from reference.ingestion.classification_adjudication import validate_classification_adjudication
    records = load(BASE / 'candidate_classification_20261109/approved_field_decision_index.json')['records']
    assert len(records) == 88
    for record in records:
        old = adjudication_from_dict(load(ROOT / record['approved_adjudication']))
        validate_classification_adjudication(old, require_approved=True)
        assert sha(ROOT / record['approved_adjudication']) == record['approved_adjudication_sha256']
        current = result[record['research_row_id']]
        doc = next(d for d in current.evidence_documents if d['source_id'] == 'human_classification_adjudication')
        active = adjudication_from_dict(load(ROOT / doc['raw_artifact_reference']))
        assert active.evidence_anchors['classifications'][record['field']] == record['classification']
    assert result['JL21-70'].canonical_powertrain['fuel_type'] == 'gasoline'
    for row in rows:
        if row['engine_code'] == 'ECX':
            assert not any(d['source_id'] == 'human_classification_adjudication' for d in result[row['research_row_id']].evidence_documents)
    rhd = load(BASE / 'candidate_classification_20261109/sport_RHD_preservation.json')
    assert rhd['deferred_decision']['decision_id'] == 'CLASS-075' and rhd['discovery_row']['model_code'] == 'JLUL74'
    return rows, result, required


def proposal_entries():
    from reference.ingestion.generation_correspondence import digest, validate_review_payload, validate_documents
    entries = load(REVIEW / 'new_correspondence_proposal_index.json')['proposals']
    assert len(entries) == 95 and len({tuple(e['key']) for e in entries}) == 95
    for entry in entries:
        artifact = load(ROOT / entry['proposal'])
        assert set(artifact) == {'review', 'content_hash'}
        p = artifact['review']
        validate_review_payload(p); validate_documents(p['evidence'], verify_bytes=True)
        assert digest(p) == artifact['content_hash'] == entry['content_hash']
        assert sha(ROOT / entry['proposal']) == entry['proposal_file_sha256']
        assert p['revision_uuid'] == entry['revision_uuid'] and p['correspondence_uuid'] == entry['correspondence_uuid']
        assert key(p) == tuple(entry['key'])
        assert p['generation_uuid'] == '38d3c3ac-f825-4406-abb5-c2d12b9129a4' and entry['target_generation_PK'] == 32
        assert p['market'] == 'US' and p['start_year'] == p['end_year'] == 2021
        assert p['finding'] == 'established' and not p['restrictions']
        assert p['supersedes_uuid'] is None and p['revision_number'] == 1
        assert len(p['evidence']) == 1 and p['evidence'] == [load(ROOT / entry['shared_selector'])]
    assert len({e['revision_uuid'] for e in entries}) == len({e['correspondence_uuid'] for e in entries}) == 95
    return entries


def preflight():
    initialise(True)
    from django.core.management import call_command
    from django.db import connection
    from reference.models import Generation, GenerationCorrespondenceRevision as Revision
    from reference.ingestion.generation_correspondence import digest, validate_documents, resolve_generation
    from django.core.exceptions import ValidationError
    assert not (HERE / 'preflight.json').exists(), 'Existing preflight: preserve and inspect, do not repeat'
    assert sys.version_info[:3] == (3, 13, 1)
    requirements = (ROOT / 'requirements.txt').read_text().splitlines()
    for r in requirements:
        name, version = r.split('=='); assert importlib.metadata.version(name) == version
    # Read every complete reviewed JSON and text artifact; verify every reviewed
    # byte, including proposal/selector/candidate indices, before publication.
    for p, h in load(REVIEW / 'artifact_hashes.json').items():
        path = REVIEW / p; assert sha(path) == h, p
        if path.suffix == '.json':
            load(path)
        else:
            path.read_text()
    for p, h in load(LATEST / 'artifact_hashes.json').items():
        assert sha(LATEST / p) == h, p
    start = sha(ROOT / 'db.sqlite3')
    assert counts() == {'VehicleDefinitions': 861, 'audit_receipts': 2980, 'correspondences': 64}, 'Material database discrepancy; stop'
    gen = Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32, uuid='38d3c3ac-f825-4406-abb5-c2d12b9129a4')
    vm = gen.vehicle_model
    assert gen.is_active and vm.is_active and vm.manufacturer.is_active and gen.name == 'JL'
    assert vm.name == 'Wrangler' and vm.manufacturer.name == 'Jeep'
    for r in Revision.objects.select_related('generation', 'vehicle_model__manufacturer', 'supersedes'):
        r.clean(); assert digest(r.review_payload()) == r.content_hash; validate_documents(r.evidence, verify_bytes=True)
    rows, docs, required = candidates()
    entries = proposal_entries(); objects = []; selectors = load(REVIEW / 'shared_selector_index.json')['selectors']
    assert len(selectors) == 95
    for e in entries:
        p = load(ROOT / e['proposal'])['review']; k = tuple(e['key'])
        assert set(e['candidate_references']) == required[k]
        assert p['vehicle_model_uuid'] == str(vm.uuid)
        selector = next(s for s in selectors if s['key'] == e['key'])
        assert sha(ROOT / selector['path']) == selector['file_sha256']
        assert digest(p['evidence'][0]) == selector['selector_content_hash']
        assert all(p['evidence'][0] in docs[rid].evidence_documents for rid in required[k])
        assert not Revision.objects.filter(uuid=p['revision_uuid']).exists()
        assert not Revision.objects.filter(correspondence_uuid=p['correspondence_uuid']).exists()
        assert not Revision.objects.filter(vehicle_model=vm, market='US', source_id=k[0], source_namespace=k[1], identity_type=k[2], native_identifier=k[3], start_year__lte=2021, end_year__gte=2021, successor__isnull=True).exists()
        obj = Revision(uuid=p['revision_uuid'], correspondence_uuid=p['correspondence_uuid'], revision_number=1,
            vehicle_model=vm, generation=gen, **{n: p[n] for n in ('source_id','source_namespace','identity_type','native_identifier','market','start_year','end_year','restrictions','evidence','finding','reviewer','review_notes')},
            reviewed_at=datetime.fromisoformat(p['reviewed_at']), content_hash=e['content_hash'])
        obj.full_clean(exclude=['content_hash']); assert digest(obj.review_payload()) == e['content_hash']; objects.append(obj)
    assert set(required) == {tuple(e['key']) for e in entries}
    def lookup(model, year, market, identities):
        assert model.pk == vm.pk and year == 2021 and market == 'US'
        keys = {key(i) for i in identities}
        return [o for o in objects if key(o.review_payload()) in keys]
    simulation = []
    with patch('reference.ingestion.generation_correspondence._applicable_revisions', side_effect=lookup):
        for rid, c in docs.items():
            r = resolve_generation(vm, 2021, 'US', c.generation_evidence, c.evidence_documents, {'trim_name': c.candidate_identity.trim_name, 'drivetrain': '4WD'})
            assert r['parents']['generation_id'] == 32 and r['parents']['generation_uuid'] == str(gen.uuid)
            assert r['basis'] == 'reviewed_source_correspondence'
            simulation.append({'candidate_reference': rid, 'target_generation_PK': 32, 'correspondences': r['correspondences']})
        for obj in list(objects):
            objects.remove(obj); c = docs[sorted(required[key(obj.review_payload())])[0]]
            try:
                resolve_generation(vm, 2021, 'US', c.generation_evidence, c.evidence_documents)
            except ValidationError as exc:
                assert exc.messages == ['Missing reviewed generation correspondence.']
            else:
                raise AssertionError('Unnecessary proposal or weakened resolver')
            objects.append(obj)
    log = StringIO(); call_command('check', stdout=log)
    files = {rel(p): sha(p) for p in BASE.rglob('*') if p.is_file() and not p.is_relative_to(HERE)}
    assert sha(ROOT / 'db.sqlite3') == start
    # Existing Layer1 snapshot procedure, on a read-only live URI. The output is
    # new, ignored, and verified before opening any write-authorized connection.
    backup = ROOT / 'backups/review' / ('MY2021_JL_correspondence_prepublication_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite3')
    backup.parent.mkdir(parents=True, exist_ok=True)
    assert not backup.exists()
    assert subprocess.run(['git', 'check-ignore', '-q', rel(backup)], cwd=ROOT).returncode == 0
    backup_log = StringIO(); call_command('snapshot_db', output=str(backup), stdout=backup_log)
    with (HERE / 'backup_command.txt').open('x') as stream:
        stream.write(backup_log.getvalue())
    b = ro(backup)
    assert b.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not b.execute('PRAGMA foreign_key_check').fetchall()
    state = snapshot(b); b.close()
    live = ro(ROOT / 'db.sqlite3'); assert snapshot(live) == state; live.close()
    assert sha(ROOT / 'db.sqlite3') == start
    protected = ['reference/models.py', 'reference/ingestion/generation_correspondence.py',
                 'reference/management/commands/publish_generation_correspondence.py',
                 'reference/ingestion/contracts.py', 'reference/ingestion/serialization.py',
                 'reference/ingestion/classification_adjudication.py']
    save(HERE / 'preservation_baseline.json', {'preexisting_handoff_files': files,
         'database_before_sha256': start, 'database_snapshot': state,
         'backup': {'path': rel(backup), 'sha256': sha(backup), 'integrity': 'ok', 'foreign_keys': 'passed', 'logical_all_table_match': True},
         'code_and_contract_hashes': {p: sha(ROOT / p) for p in protected}})
    save(HERE / 'environment.json', {'python': sys.version, 'interpreter': sys.executable,
         'Django': importlib.metadata.version('Django'), 'pypdf': importlib.metadata.version('pypdf'),
         'requirements': requirements, 'requirements_match': True})
    save(HERE / 'preflight.json', {'result': 'passed before publication', 'recorded_at': datetime.now(timezone.utc).isoformat(),
         'authority': 'Current explicit project-owner authorization to publish the exact95 reviewed MY2021 correspondences in one atomic batch',
         'writes_authorized': '95 new GenerationCorrespondenceRevision rows and95 correspondence-publication ImportExecutionReceipt rows; normal sequence advances only',
         'operator': 'project_owner', 'agent': 'codex', 'existing_CLI_confirmation_authorized': 'yes for each exact approved proposal',
         'review_manifest_sha256': sha(REVIEW / 'artifact_hashes.json'), 'proposal_index_sha256': sha(REVIEW / 'new_correspondence_proposal_index.json'),
         'candidate_index_sha256': sha(LATEST / 'current_candidate_index.json'), 'exact_proposals': entries,
         'distinct_keys': 95, 'shared_selectors': 95, 'current_candidates': 73, 'simulation': simulation,
         'all_95_required': True, 'duplicates_conflicts_UUID_or_chain_reuse': 0,
         'prior_88_decisions_and_392_fuel_approval_preserved': True, 'RHD_CLASS075': 'preserved/deferred',
         'counts': counts(), 'Django_check': log.getvalue().strip(), 'backup': load(HERE / 'preservation_baseline.json')['backup'],
         'atomicity': 'All accepted CLI/service calls and precommit verification run on one Django connection inside transaction.atomic(durable=True); any failure raises and rolls back all revisions and receipts'})
    connection.close()
    print('PREFLIGHT PASSED: exact95;73 candidates;consistent verified backup', rel(backup), flush=True)


def publish_with_cli(entries, *, operator='project_owner', agent='codex', log_dir=None):
    """Caller supplies outer transaction; any non-created outcome is fatal."""
    from django.core.management import call_command
    from django.db import connection
    from reference.models import GenerationCorrespondenceRevision as Revision, ImportExecutionReceipt
    from reference.ingestion.generation_correspondence import digest
    assert connection.in_atomic_block, 'Batch requires an enclosing transaction'
    results = []
    for number, entry in enumerate(entries, 1):
        p = load(Path(entry['proposal']))['review']
        stdout = StringIO(); stderr = StringIO()
        try:
            with patch('builtins.input', return_value='yes'):
                call_command('publish_generation_correspondence', review=entry['proposal'], operator=operator,
                             agent=agent, skip_checks=True, stdout=stdout, stderr=stderr)
            revision = Revision.objects.get(uuid=p['revision_uuid'])
            assert revision.content_hash == entry['content_hash'] == digest(p) and revision.review_payload() == p
            receipt = ImportExecutionReceipt.objects.get(correspondence_revision=revision)
            assert receipt.execution_outcome == 'created', 'Publication was not a new created finding'
            assert receipt.operation_type == 'correspondence_publication' and receipt.operator_label == operator
            assert receipt.manifest_hash == entry['content_hash']
            assert receipt.resolution_snapshot_json['review'] == p
            assert receipt.resolution_snapshot_json['content_hash'] == entry['content_hash']
            assert receipt.resolution_snapshot_json['attribution']['execution_agent'] == agent
            assert receipt.source_id == p['source_id'] and receipt.native_identifier == p['native_identifier']
            assert receipt.source_identity_type == p['identity_type'] and receipt.candidate_reference == p['revision_uuid']
            results.append({'proposal': entry['proposal'], 'source_model_key': list(key(p)), 'content_hash': entry['content_hash'],
                 'revision_PK': revision.pk, 'revision_uuid': str(revision.uuid), 'correspondence_uuid': str(revision.correspondence_uuid),
                 'receipt_PK': receipt.pk, 'receipt_uuid': str(receipt.uuid), 'execution_outcome': 'created',
                 'target_generation_PK': revision.generation_id, 'candidate_references': entry.get('candidate_references', [])})
        finally:
            if log_dir:
                log_dir.mkdir(parents=True, exist_ok=True)
                with (log_dir / f'{number:02d}.txt').open('x') as stream:
                    stream.write('Invocation inside outer atomic transaction; this log alone does not establish commit.\n')
                    stream.write(stdout.getvalue() + stderr.getvalue())
    return results


def actual_resolutions(rows, docs, entries):
    from reference.models import Generation
    from reference.ingestion.generation_correspondence import resolve_generation
    gen = Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32, uuid='38d3c3ac-f825-4406-abb5-c2d12b9129a4')
    result = []
    for row in rows:
        rid = row['research_row_id']; c = docs[rid]
        resolution = resolve_generation(gen.vehicle_model, 2021, 'US', c.generation_evidence, c.evidence_documents,
                                        {'trim_name': c.candidate_identity.trim_name, 'drivetrain': '4WD'})
        assert resolution['parents']['generation_id'] == 32 and resolution['parents']['generation_uuid'] == str(gen.uuid)
        assert resolution['basis'] == 'reviewed_source_correspondence'
        expected = {e['revision_uuid']: e['content_hash'] for e in entries if rid in e['candidate_references']}
        assert {r['uuid']: r['hash'] for r in resolution['correspondences']} == expected
        result.append({'candidate_reference': rid, 'model_code': row['model_code'], 'candidate_artifact': row['candidate_artifact'],
             'candidate_hash': row['candidate_hash'], 'target_generation_PK': 32, 'target_generation_uuid': str(gen.uuid),
             'basis': resolution['basis'], 'actual_published_state': True, 'correspondences': resolution['correspondences']})
    return result


def publish():
    initialise(False)
    from django.db import connection, transaction
    from reference.models import GenerationCorrespondenceRevision as Revision
    assert not (HERE / 'publication_results.json').exists(), 'Already published; do not repeat'
    pre = load(HERE / 'preflight.json'); assert pre['result'] == 'passed before publication'
    assert pre['distinct_keys'] == len(pre['exact_proposals']) == 95
    verify_files()
    baseline = load(HERE / 'preservation_baseline.json')
    assert sha(ROOT / 'db.sqlite3') == baseline['database_before_sha256'], 'DB changed since verified backup'
    entries = proposal_entries(); rows, docs, required = candidates()
    assert entries == pre['exact_proposals']
    committed = False
    try:
        with transaction.atomic(durable=True):
            # The transaction's read snapshot must match the verified consistent
            # backup. A competing write/upgrade failure aborts the whole batch.
            connection.ensure_connection()
            assert snapshot(connection.connection) == baseline['database_snapshot'], 'Concurrent database change'
            assert counts() == pre['counts']
            assert not Revision.objects.filter(uuid__in=[e['revision_uuid'] for e in entries]).exists()
            # Verify all exact keys again under this same transaction snapshot.
            for e in entries:
                k = tuple(e['key'])
                assert not Revision.objects.filter(market='US', source_id=k[0], source_namespace=k[1], identity_type=k[2], native_identifier=k[3], start_year__lte=2021, end_year__gte=2021, successor__isnull=True).exists()
            results = publish_with_cli(entries, log_dir=HERE / 'workflow_logs')
            assert len(results) == len({r['revision_PK'] for r in results}) == len({r['receipt_PK'] for r in results}) == 95
            assert counts() == {'VehicleDefinitions': 861, 'audit_receipts': 3075, 'correspondences': 159}
            resolutions = actual_resolutions(rows, docs, entries)
            assert len(resolutions) == 73
            reconcile(baseline['database_snapshot'], snapshot(connection.connection),
                      {'reference_generationcorrespondencerevision': 95, 'reference_importexecutionreceipt': 95})
            assert connection.connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not connection.connection.execute('PRAGMA foreign_key_check').fetchall()
            verify_files()
        committed = True
    except Exception as exc:
        connection.close()
        live = ro(ROOT / 'db.sqlite3'); after = snapshot(live); live.close()
        rolled_back = after == baseline['database_snapshot']
        failure = HERE / 'publication_failure.json'
        if failure.exists():
            failure = HERE / ('publication_failure_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        save(failure, {'error_type': type(exc).__name__, 'error': str(exc),
             'committed': committed, 'entire_database_logically_matches_prepublication_snapshot': rolled_back,
             'backup_preserved': baseline['backup'], 'no_retry_or_restore_performed': True})
        raise
    # Success records are emitted only after the outer transaction commits.
    save(HERE / 'publication_results.json', {'status': 'committed atomically', 'published': 95,
         'new_receipts': 95, 'revision_PKs': [r['revision_PK'] for r in results],
         'receipt_PKs': [r['receipt_PK'] for r in results], 'results': results,
         'atomic_precommit_actual_resolutions': resolutions})
    for n, item in enumerate(results, 1):
        save(HERE / 'publication_records' / f'{n:02d}.json', item)
    connection.close()
    print('COMMITTED ATOMICALLY:95 correspondences and95 receipts;73 actual resolutions checked before commit', flush=True)


def verify():
    initialise(True)
    from django.db import connection
    from django.core.management import call_command
    from reference.models import GenerationCorrespondenceRevision as Revision, ImportExecutionReceipt
    from reference.ingestion.generation_correspondence import digest
    baseline = load(HERE / 'preservation_baseline.json'); published = load(HERE / 'publication_results.json')
    assert published['status'] == 'committed atomically' and published['published'] == 95
    verify_files(); rows, docs, required = candidates(); entries = proposal_entries()
    reconciled = []
    for entry in entries:
        p = load(ROOT / entry['proposal'])['review']
        rev = Revision.objects.get(uuid=p['revision_uuid']); rev.clean()
        assert rev.content_hash == digest(rev.review_payload()) == entry['content_hash']
        assert rev.review_payload() == p and rev.generation_id == 32
        receipt = ImportExecutionReceipt.objects.get(correspondence_revision=rev)
        assert receipt.operation_type == 'correspondence_publication' and receipt.execution_outcome == 'created'
        assert receipt.manifest_hash == entry['content_hash'] and receipt.resolution_snapshot_json['review'] == p
        assert receipt.operator_label == 'project_owner' and receipt.resolution_snapshot_json['attribution']['execution_agent'] == 'codex'
        original = next(r for r in published['results'] if r['revision_uuid'] == str(rev.uuid))
        assert original['revision_PK'] == rev.pk and original['receipt_PK'] == receipt.pk
        reconciled.append({**original, 'proposal_file_sha256': sha(ROOT / entry['proposal']),
                           'approved_payload_equals_published_payload': True})
    actual = actual_resolutions(rows, docs, entries)
    expected = {'VehicleDefinitions': 861, 'audit_receipts': 3075, 'correspondences': 159}
    assert counts() == expected
    live = ro(ROOT / 'db.sqlite3')
    comparison = reconcile(baseline['database_snapshot'], snapshot(live),
                          {'reference_generationcorrespondencerevision': 95, 'reference_importexecutionreceipt': 95})
    assert live.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not live.execute('PRAGMA foreign_key_check').fetchall(); live.close()
    check = StringIO(); call_command('check', stdout=check)
    verify_files(); connection.close()
    save(HERE / 'proposal_publication_reconciliation.json', {'published': 95, 'rows': reconciled})
    save(HERE / 'candidate_resolution_report.json', {'actual_published_state': True, 'resolved_to_JL32': 73, 'rows': actual})
    save(HERE / 'postpublication_verification.json', {'result': 'passed', 'counts': expected,
         'new_correspondences': 95, 'new_publication_receipts': 95, 'actual_candidate_resolutions_to_JL32': 73,
         'all_861_preexisting_VehicleDefinitions_unchanged': True, 'all_64_preexisting_correspondences_unchanged': True,
         'all_preexisting_database_rows_and_schema_unchanged': True, 'table_reconciliation': comparison,
         'only_additions': '95 correspondences +95 publication receipts +normal sequence advances',
         'candidate_and_classification_files_unchanged': True, 'RHD_CLASS075': 'unchanged/deferred',
         'SQLite_integrity': 'ok', 'foreign_key_violations': 0, 'Django_check': check.getvalue().strip(),
         'database_before_sha256': baseline['database_before_sha256'], 'database_after_sha256': sha(ROOT / 'db.sqlite3'),
         'backup': baseline['backup'], 'backup_unchanged': True,
         'preexisting_handoff_files_preserved': len(baseline['preexisting_handoff_files']),
         'application_contract_schema_changes': False, 'canonical_plans_or_imports': 0})
    print('POST-COMMIT VERIFIED:73/73 actual JL32 resolutions;861 definitions unchanged;3075 receipts;159 correspondences', flush=True)


if __name__ == '__main__':
    {'preflight': preflight, 'publish': publish, 'verify': verify}[sys.argv[1]]()
