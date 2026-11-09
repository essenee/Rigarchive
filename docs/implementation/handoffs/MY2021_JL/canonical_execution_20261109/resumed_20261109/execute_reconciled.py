"""Exact73 owner-authorized MY2021 execution through the accepted Matrix CLI.

Parent preflight/reconciliation use live SQLite mode=ro/query_only. Only the
accepted child execution CLI writes canonical records, in its existing durable
model-year transaction with fresh per-row plans and rollback/reconciliation.
"""
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
PLANNING = BASE / 'final_planning_20261109'
LATEST = BASE / 'fuel_completion_20261109'
PUBLICATION = BASE / 'generation_publication_20261109'
ROOT = next(p for p in HERE.parents if (p / 'manage.py').is_file())
EXPECTED = 'sha256:6926df6c06e4bd471bbda02c67257cf7a7e2999cf5cdfebfc8b06ead31a9996e'
sys.path.insert(0, str(ROOT))
from docs.implementation.handoffs.MY2021_JL.generation_publication_20261109 import publish_atomic as helpers
helpers.initialise(True)
from django.db import connection
from django.core.management import call_command
from reference.models import Generation, GenerationCorrespondenceRevision as Revision, VehicleDefinition, ImportExecutionReceipt
from reference.ingestion.serialization import candidate_config_doc_to_dict, deserialize_artifact
from reference.ingestion.generation_correspondence import digest, validate_documents, revalidate_resolution
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.importing.matrix_workflow import MatrixYear, _references, _identity
from reference.ingestion.matrix import validate_matrix, compute_matrix_digest
from reference.ingestion.matrix_approval import read_matrix_approval
from reference.ingestion.manifest import dict_to_manifest, manifest_to_dict, reconstruct_plan_from_manifest
from reference.powertrain import FIELDS, BASE_FIELDS, record_powertrain
from docs.implementation.handoffs.MY2021_JL.canonical_execution_20261109.resumed_20261109.baseline_guard import (
    verify_reconciled_state, reconcile_preserving_authentication, BASELINE_FILE,
)


def load(p):
    return json.loads(p.read_text())


def sha(p):
    return 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p):
    return str(p.relative_to(ROOT))


def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as stream:
        json.dump(obj, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def unchanged_files():
    b = load(HERE / 'preservation_baseline.json')
    for p, h in b['preexisting_handoff_files'].items():
        assert sha(ROOT / p) == h, p
    for p, h in b['code_and_contract_hashes'].items():
        assert sha(ROOT / p) == h, p
    assert sha(ROOT / b['backup']['path']) == b['backup']['sha256']


def inputs():
    matrix = load(PLANNING / 'matrix_2_1.json')
    validate_matrix(matrix); assert compute_matrix_digest(matrix) == EXPECTED
    assert matrix['market'] == 'US' and matrix['model_years'] == [2021]
    approval = read_matrix_approval(PLANNING / 'matrix_approval.json', matrix)
    assert approval['matrix_digest'] == EXPECTED and approval['operator'] == 'project_owner'
    rows, candidates, required = helpers.candidates()
    assert len(rows) == len(matrix['rows']) == 73 and len(required) == 95
    assert {r['research_row_id'] for r in rows} == {r['row_id'] for r in matrix['rows']}
    assert Counter(r['body_style'] for r in rows) == {'2-door': 23, '4-door': 50}
    assert len({r['marketed_trim_proposal'] for r in rows}) == 24
    return matrix, approval, rows, candidates


def preflight():
    assert not (HERE / 'preflight.json').exists(), 'Preserve existing preflight; no blind rerun'
    for directory in (PLANNING, LATEST, PUBLICATION):
        for p, h in load(directory / 'artifact_hashes.json').items():
            path = directory / p; assert sha(path) == h, p
            if path.suffix == '.json':
                load(path)
            else:
                path.read_text()
    assert sys.version_info[:3] == (3, 13, 1)
    requirements = (ROOT / 'requirements.txt').read_text().splitlines()
    for r in requirements:
        name, version = r.split('=='); assert importlib.metadata.version(name) == version
    matrix, approval, rows, candidates = inputs()
    accepted_state = verify_reconciled_state('initial_preflight')
    current_hash = accepted_state['current_file_sha256']
    counts = helpers.counts()
    assert counts == {'VehicleDefinitions': 861, 'audit_receipts': 3075, 'correspondences': 159}
    assert not VehicleDefinition.objects.filter(generation_id=32, model_year=2021, market='US').exists()
    gen = Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32, uuid='38d3c3ac-f825-4406-abb5-c2d12b9129a4')
    vm = gen.vehicle_model
    for name, obj in [('manufacturer', vm.manufacturer), ('vehicle_model', vm), ('generation', gen)]:
        assert obj.is_active and matrix['parents'][name] == _identity(obj)
    pubs = load(PUBLICATION / 'publication_results.json')['results']
    assert len(pubs) == 95 and {p['revision_PK'] for p in pubs} == set(range(65, 160))
    for p in pubs:
        r = Revision.objects.get(pk=p['revision_PK'], uuid=p['revision_uuid']); r.clean()
        assert r.content_hash == p['content_hash'] == digest(r.review_payload()) and r.generation_id == 32
        receipt = ImportExecutionReceipt.objects.get(pk=p['receipt_PK'], correspondence_revision=r)
        assert receipt.execution_outcome == 'created' and receipt.manifest_hash == r.content_hash
        assert receipt.resolution_snapshot_json['review'] == r.review_payload()
    plan_index = load(PLANNING / 'plan_index.json')['plans']
    proof_index = load(PLANNING / 'engine_proof_index.json')['rows']
    resolution_index = load(PLANNING / 'resolution_index.json')['rows']
    assert len(plan_index) == len(proof_index) == len(resolution_index) == 73
    snapshots = []; seen_trim = defaultdict(list); creation_bases = []
    for n, row in enumerate(sorted(rows, key=lambda r: r['research_row_id'])):
        rid = row['research_row_id']; c = candidates[rid]
        pi = next(p for p in plan_index if p['row_id'] == rid)
        raw = load(ROOT / pi['manifest']); manifest = dict_to_manifest(raw)
        assert manifest_to_dict(manifest) == raw and manifest.manifest_hash == pi['manifest_hash']
        assert sha(ROOT / pi['manifest']) == pi['manifest_file_sha256']
        snapshot_plan = reconstruct_plan_from_manifest(manifest.plans[0]); revalidate_resolution(snapshot_plan)
        fresh = plan_candidate_import(c)
        assert asdict(fresh) == asdict(snapshot_plan)
        assert fresh.eligibility_status.value == 'eligible' and fresh.planned_action.value == 'create'
        assert fresh.resolved_generation_id == 32 and fresh.existing_vehicle_definition_id is None
        assert fresh.create_basis.value == 'first_representation' and fresh.namespace_snapshot_count == 0
        mr = next(r for r in matrix['rows'] if r['row_id'] == rid)
        assert mr['candidate_reference'] == c.candidate_reference and mr['candidate_digest'] == fresh.candidate_hash == row['candidate_hash']
        assert mr['target_fields'] == fresh.target_vehicle_definition_fields and mr['target_slug'] == fresh.target_slug
        assert mr['action'] == 'create' and mr['existing_record'] is None
        assert (mr['evidence'], mr['correspondence']) == _references(fresh)
        expected = {p['revision_uuid']: p['content_hash'] for p in pubs if rid in p['candidate_references']}
        assert {r['uuid']: r['hash'] for r in fresh.generation_resolution['correspondences']} == expected
        proof_entry = next(p for p in proof_index if p['row_id'] == rid)
        proof = load(ROOT / proof_entry['proof_artifact'])
        assert sha(ROOT / proof_entry['proof_artifact']) == proof_entry['proof_file_sha256']
        assert digest(proof) == proof_entry['proof_content_digest']
        assert proof == fresh.generation_resolution['engine_distinction'] and proof['version'] == '2.0' and proof['peers'] == []
        resolution_entry = next(r for r in resolution_index if r['row_id'] == rid)
        resolution = load(ROOT / resolution_entry['resolution_artifact'])
        assert sha(ROOT / resolution_entry['resolution_artifact']) == resolution_entry['resolution_file_sha256']
        assert digest(resolution) == resolution_entry['resolution_content_digest']
        assert resolution == fresh.generation_resolution and resolution['resolution_version'] == '1.1'
        assert resolution['parents']['generation_id'] == 32 and resolution['parents']['generation_uuid'] == str(gen.uuid)
        prior = seen_trim[c.candidate_identity.trim_name]
        expected_basis = 'first_representation' if n == 0 else 'mechanical_dimension' if prior else 'source_established_grade'
        assert mr['permitted_create_bases'] == sorted({'first_representation', expected_basis})
        assert all(x != c.canonical_powertrain for x in prior)
        prior.append(c.canonical_powertrain)
        creation_bases.append({'row_id': rid, 'anticipated_basis': expected_basis, 'permitted_create_bases': mr['permitted_create_bases']})
        snapshots.append({'row_id': rid, 'candidate_artifact': row['candidate_artifact'], 'candidate_digest': row['candidate_hash'],
             'snapshot_manifest_hash': manifest.manifest_hash, 'target_fields': mr['target_fields'], 'target_slug': mr['target_slug']})
        print('PRECHECK', n + 1, '/73', rid, flush=True)
    status = MatrixYear(matrix, approval, 2021, candidates).status()
    assert status['counts'] == {'pending_create': 73} and not status['complete']
    assert Counter(x['anticipated_basis'] for x in creation_bases) == {'first_representation': 1, 'source_established_grade': 23, 'mechanical_dimension': 49}
    check = StringIO(); call_command('check', stdout=check)
    files = {rel(p): sha(p) for p in BASE.rglob('*') if p.is_file() and not p.is_relative_to(HERE)}
    verify_reconciled_state('before_backup')
    backup = ROOT / 'backups/review' / ('MY2021_JL_canonical_preimport_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.sqlite3')
    backup.parent.mkdir(parents=True, exist_ok=True)
    assert not backup.exists()
    assert subprocess.run(['git', 'check-ignore', '-q', rel(backup)], cwd=ROOT).returncode == 0
    backup_log = StringIO(); call_command('snapshot_db', output=str(backup), stdout=backup_log)
    with (HERE / 'backup_command.txt').open('x') as stream:
        stream.write(backup_log.getvalue())
    b = helpers.ro(backup)
    assert b.execute('PRAGMA integrity_check').fetchone()[0] == 'ok' and not b.execute('PRAGMA foreign_key_check').fetchall()
    baseline = helpers.snapshot(b); b.close()
    live = helpers.ro(ROOT / 'db.sqlite3'); current_snapshot = helpers.snapshot(live); live.close()
    assert current_snapshot['schema_digest'] == baseline['schema_digest']
    for table, state in baseline['tables'].items():
        if table != 'django_session':
            assert current_snapshot['tables'][table] == state, 'Backup/live non-session mismatch'
    after_backup_state = verify_reconciled_state('after_backup')
    current_hash = after_backup_state['current_file_sha256']
    code = ['reference/models.py', 'reference/ingestion/importing/matrix_workflow.py',
            'reference/ingestion/importing/workflow.py', 'reference/ingestion/importing/planner.py',
            'reference/ingestion/importing/powertrain_identity.py', 'reference/ingestion/matrix.py',
            'reference/ingestion/matrix_approval.py', 'reference/ingestion/contracts.py',
            'reference/ingestion/generation_correspondence.py', 'reference/ingestion/classification_adjudication.py']
    save(HERE / 'preservation_baseline.json', {'preexisting_handoff_files': files, 'database_before_sha256': current_hash,
         'snapshot': baseline, 'code_and_contract_hashes': {p: sha(ROOT / p) for p in code},
         'backup': {'path': rel(backup), 'sha256': sha(backup), 'integrity': 'ok', 'foreign_keys': 'passed',
                    'all_non_session_table_match': True, 'session_state_independently_verified': True},
         'reconciled_baseline_reference': rel(BASELINE_FILE), 'reconciled_baseline_file_sha256': sha(BASELINE_FILE)})
    git = subprocess.run(['git', 'status', '--short'], cwd=ROOT, capture_output=True, text=True, check=True)
    save(HERE / 'preflight.json', {'result': 'passed before any canonical execution', 'recorded_at': datetime.now(timezone.utc).isoformat(),
         'authorized_matrix_digest': EXPECTED, 'certified_approval': rel(PLANNING / 'matrix_approval.json'),
         'certified_approval_sha256': sha(PLANNING / 'matrix_approval.json'), 'planning_manifest_sha256': sha(PLANNING / 'artifact_hashes.json'),
         'scope': {'candidates': 73, 'two_door': 23, 'four_door': 50, 'labels': 24, 'expected_creations': 73, 'expected_no_ops': 0,
                   'generation_PK': 32, 'generation_uuid': str(gen.uuid), 'year': 2021, 'market': 'US'},
         'counts_before': counts, 'candidate_snapshot_plan_rechecks': snapshots, 'anticipated_creation_bases': creation_bases,
         'certified_live_status': status, 'prior_88_classification_decisions_and_392_fuel_approval': 'unchanged',
         'RHD_CLASS075': 'excluded/preserved/deferred', 'Django_check': check.getvalue().strip(),
         'git_status_before_execution': git.stdout, 'backup': load(HERE / 'preservation_baseline.json')['backup'],
         'authority': 'Current explicit project-owner authorization for this exact certified digest,73 new records and73 corresponding import receipts only',
         'execution_confirmation_authorized': 'yes to existing execute_generation_trim_matrix_year prompt only; project_owner/codex',
         'execution_method': 'Accepted durable model-year transaction, fresh plan/manifest per row, stale-plan guards and precommit reconciliation; no sequential reuse of standalone snapshots'})
    save(HERE / 'reconciled_authorization.json', {'authority': 'Current explicit owner resumption authorizes exactly73 certified MY2021 creations; verified ordinary session-only differences may be accepted',
         'matrix_digest': EXPECTED, 'accepted_reconciliation_baseline': rel(BASELINE_FILE), 'baseline_file_sha256': sha(BASELINE_FILE),
         'canonical_data_changes_tolerated_before_execution': False, 'application_contract_changes': False,
         'scope': {'creates':73,'two_door':23,'four_door':50,'expected_no_ops':0,'generation_PK':32},
         'stopped_preflight_record_preserved': rel(HERE.parent/'README.md')})
    save(HERE / 'environment.json', {'python': sys.version, 'interpreter': sys.executable,
         'Django': importlib.metadata.version('Django'), 'pypdf': importlib.metadata.version('pypdf'),
         'requirements': requirements, 'requirements_match': True})
    connection.close()
    print('PREFLIGHT AND BACKUP PASSED:73eligible creates;exact certified digest;no discrepancies;', rel(backup), flush=True)


def execute():
    assert not (HERE / 'execution_command_result.json').exists(), 'Execution already attempted; reconcile rather than retry blindly'
    pre = load(HERE / 'preflight.json'); baseline = load(HERE / 'preservation_baseline.json')
    assert pre['result'] == 'passed before any canonical execution'
    unchanged_files()
    verify_reconciled_state('before_execution_recheck')
    assert helpers.counts() == pre['counts_before']
    matrix, approval, rows, candidates = inputs()
    assert MatrixYear(matrix, approval, 2021, candidates).status()['counts'] == {'pending_create': 73}
    verify_reconciled_state('before_execution_launch')
    attempt_root = HERE / 'attempts'; attempt_root.mkdir(exist_ok=True)
    command = [str(ROOT / '.venv/bin/python'), '-B', str(ROOT / 'manage.py'), 'execute_generation_trim_matrix_year',
               '--matrix', rel(PLANNING / 'matrix_2_1.json'), '--approval', rel(PLANNING / 'matrix_approval.json'), '--year', '2021']
    for row in sorted(rows, key=lambda r: r['research_row_id']):
        command.extend(['--candidate', row['candidate_artifact']])
    command.extend(['--operator', 'project_owner', '--agent', 'codex', '--output-dir', rel(attempt_root), '--skip-checks'])
    env = os.environ.copy(); env.pop('RIGARCHIVE_TEST_DB_PATH', None)
    print('STARTING ACCEPTED ATOMIC EXECUTION;fresh per-row transaction plans;73expected creations;no no-ops', flush=True)
    with (HERE / 'execution_cli.txt').open('x') as log:
        result = subprocess.run(command, input='yes\n', text=True, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT, env=env, timeout=3600)
    save(HERE / 'execution_command_result.json', {'command': command, 'exit_code': result.returncode,
         'matrix_digest': EXPECTED, 'approval_sha256': sha(PLANNING / 'matrix_approval.json'),
         'affirmative_confirmation': 'Explicit current owner authorization for exact certified digest supplied to unchanged CLI',
         'standalone_snapshots_executed': False, 'accepted_atomic_Matrix_workflow': True})
    if result.returncode != 0:
        live = helpers.ro(ROOT / 'db.sqlite3'); actual = helpers.snapshot(live); live.close()
        save(HERE / 'execution_failure_reconciliation.json', {'CLI_exit_code': result.returncode,
             'entire_database_logically_matches_preimport_snapshot': actual == baseline['snapshot'],
             'counts_now': helpers.counts(), 'attempts': [rel(p) for p in attempt_root.iterdir() if p.is_dir()],
             'no_retry_or_restore_performed': True})
        raise RuntimeError('Execution failed or reporting incomplete; inspect retained attempt and reconcile before any retry')
    attempts = [p for p in attempt_root.iterdir() if p.is_dir()]
    assert len(attempts) == 1
    attempt = attempts[0]; report = load(attempt / 'result.json')
    assert report['matrix_digest'] == EXPECTED and report['authorized_count'] == 73 and report['complete']
    assert report['counts'] == {'newly_created': 73}, 'Actual scope differs; stop and report'
    assert compute_matrix_digest(load(attempt / 'matrix.json')) == EXPECTED
    assert load(attempt / 'approval.json') == approval
    save(HERE / 'committed_execution.json', {'status': 'committed through accepted atomic Matrix workflow',
         'matrix_digest': EXPECTED, 'attempt_directory': rel(attempt), 'created': 73, 'no_ops': 0,
         'accepted_workflow_result': report})
    connection.close()
    print('COMMITTED:73new VehicleDefinitions/73receipts;one accepted atomic model-year transaction', flush=True)


def verify():
    from uuid import UUID
    matrix, approval, rows, candidates = inputs()
    baseline = load(HERE / 'preservation_baseline.json'); committed = load(HERE / 'committed_execution.json')
    attempt = ROOT / committed['attempt_directory']
    unchanged_files()
    reconciliation = MatrixYear(matrix, approval, 2021, candidates).status()
    assert reconciliation['complete'] and reconciliation['counts'] == {'previously_completed': 73}
    save(HERE / 'matrix_reconciliation.json', reconciliation)
    new = list(VehicleDefinition.objects.filter(generation_id=32, model_year=2021, market='US').order_by('pk'))
    assert len(new) == 73 and helpers.counts() == {'VehicleDefinitions': 934, 'audit_receipts': 3148, 'correspondences': 159}
    assert len({r.slug for r in new}) == len({str(r.uuid) for r in new}) == 73
    pubs = load(PUBLICATION / 'publication_results.json')['results']
    mapped = []; receipts_used = []; bases = []; targets_seen = set(); earlier = []
    source_rows = {r['research_row_id']: r for r in rows}
    for n, mr in enumerate(sorted(matrix['rows'], key=lambda r: r['row_id'])):
        rid = mr['row_id']; record = next(r for r in new if r.slug == mr['target_slug'])
        assert str(UUID(str(record.uuid))) == str(record.uuid) and record.build_slug() == record.slug
        assert record.generation_id == 32 and record.is_active and record.model_year == 2021 and record.market == 'US'
        for k in BASE_FIELDS:
            assert getattr(record, k) == mr['target_fields'][k]
        values = record_powertrain(record)
        assert values == {k: mr['target_fields'][k] for k in FIELDS} == candidates[rid].canonical_powertrain
        record.clean()
        semantic = (record.trim_name, record.drivetrain, record.market, tuple(values[k] for k in FIELDS))
        assert semantic not in targets_seen; targets_seen.add(semantic)
        receipt = ImportExecutionReceipt.objects.get(created_vehicle_definition=record, execution_outcome='created', operation_type='vehicle_definition_import')
        assert receipt.operator_label == 'project_owner' and receipt.candidate_reference == mr['candidate_reference']
        assert receipt.target_fields_json == mr['target_fields'] and receipt.resolved_generation_id == 32
        assert receipt.created_vehicle_definition_pk_snapshot == record.pk
        assert str(receipt.created_vehicle_definition_uuid_snapshot) == str(record.uuid) and receipt.created_vehicle_definition_slug_snapshot == record.slug
        snapshot = receipt.resolution_snapshot_json; resolution = snapshot['generation_resolution']; link = snapshot['matrix']
        assert link['matrix_digest'] == EXPECTED and link['row_id'] == rid and link['model_year'] == 2021
        assert link['approval_digest'] == reconciliation['approval_digest']
        assert link['generation_binding'] == reconciliation['rows'][n]['generation_binding']
        assert resolution['resolution_version'] == '1.1' and resolution['parents']['generation_id'] == 32
        assert resolution['parents']['generation_uuid'] == '38d3c3ac-f825-4406-abb5-c2d12b9129a4'
        assert resolution['engine_distinction']['version'] == '2.0' and resolution['engine_distinction']['canonical_powertrain'] == values
        assert {c['uuid']: c['hash'] for c in resolution['correspondences']} == {p['revision_uuid']: p['content_hash'] for p in pubs if rid in p['candidate_references']}
        validate_documents(resolution['documents'], verify_bytes=True)
        assert snapshot['candidate_hash'] == mr['candidate_digest']
        path = attempt / f'{n:04d}.manifest.json'
        manifest = dict_to_manifest(load(path)); assert manifest.manifest_hash == receipt.manifest_hash
        plan = manifest.plans[0]
        assert plan.candidate_snapshot == candidate_config_doc_to_dict(candidates[rid])
        assert plan.generation_resolution == resolution and plan.candidate_hash == mr['candidate_digest']
        assert plan.target_slug == record.slug and plan.create_basis in mr['permitted_create_bases'] and plan.planned_action == 'create'
        assert plan.namespace_snapshot_count == n
        expected_peers = [r for r in earlier if r['trim_name'] == record.trim_name]
        assert len(plan.generation_resolution['engine_distinction']['peers']) == len(expected_peers)
        assert {p['record_pk'] for p in plan.generation_resolution['engine_distinction']['peers']} == {r['VehicleDefinition_PK'] for r in expected_peers}
        assert snapshot['attribution']['execution_agent'] == 'codex'
        bases.append(plan.create_basis); receipts_used.append(receipt.pk)
        mapped.append({'row_id': rid, 'candidate_reference': mr['candidate_reference'],
             'candidate_artifact': source_rows[rid]['candidate_artifact'], 'candidate_digest': mr['candidate_digest'],
             'body_style': source_rows[rid]['body_style'], 'model_code': source_rows[rid]['model_code'],
             'VehicleDefinition_PK': record.pk, 'UUID': str(record.uuid), 'slug': record.slug,
             'generation_PK': 32, 'target_fields': mr['target_fields'], 'canonical_powertrain': values,
             'receipt_PK': receipt.pk, 'receipt_UUID': str(receipt.uuid),
             'fresh_execution_manifest': rel(path), 'execution_manifest_hash': manifest.manifest_hash,
             'execution_manifest_file_sha256': sha(path), 'creation_basis': plan.create_basis,
             'namespace_count_at_creation': plan.namespace_snapshot_count,
             'same_trim_peers_at_creation': len(expected_peers), 'matrix_digest': EXPECTED,
             'published_correspondence_UUIDs': [x['uuid'] for x in resolution['correspondences']]})
        earlier.append({'trim_name': record.trim_name, 'VehicleDefinition_PK': record.pk})
    assert len(set(receipts_used)) == 73
    assert Counter(bases) == {'first_representation': 1, 'source_established_grade': 23, 'mechanical_dimension': 49}
    assert Counter(r['body_style'] for r in mapped) == {'2-door': 23, '4-door': 50}
    assert len({r['target_fields']['trim_name'] for r in mapped}) == 24
    live = helpers.ro(ROOT / 'db.sqlite3'); after = helpers.snapshot(live)
    tables = reconcile_preserving_authentication(baseline['snapshot'], after, {'reference_vehicledefinition': 73, 'reference_importexecutionreceipt': 73})
    assert live.execute('PRAGMA integrity_check').fetchone()[0] == 'ok' and not live.execute('PRAGMA foreign_key_check').fetchall()
    live.close(); unchanged_files()
    check = StringIO(); call_command('check', stdout=check); connection.close()
    save(HERE / 'candidate_to_canonical_mapping.json', {'matrix_digest': EXPECTED, 'created': 73, 'rows': mapped})
    save(HERE / 'verification.json', {'result': 'passed', 'certified_matrix_digest': EXPECTED,
         'new_VehicleDefinitions': 73, 'new_execution_receipts': 73,
         'VehicleDefinition_PKs': [r.pk for r in new], 'receipt_PKs': sorted(receipts_used),
         'body_distribution': {'2-door': 23, '4-door': 50}, 'approved_labels': 24,
         'all_five_fields_evidence_and_adjudication_lineage': 'passed', 'actual_creation_basis_counts': dict(Counter(bases)),
         'all_861_preexisting_VehicleDefinitions_unchanged': True, 'all_159_correspondences_unchanged': True,
         'all_preexisting_non_session_database_rows_unchanged': True,
         'all_preexisting_database_rows_unchanged': all(r['all_preexisting_rows_unchanged'] for r in tables.values()),
         'local_authentication_state_preserved': True, 'schema_unchanged': True, 'table_reconciliation': tables,
         'post_counts': helpers.counts(), 'unique_new_UUIDs_slugs_and_identities': 73,
         'Matrix_receipt_reconciliation': '73previously_completed;complete;no import replay',
         'SQLite_integrity': 'ok', 'foreign_key_violations': 0, 'Django_check': check.getvalue().strip(),
         'backup': baseline['backup'], 'backup_unchanged': True,
         'database_before_sha256': baseline['database_before_sha256'], 'database_after_sha256': sha(ROOT / 'db.sqlite3'),
         'preexisting_handoff_files_preserved': len(baseline['preexisting_handoff_files']),
         'RHD_CLASS075': 'unchanged/excluded/deferred', 'no_other_imports_backfills_migrations_or_code_contract_changes': True})
    print('VERIFIED:73created;73receipts;934definitions/3148receipts/159correspondences;all preexisting rows unchanged', flush=True)


if __name__ == '__main__':
    {'preflight': preflight, 'execute': execute, 'verify': verify}[sys.argv[1]]()
