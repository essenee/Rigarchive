"""Read-only canonical planning and local Matrix certification; never execution.

Both stages use live SQLite mode=ro/query_only. Certification writes only an
existing-format local approval artifact under explicit current owner authority.
"""
import copy
import hashlib
import importlib.metadata
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
LATEST = BASE / 'fuel_completion_20261109'
PUBLICATION = BASE / 'generation_publication_20261109'
ROOT = next(p for p in HERE.parents if (p / 'manage.py').is_file())
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
from django.conf import settings
settings.DATABASES['default']['NAME'] = 'file:' + str(ROOT / 'db.sqlite3') + '?mode=ro'
settings.DATABASES['default']['OPTIONS'] = {'uri': True}
import django
django.setup()
from django.db import connection
from django.core.management import call_command
from reference.models import Generation, GenerationCorrespondenceRevision as Revision, ImportExecutionReceipt, VehicleDefinition
from reference.ingestion.generation_correspondence import digest, revalidate_resolution
from reference.ingestion.serialization import serialize_artifact, deserialize_artifact, adjudication_from_dict
from reference.ingestion.importing.powertrain_identity import identity_proof
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.importing.matrix_workflow import _identity, _references, MatrixYear
from reference.ingestion.manifest import dict_to_manifest, manifest_to_dict, reconstruct_plan_from_manifest
from reference.ingestion.matrix import validate_matrix, canonical_matrix_payload, compute_matrix_digest
from reference.ingestion.matrix_approval import read_matrix_approval, serialize_matrix_approval
from reference.powertrain import FIELDS
from docs.implementation.handoffs.MY2021_JL.generation_publication_20261109 import publish_atomic as previous

connection.cursor().execute('PRAGMA query_only=ON')
NOW = datetime.now(timezone.utc).isoformat()


def load(p):
    return json.loads(p.read_text())


def sha(p):
    return 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p):
    return str(p.relative_to(ROOT))


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def textsave(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x') as stream:
        stream.write(value)


def unchanged():
    b = load(HERE / 'preservation.json')
    assert sha(ROOT / 'db.sqlite3') == b['database_sha256_before'], 'Database bytes changed during task'
    for p, h in b['preexisting_handoff_files'].items():
        assert sha(ROOT / p) == h, p
    for p, h in b['code_and_contract_hashes'].items():
        assert sha(ROOT / p) == h, p
    assert previous.counts() == b['database_counts']


def build():
    assert not (HERE / 'preservation.json').exists(), 'Preserve existing planning checkpoint'
    assert sys.version_info[:3] == (3, 13, 1)
    for requirement in (ROOT / 'requirements.txt').read_text().splitlines():
        package, version = requirement.split('=='); assert importlib.metadata.version(package) == version
    for folder in (LATEST, PUBLICATION):
        for p, h in load(folder / 'artifact_hashes.json').items():
            assert sha(folder / p) == h, p
    count = previous.counts()
    assert count == {'VehicleDefinitions': 861, 'audit_receipts': 3075, 'correspondences': 159}
    gen = Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32, uuid='38d3c3ac-f825-4406-abb5-c2d12b9129a4')
    vm = gen.vehicle_model
    assert gen.is_active and vm.is_active and vm.manufacturer.is_active
    assert (gen.name, vm.name, vm.manufacturer.name) == ('JL', 'Wrangler', 'Jeep')
    connection.ensure_connection()
    current_snapshot = previous.snapshot(connection.connection)
    historical = load(PUBLICATION / 'preservation_baseline.json')['database_snapshot']
    drift = []
    additions = {'reference_generationcorrespondencerevision': 95, 'reference_importexecutionreceipt': 95}
    assert current_snapshot['schema_digest'] == historical['schema_digest']
    for name, old in historical['tables'].items():
        new = current_snapshot['tables'][name]
        changed = sum(new['rows'].get(k) != value for k, value in old['rows'].items())
        assert new['count'] - old['count'] == additions.get(name, 0)
        if changed:
            assert name == 'django_session' and changed == 1, 'Unexpected canonical/state drift: ' + name
            drift.append({'table': name, 'changed_existing_rows': changed, 'row_contents_or_identifiers_reported': False})
    files = {rel(p): sha(p) for p in BASE.rglob('*') if p.is_file() and not p.is_relative_to(HERE)}
    protected = ['reference/ingestion/matrix.py', 'reference/ingestion/matrix_approval.py',
                 'reference/ingestion/importing/matrix_workflow.py', 'reference/ingestion/importing/planner.py',
                 'reference/ingestion/importing/powertrain_identity.py', 'reference/ingestion/manifest.py',
                 'reference/ingestion/generation_correspondence.py', 'reference/ingestion/classification_adjudication.py',
                 'reference/ingestion/contracts.py', 'reference/models.py']
    save(HERE / 'preservation.json', {'database_sha256_before': sha(ROOT / 'db.sqlite3'), 'database_counts': count,
         'preexisting_handoff_files': files, 'code_and_contract_hashes': {p: sha(ROOT / p) for p in protected},
         'read_only_access': 'SQLite URI mode=ro plus query_only=ON',
         'historical_publication_database_hash': load(PUBLICATION / 'postpublication_verification.json')['database_after_sha256'],
         'intervening_drift': drift, 'intervening_canonical_or_schema_drift': False,
         'session_drift_handling': 'Preexisting session update only; no session contents or identifiers reported and no session row changed by this task; fresh current byte hash is the task baseline',
         'candidate_index': rel(LATEST / 'current_candidate_index.json'), 'candidate_index_sha256': sha(LATEST / 'current_candidate_index.json')})
    save(HERE / 'environment.json', {'interpreter': sys.executable, 'python': sys.version,
         'Django': django.get_version(), 'pypdf': importlib.metadata.version('pypdf'),
         'requirements': (ROOT / 'requirements.txt').read_text().splitlines(), 'requirements_match': True})
    rows, candidates, required = previous.candidates()
    published = load(PUBLICATION / 'publication_results.json')['results']
    assert len(published) == len(required) == 95
    for item in published:
        r = Revision.objects.get(pk=item['revision_PK'], uuid=item['revision_uuid'])
        r.clean(); assert r.content_hash == digest(r.review_payload()) == item['content_hash'] and r.generation_id == 32
        assert r.start_year == r.end_year == 2021 and r.market == 'US'
        receipt = ImportExecutionReceipt.objects.get(pk=item['receipt_PK'], correspondence_revision=r)
        assert receipt.execution_outcome == 'created' and receipt.operation_type == 'correspondence_publication'
        assert receipt.manifest_hash == r.content_hash and receipt.resolution_snapshot_json['review'] == r.review_payload()
    namespace = list(VehicleDefinition.objects.filter(generation=gen, model_year=2021, market='US').order_by('pk'))
    namespace_records = [{**_identity(r), 'is_active': r.is_active, 'trim_name': r.trim_name, 'drivetrain': r.drivetrain} for r in namespace]
    save(HERE / 'canonical_namespace_snapshot.json', {'generation_PK': 32, 'model_year': 2021, 'market': 'US',
         'all_active_and_inactive_records': namespace_records, 'count': len(namespace), 'counts_are_observed_not_assumed': True})
    # Current namespace was independently inspected; a new record would require
    # reassessment, never forced creates or mutation of an existing record.
    assert not namespace, 'Namespace changed since inspection; reassess exact plan outcomes'
    plans = []; matrixrows = []; proofs = []; peers = []; basis_review = []
    bytrim = defaultdict(list); identities = set(); slugs = set(); used = set(); claim_count = 0
    outcomes = Counter(); raw_plans = {}
    print('PREFLIGHT PASSED:73 current candidates;95 actual published mappings;observed canonical namespace0', flush=True)
    for number, row in enumerate(sorted(rows, key=lambda r: r['research_row_id']), 1):
        rid = row['research_row_id']; c = candidates[rid]
        manifest_path = HERE / 'manifests' / (rid + '.manifest.2.1.json')
        manifest_path.parent.mkdir(exist_ok=True)
        log = StringIO()
        call_command('plan_canonical_import', candidate=row['candidate_artifact'], output=rel(manifest_path), stdout=log, skip_checks=True)
        textsave(HERE / 'planning_logs' / (rid + '.txt'), log.getvalue())
        raw = load(manifest_path); manifest = dict_to_manifest(raw)
        assert raw['manifest_version'] == '2.1' and manifest_to_dict(manifest) == raw and len(manifest.plans) == 1
        plan = reconstruct_plan_from_manifest(manifest.plans[0])
        fresh = plan_candidate_import(c)
        assert asdict(fresh) == asdict(plan), 'Fresh planning differs: ' + rid
        eligibility = plan.eligibility_status.value; action = plan.planned_action.value
        outcomes[(eligibility, action)] += 1
        raw_plans[rid] = plan
        if eligibility != 'eligible' or action not in {'create', 'no_op_exact_match'}:
            plans.append({'row_id': rid, 'manifest': rel(manifest_path), 'manifest_hash': manifest.manifest_hash,
                          'eligibility': eligibility, 'planned_action': action, 'reasons': plan.reasons})
            continue
        revalidate_resolution(plan)
        assert plan.resolved_generation_id == 32 and plan.resolved_vehicle_model_id == vm.pk and plan.resolved_manufacturer_id == vm.manufacturer_id
        resolution = plan.generation_resolution
        assert resolution['resolution_version'] == '1.1' and resolution['basis'] == 'reviewed_source_correspondence'
        assert resolution['parents']['generation_uuid'] == str(gen.uuid)
        expected = {p['revision_uuid']: p['content_hash'] for p in published if rid in p['candidate_references']}
        assert {r['uuid']: r['hash'] for r in resolution['correspondences']} == expected
        used.update(expected)
        proof = resolution['engine_distinction']
        assert proof['version'] == '2.0' and proof['canonical_powertrain'] == c.canonical_powertrain
        assert proof == identity_proof(c, []) and proof['peers'] == []
        human = [d for d in c.evidence_documents if d['source_id'] == 'human_classification_adjudication']
        claims = {}
        if human:
            assert len(human) == 1 and human[0]['raw_artifact_reference'] == row['approved_adjudication']
            adj = adjudication_from_dict(load(ROOT / row['approved_adjudication']))
            assert adj.adjudication_hash == row['approved_adjudication_hash']
            claims = adj.evidence_anchors['classifications']; claim_count += len(claims)
            assert all(v['confidence'] == 'moderate' and v['limitations'] and v['reasoning'] and v['source_assertion_refs'] for v in claims.values())
        else:
            assert row['engine_code'] == 'ECX'
        fields = plan.target_vehicle_definition_fields
        assert fields['trim_name'] == row['marketed_trim_proposal']
        identity = (fields['trim_name'], fields['drivetrain'], fields['market'], tuple(fields[k] for k in FIELDS))
        assert identity not in identities and plan.target_slug not in slugs
        identities.add(identity); slugs.add(plan.target_slug)
        assert not VehicleDefinition.objects.filter(generation=gen, slug=plan.target_slug).exists()
        assert action == 'create' and plan.existing_vehicle_definition_id is None
        assert plan.create_basis.value == 'first_representation' and plan.namespace_snapshot_count == 0
        prior = bytrim[fields['trim_name']]
        assert all(p['canonical_powertrain'] != c.canonical_powertrain for p in prior)
        anticipated = 'first_representation' if number == 1 else 'mechanical_dimension' if prior else 'source_established_grade'
        permitted = sorted({'first_representation', anticipated})
        evidence_refs, correspondence_refs = _references(plan)
        matrixrows.append({'row_id': rid, 'model_year': 2021, 'target_fields': fields, 'target_slug': plan.target_slug,
             'action': 'create', 'permitted_create_bases': permitted, 'candidate_reference': c.candidate_reference,
             'candidate_digest': plan.candidate_hash, 'evidence': evidence_refs, 'correspondence': correspondence_refs,
             'existing_record': None, 'generation_binding': {'mode': 'explicit_correspondence', 'strategy': 'reviewed_source_correspondence', 'resolution_version': '1.1'}})
        proof_path = HERE / 'engine_proofs' / (rid + '.engine_proof.2.0.json')
        resolution_path = HERE / 'resolutions' / (rid + '.resolution.1.1.json')
        save(proof_path, proof); save(resolution_path, resolution)
        proof_record = {'row_id': rid, 'engine_code': row['engine_code'], 'candidate_digest': plan.candidate_hash,
             'proof_artifact': rel(proof_path), 'proof_content_digest': digest(proof), 'proof_file_sha256': sha(proof_path),
             'classification_basis': 'human_adjudication_plus_direct_sources' if human else 'direct_technical_sources',
             'approved_adjudication': row.get('approved_adjudication'), 'approved_adjudication_hash': row.get('approved_adjudication_hash'),
             'approved_claims': claims, 'human_evidence_document': human,
             'direct_fields': [k for k in FIELDS if k not in claims],
             'original_source_lineage': c.unknown_fields['research_revision_lineage']}
        proofs.append(proof_record)
        peers.append({'row_id': rid, 'resolution_artifact': rel(resolution_path), 'resolution_content_digest': digest(resolution),
             'resolution_file_sha256': sha(resolution_path), 'target': resolution['parents'], 'canonical_peers': proof['peers'],
             'existing_record_PK': plan.existing_vehicle_definition_id, 'namespace_snapshot_count': plan.namespace_snapshot_count,
             'eligibility': eligibility, 'planned_action': action})
        basis_review.append({'row_id': rid, 'snapshot_basis': plan.create_basis.value, 'namespace_snapshot_count': 0,
             'anticipated_basis_in_fixed_row_order': anticipated, 'permitted_create_bases': permitted,
             'earlier_same_trim_rows': [p['row_id'] for p in prior], 'approved_five_field_tuples_are_distinct': True})
        prior.append({'row_id': rid, 'canonical_powertrain': c.canonical_powertrain})
        plans.append({'row_id': rid, 'body_style': row['body_style'], 'trim_name': fields['trim_name'], 'engine_code': row['engine_code'],
             'candidate_artifact': row['candidate_artifact'], 'candidate_digest': plan.candidate_hash, 'candidate_file_sha256': row['artifact_sha256'],
             'manifest': rel(manifest_path), 'manifest_hash': manifest.manifest_hash, 'manifest_file_sha256': sha(manifest_path),
             'eligibility': eligibility, 'planned_action': action, 'current_create_basis': plan.create_basis.value,
             'target_slug': plan.target_slug, 'target_fields': fields, 'engine_proof': rel(proof_path),
             'resolution': rel(resolution_path), 'correspondences': resolution['correspondences'],
             'evidence_references': evidence_refs, 'approved_adjudication': row.get('approved_adjudication')})
        print('PLANNED', number, '/73', rid, eligibility, action, flush=True)
    if len(matrixrows) != 73:
        save(HERE / 'blocked_planning_report.json', {'outcomes': [{'eligibility': k[0], 'action': k[1], 'count': n} for k, n in outcomes.items()], 'plans': plans, 'certification': 'not performed'})
        raise RuntimeError('Blocked or conflicting rows; preserve report and stop before Matrix certification')
    assert claim_count == 89 and len(used) == 95
    matrix = canonical_matrix_payload({'matrix_version': '2.1',
        'parents': {'manufacturer': _identity(vm.manufacturer), 'vehicle_model': _identity(vm), 'generation': _identity(gen)},
        'market': 'US', 'model_years': [2021], 'rows': matrixrows})
    validate_matrix(matrix)
    md = compute_matrix_digest(matrix)
    save(HERE / 'matrix_2_1.json', matrix)
    assert compute_matrix_digest(load(HERE / 'matrix_2_1.json')) == md
    assert canonical_matrix_payload(json.loads(json.dumps(matrix, ensure_ascii=False))) == matrix
    save(HERE / 'plan_index.json', {'created_at': NOW, 'matrix_digest': md, 'manifest_version': '2.1', 'plans': plans})
    save(HERE / 'engine_proof_index.json', {'version': '2.0', 'complete': 73, 'original_88_decisions_preserved': True,
         'additional_392_fuel_decision_preserved': True, 'distinct_human_field_claims': 89, 'direct_ECX_candidates': 3, 'rows': proofs})
    save(HERE / 'resolution_index.json', {'version': '1.1', 'actual_published_correspondence_state': True, 'rows': peers})
    save(HERE / 'canonical_peer_and_conflict_assessment.json', {'namespace_records': namespace_records,
         'eligible': 73, 'blocked': 0, 'conflicting': 0, 'preexisting': 0, 'expected_creations': 73, 'expected_no_ops': 0,
         'unique_target_identities': 73, 'unique_unoccupied_target_slugs': 73, 'current_canonical_peers': 0,
         'intra_set_duplicates': 0, 'actual_existing_records_checked_including_inactive': True, 'rows': peers})
    save(HERE / 'execution_scope_and_bases.json', {'matrix_digest': md, 'scope': '73 US MY2021 consumer rows only;23two-door/50four-door;24body/trim labels',
         'standalone_snapshot_basis_counts': {'first_representation': 73},
         'anticipated_transaction_basis_counts': dict(Counter(r['anticipated_basis_in_fixed_row_order'] for r in basis_review)),
         'notice': 'All snapshots bind the present empty namespace. They must not be executed sequentially unchanged. Any separately authorized Matrix execution must freshly replan each row in fixed row-ID order inside one model-year transaction, recomputing namespace counts and sibling receipt/evidence proofs. Anticipated bases are code/tuple analysis, not executed sibling proofs.',
         'execution_authorized': False, 'rows': basis_review})
    textsave(HERE / 'plan_hashes.md', '# MY2021 snapshot manifest hashes\n\nMatrix digest: `' + md + '`\n\nThese are read-only snapshot plans. Future execution requires separate authorization and fresh per-row Matrix planning.\n\n| Row | Manifest content hash |\n| --- | --- |\n' + '\n'.join('| ' + p['row_id'] + ' | `' + p['manifest_hash'] + '` |' for p in plans) + '\n')
    unchanged()
    save(HERE / 'planning_validation.json', {'result': 'passed', 'matrix_digest': md, 'candidate_count': 73,
         'distribution': {'2-door': 23, '4-door': 50}, 'approved_labels': 24, 'complete_engine_proofs_2_0': 73,
         'actual_published_resolutions_1_1': 73, 'published_correspondences_used': 95,
         'eligible': 73, 'blocked': 0, 'conflicting': 0, 'preexisting': 0, 'expected_creations': 73, 'expected_no_ops': 0,
         'manifest_round_trips_fresh_plan_matches_and_revalidations': 73, 'certification': 'next explicit stage',
         'database_unchanged': True, 'database_sha256': sha(ROOT / 'db.sqlite3'), 'execution_performed': False})
    connection.close()
    print('PLANNING VALIDATED:', md, '73 eligible creates;0 blocked/conflict/preexisting/noops;DB unchanged', flush=True)


def certify():
    unchanged()
    testlog = (HERE / 'focused_tests.txt').read_text()
    assert re.search(r'Ran 157 tests in ', testlog) and re.search(r'^OK$', testlog, re.M)
    matrix_path = HERE / 'matrix_2_1.json'; matrix = load(matrix_path)
    rows, candidates, _ = previous.candidates()
    c392 = candidates['JL21-70']
    assert c392.canonical_powertrain == {'engine_displacement_liters': '6.4', 'engine_cylinders': 8,
        'engine_aspiration': 'naturally_aspirated', 'fuel_type': 'gasoline', 'electrification_type': 'none'}
    source = next(d for d in c392.evidence_documents if d['source_id'] == 'FCA_MY2021_Wrangler_392_specifications')
    page = next(a for a in source['assertions'] if a['assertion_id'].endswith('-p1'))
    fuel_line = next(line for line in page['raw_value'].splitlines() if 'Fuel Requirement' in line)
    assert 'Premium 91 octane (R+M)/2' in fuel_line and 'required' in fuel_line
    ecx = []
    for row in rows:
        if row['engine_code'] == 'ECX':
            c = candidates[row['research_row_id']]
            assert c.canonical_powertrain == {'engine_displacement_liters': '2', 'engine_cylinders': 4,
                'engine_aspiration': 'turbocharged', 'fuel_type': 'gasoline', 'electrification_type': 'plug_in_hybrid'}
            assert not any(d['source_id'] == 'human_classification_adjudication' for d in c.evidence_documents)
            ecx.append(row['research_row_id'])
    save(HERE / '392_and_ECX_provenance_validation.json', {'Rubicon_392': {'candidate_reference': 'JL21-70',
         'canonical_powertrain': c392.canonical_powertrain, 'raw_fuel_grade_requirement': fuel_line,
         'fuel_grade_is_outside_five_field_identity': True, 'source_document': source['raw_artifact_reference'],
         'source_sha256': source['raw_artifact_hash'], 'source_assertion_id': page['assertion_id'],
         'classification': 'Approved human gasoline conclusion; source wording preserved; no new approval or normalization'},
         'ECX': {'candidate_references': ecx, 'five_fields': 'complete; gasoline PHEV', 'direct_technical_evidence_preserved': True}})
    output = HERE / 'matrix_approval.json'
    assert not output.exists(), 'Preserve existing certification; do not repeat'
    save(HERE / 'certification_authority.json', {'created_at': NOW,
         'authority': 'Current explicit owner task authorizes MY2021 Matrix2.1 certification and read-only canonical planning',
         'matrix_digest': compute_matrix_digest(matrix), 'row_count': 73,
         'conditions_verified': '73 current complete approved identities;23/50distribution;24labels;all95actual published bindings;73eligible;zero blocked/conflicting/preexisting;deterministic parent/plan/source pins',
         'affirmative_confirmation_authorized_for': 'approve_generation_trim_matrix only; operator project_owner, agent codex',
         'execution_authorized': False, 'canonical_execution_or_rehearsal_performed': False})
    log = StringIO()
    with patch('builtins.input', return_value='yes'):
        call_command('approve_generation_trim_matrix', matrix=rel(matrix_path), candidate=[r['candidate_artifact'] for r in rows],
                     operator='project_owner', agent='codex', output=rel(output), stdout=log, skip_checks=True)
    textsave(HERE / 'matrix_certification_cli.txt', log.getvalue())
    review, _ = json.JSONDecoder().raw_decode(log.getvalue())
    assert review['matrix_digest'] == compute_matrix_digest(matrix)
    assert review['validation'][0]['counts'] == {'pending_create': 73}
    save(HERE / 'matrix_review_at_certification.json', review)
    approval = read_matrix_approval(output, matrix)
    assert approval['decision'] == 'approved' and approval['operator'] == 'project_owner'
    assert output.read_bytes() == serialize_matrix_approval(matrix, approval)
    # Read-only status recomputes current plans with the certified scope/approval.
    status = MatrixYear(matrix, approval, 2021, candidates).status()
    assert status['counts'] == {'pending_create': 73} and status['approval_digest'] == sha(output)
    save(HERE / 'certified_matrix_status.json', status)
    check = StringIO(); call_command('check', stdout=check)
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA integrity_check'); assert cursor.fetchone()[0] == 'ok'
        cursor.execute('PRAGMA foreign_key_check'); assert cursor.fetchall() == []
    unchanged()
    save(HERE / 'matrix_certification_status.json', {'result': 'certified/approved under current owner authorization',
         'matrix_version': '2.1', 'matrix_digest': compute_matrix_digest(matrix), 'approval_artifact': rel(output),
         'approval_file_sha256': sha(output), 'approval': approval, 'certified_status_counts': status['counts'],
         'eligible': 73, 'blocked': 0, 'conflicting': 0, 'preexisting': 0, 'expected_creations': 73, 'expected_no_ops': 0,
         'engine_proof_version': '2.0', 'resolution_version': '1.1', 'actual_correspondence_revisions': 95,
         'Django_check': check.getvalue().strip(), 'SQLite_integrity': 'ok', 'foreign_key_violations': 0,
         'database_sha256_before_and_after': sha(ROOT / 'db.sqlite3'), 'database_unchanged': True,
         'execution_authorization': 'not granted; separate owner instruction required', 'execution_performed': False})
    connection.close()
    print('CERTIFIED:', compute_matrix_digest(matrix), '73pending_create;no execution;DB byte-identical', flush=True)


if __name__ == '__main__':
    {'build': build, 'certify': certify}[sys.argv[1]]()
