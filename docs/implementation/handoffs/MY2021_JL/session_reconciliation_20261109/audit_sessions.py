"""Read-only all-table/session audit; persist only redacted audit metadata.

No session save, database write, import, migration, backup restore or execution.
The Git database is deserialized only into memory. Raw session/account values
remain in memory for comparison and are never emitted into reports.
"""
import hashlib
import importlib.metadata
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = next(p for p in HERE.parents if (p / 'manage.py').is_file())
LIVE = ROOT / 'db.sqlite3'
PUB = BASE / 'generation_publication_20261109'
COMMIT_CHECKPOINT = ROOT / 'backups/review/MY2020_commit_checkpoint_20261109T025312470275Z'
BASELINE = ROOT / 'backups/review/MY2021_JL_correspondence_prepublication_20261109T154455104372Z.sqlite3'
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
from django.conf import settings
settings.DATABASES['default']['NAME'] = 'file:' + str(LIVE) + '?mode=ro'
settings.DATABASES['default']['OPTIONS'] = {'uri': True}
import django
django.setup()
from django.core import signing
from django.contrib.sessions.backends.db import SessionStore
from django.db import connection
from reference.models import Generation, GenerationCorrespondenceRevision as Revision, ImportExecutionReceipt, VehicleDefinition
from reference.ingestion.generation_correspondence import digest
from reference.ingestion.matrix import compute_matrix_digest


def load(p):
    return json.loads(p.read_text())


def save(p, value):
    with p.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def sha(p):
    return 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()


def value_hash(value):
    return digest(value)


def ro(p):
    c = sqlite3.connect('file:' + str(p) + '?mode=ro', uri=True)
    c.execute('PRAGMA query_only=ON')
    return c


def stamp(epoch):
    utc = datetime.fromtimestamp(epoch, timezone.utc)
    return {'UTC': utc.isoformat(), 'America_Los_Angeles': utc.astimezone(ZoneInfo('America/Los_Angeles')).isoformat()}


def metadata(p):
    s = p.stat()
    return {'absolute_path': str(p), 'sha256': sha(p), 'size_bytes': s.st_size,
            'modification_time': stamp(s.st_mtime),
            'filesystem_birth_time': stamp(s.st_birthtime) if hasattr(s, 'st_birthtime') else None}


def tables(c):
    result = {}
    for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
        q = '"' + name.replace('"', '""') + '"'
        info = c.execute('PRAGMA table_info(' + q + ')').fetchall()
        names = [r[1] for r in info]
        pk = [i for i, r in enumerate(info) if r[5]]
        if name == 'sqlite_sequence':
            pk = [names.index('name')]
        assert pk, 'No stable row identity: ' + name
        rows = {tuple(r[i] for i in pk): tuple(r) for r in c.execute('SELECT * FROM ' + q)}
        result[name] = {'columns': names, 'pk_columns': [names[i] for i in pk], 'rows': rows}
    return result


def safe_pk(table, columns, pk):
    if table == 'django_session':
        # Its primary key is an authentication token; never report it verbatim.
        return {'redacted': True, 'PK_fingerprint': value_hash(list(pk))}
    return dict(zip(columns, pk))


def compare(left, right):
    assert set(left) == set(right), 'Unexplained table inventory change'
    report = []
    for table in sorted(left):
        a, b = left[table], right[table]
        assert a['columns'] == b['columns'] and a['pk_columns'] == b['pk_columns'], 'Unexplained columns/PK change'
        added = sorted(b['rows'].keys() - a['rows'].keys())
        removed = sorted(a['rows'].keys() - b['rows'].keys())
        changed = []
        for pk in sorted(a['rows'].keys() & b['rows'].keys()):
            if a['rows'][pk] != b['rows'][pk]:
                changed.append({'primary_key': safe_pk(table, a['pk_columns'], pk),
                    'changed_columns': [name for n, name in enumerate(a['columns']) if a['rows'][pk][n] != b['rows'][pk][n]]})
        report.append({'table': table, 'baseline_count': len(a['rows']), 'live_count': len(b['rows']),
            'added_rows': [safe_pk(table, b['pk_columns'], pk) for pk in added],
            'deleted_rows': [safe_pk(table, a['pk_columns'], pk) for pk in removed], 'changed_rows': changed})
    return report


def schema(c):
    return c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_autoindex%' ORDER BY type,name").fetchall()


def main():
    assert not (HERE / 'execution_baseline.json').exists(), 'Preserve completed audit; no overwrite'
    before = metadata(LIVE)
    backup_meta = metadata(BASELINE)
    assert backup_meta['sha256'] == load(PUB / 'preservation_baseline.json')['backup']['sha256']
    live = ro(LIVE); old = ro(BASELINE)
    live.execute('BEGIN')  # Consistent read snapshot; never acquires a write transaction.
    old.execute('BEGIN')
    raw_git = subprocess.run(['git', 'show', 'HEAD:db.sqlite3'], cwd=ROOT, capture_output=True, check=True).stdout
    git_db = sqlite3.connect(':memory:'); git_db.deserialize(raw_git); git_db.execute('PRAGMA query_only=ON')
    commit_state = load(COMMIT_CHECKPOINT / 'state.json')
    git_hash = 'sha256:' + hashlib.sha256(raw_git).hexdigest()
    assert git_hash == commit_state['sanitized_sha256'] == sha(COMMIT_CHECKPOINT / 'sanitized.sqlite3')
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    git_date = subprocess.run(['git', 'log', '-1', '--format=%cI', '--', 'db.sqlite3'], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    a, b, committed = tables(old), tables(live), tables(git_db)
    assert schema(old) == schema(live) == schema(git_db), 'Unexplained schema difference'
    diff = compare(a, b)
    committed_diff = compare(committed, a)
    publication = load(PUB / 'publication_results.json')['results']
    assert len(publication) == 95
    correspondence_ids = {p['revision_PK'] for p in publication}
    receipt_ids = {p['receipt_PK'] for p in publication}
    unexpected = []
    for row in diff:
        t = row['table']
        if t == 'django_session':
            assert not row['added_rows'] and not row['deleted_rows'], 'New/deleted sessions require separate lifecycle assessment'
            assert all(set(r['changed_columns']) <= {'session_data', 'expire_date'} for r in row['changed_rows'])
            row['classification'] = 'session nature assessed separately; never assumed benign by table name'
        elif t in {'reference_generationcorrespondencerevision', 'reference_importexecutionreceipt'}:
            ids = correspondence_ids if t.endswith('generationcorrespondencerevision') else receipt_ids
            assert {r['id'] for r in row['added_rows']} == ids
            assert not row['changed_rows'] and not row['deleted_rows']
            row['classification'] = 'exact previously owner-authorized95 correspondence publication additions; not new unexplained drift'
        elif t == 'sqlite_sequence':
            assert not row['added_rows'] and not row['deleted_rows']
            assert {r['primary_key']['name'] for r in row['changed_rows']} == {'reference_generationcorrespondencerevision', 'reference_importexecutionreceipt'}
            for pk, values in a[t]['rows'].items():
                delta = b[t]['rows'][pk][1] - values[1]
                assert delta == (95 if pk[0] in {'reference_generationcorrespondencerevision', 'reference_importexecutionreceipt'} else 0)
            row['classification'] = 'two documented publication sequences advanced95; no other sequence changed'
        else:
            if row['added_rows'] or row['deleted_rows'] or row['changed_rows']:
                unexpected.append(row)
            row['classification'] = 'unchanged'
    assert not unexpected, 'Unexplained non-session application change; do not establish baseline'
    connection.cursor().execute('PRAGMA query_only=ON')
    published_checks = []
    start_time = datetime.fromisoformat(load(PUB / 'preflight.json')['recorded_at'])
    end_time = datetime.fromtimestamp((PUB / 'publication_results.json').stat().st_mtime + 2, timezone.utc)
    for item in publication:
        p = load(ROOT / item['proposal'])['review']
        r = Revision.objects.get(pk=item['revision_PK'], uuid=item['revision_uuid'])
        assert r.review_payload() == p and r.content_hash == digest(p) == item['content_hash'] and r.generation_id == 32
        receipt = ImportExecutionReceipt.objects.get(pk=item['receipt_PK'], uuid=item['receipt_uuid'], correspondence_revision=r)
        expected = {'operator_label': 'project_owner', 'operation_type': 'correspondence_publication',
            'execution_channel': 'cli', 'resolution_snapshot_json': {'review': p, 'content_hash': item['content_hash'], 'attribution': {'version': '1.0', 'execution_agent': 'codex'}},
            'manifest_hash': item['content_hash'], 'candidate_reference': p['revision_uuid'], 'planned_action': 'publish',
            'source_id': p['source_id'], 'raw_artifact_hash': p['evidence'][0]['raw_artifact_hash'],
            'raw_artifact_reference': p['evidence'][0]['raw_artifact_reference'], 'source_identity_type': p['identity_type'],
            'native_identifier': p['native_identifier'], 'execution_outcome': 'created', 'messages_json': [], 'target_slug': ''}
        for field in receipt._meta.concrete_fields:
            if field.name in {'id', 'uuid', 'created_at', 'updated_at', 'executed_at', 'correspondence_revision'}:
                continue
            value = getattr(receipt, field.attname)
            if field.name in expected:
                assert value == expected[field.name], 'Publication receipt field mismatch'
            elif field.has_default():
                assert value == field.get_default(), 'Publication receipt default mismatch'
            elif field.null:
                assert value is None, 'Unexpected publication receipt target'
            elif field.blank:
                assert value == '', 'Unexpected publication receipt text'
            else:
                raise AssertionError('Unassessed receipt field')
        for obj in (r, receipt):
            times = [obj.created_at, obj.updated_at] + ([obj.executed_at] if obj is receipt else [])
            assert all(start_time <= value <= end_time for value in times)
            assert (max(times) - min(times)).total_seconds() < 1
        published_checks.append({'revision_PK': r.pk, 'receipt_PK': receipt.pk, 'review_hash': r.content_hash,
            'approved_payload_and_receipt_lineage_match': True, 'nonpayload_fields_defaults_and_creation_window_verified': True})
    # Documented committed sanitization must explain every private-state delta.
    account_columns = set(a['accounts_user']['columns'])
    def documented_fields(value):
        if isinstance(value, str):
            return {value} if value in account_columns else set()
        if isinstance(value, list):
            return set().union(*(documented_fields(v) for v in value))
        if isinstance(value, dict):
            return (set(value) & account_columns) | set().union(*(documented_fields(v) for v in value.values()))
        return set()
    sanitized_fields = documented_fields(commit_state['account_fields_sanitized'])
    for row in committed_diff:
        if row['table'] == 'accounts_user':
            assert not row['added_rows'] and not row['deleted_rows']
            assert all(set(r['changed_columns']) <= sanitized_fields for r in row['changed_rows'])
            row['classification'] = 'previously documented committed-copy account sanitization; operational values unchanged from closest live backup'
        elif row['table'] == 'django_session':
            assert row['baseline_count'] == 0 and not row['deleted_rows'] and not row['changed_rows']
            row['classification'] = 'sessions deliberately removed only in documented committed sanitized copy'
        else:
            assert not row['added_rows'] and not row['deleted_rows'] and not row['changed_rows'], 'Unexplained committed/live-baseline difference'
            row['classification'] = 'unchanged'
    store = SessionStore()
    def decode_private_session(value):
        try:
            return signing.loads(value, salt=store.key_salt, serializer=store.serializer)
        except signing.BadSignature:
            # BadSignature messages may contain a signature fragment. Keep it
            # out of logs as well as structured reports.
            raise AssertionError('A retained session signature could not be verified; no baseline issued') from None
    generations = list(Generation.objects.select_related('vehicle_model__manufacturer'))
    by_url = {g.get_absolute_url(): g for g in generations}
    history_keys = {'manufacturer_name', 'model_name', 'generation_name', 'generation_number', 'year_span', 'url', 'image_url'}
    def validate_history(data):
        history = data.get('recently_viewed_generations', [])
        assert isinstance(history, list) and len(history) <= 5
        urls = []
        for item in history:
            assert isinstance(item, dict) and set(item) == history_keys and item['url'] in by_url
            g = by_url[item['url']]
            assert item['manufacturer_name'] == g.vehicle_model.manufacturer.name
            assert item['model_name'] == g.vehicle_model.name and item['generation_name'] == g.name
            assert item['generation_number'] == g.generation_number
            assert item['year_span'] == (f'{g.start_year}–{g.end_year}' if g.end_year else f'{g.start_year}–present')
            assert item['image_url'] is None or isinstance(item['image_url'], str)
            urls.append(item['url'])
        assert len(urls) == len(set(urls))
        return history
    sessions = []; session_baseline = []
    oldcols = a['django_session']['columns']; datapos = oldcols.index('session_data'); expirypos = oldcols.index('expire_date')
    for pk, new in b['django_session']['rows'].items():
        prior = a['django_session']['rows'][pk]
        before_data = decode_private_session(prior[datapos])
        after_data = decode_private_session(new[datapos])
        before_history = validate_history(before_data); after_history = validate_history(after_data)
        old_signed = signing.b62_decode(prior[datapos].rsplit(':', 2)[1]); new_signed = signing.b62_decode(new[datapos].rsplit(':', 2)[1])
        expiry = datetime.fromisoformat(new[expirypos]).replace(tzinfo=timezone.utc)
        old_expiry = datetime.fromisoformat(prior[expirypos]).replace(tzinfo=timezone.utc)
        changed = [k for k in sorted(set(before_data) | set(after_data)) if before_data.get(k) != after_data.get(k)]
        assert set(before_data) == set(after_data) and set(changed) <= {'recently_viewed_generations'}
        assert new_signed >= old_signed and expiry >= old_expiry
        if prior != new:
            assert 0 <= (expiry.timestamp() - new_signed) - settings.SESSION_COOKIE_AGE < 2
            assert 0 <= (old_expiry.timestamp() - old_signed) - settings.SESSION_COOKIE_AGE < 2
            sessions.append({'primary_key': safe_pk('django_session', ['session_key'], pk),
                'changed_columns': [k for n, k in enumerate(oldcols) if prior[n] != new[n]],
                'valid_signatures_before_and_after': True, 'decoded_keys_added': [], 'decoded_keys_removed': [],
                'decoded_keys_changed': changed, 'authentication_and_all_other_decoded_fields_unchanged': True,
                'history_entry_count_before': len(before_history), 'history_entry_count_after': len(after_history),
                'history_schema_limit_uniqueness_and_canonical_metadata_valid': True,
                'old_signed_time': stamp(old_signed), 'new_signed_time': stamp(new_signed),
                'old_expiry': old_expiry.isoformat(), 'new_expiry': expiry.isoformat(),
                'expiry_matches_normal_cookie_age_seconds': settings.SESSION_COOKIE_AGE,
                'classification': 'normal recently-viewed generation browsing write, session re-signing and expiry renewal; no auth-field change'})
        session_baseline.append({'PK_fingerprint': value_hash(list(pk)), 'row_digest': value_hash(list(new)),
            'decoded_non_history_digest': value_hash({k: v for k, v in after_data.items() if k != 'recently_viewed_generations'}),
            'decoded_key_names': sorted(after_data), 'history_digest': value_hash(after_history),
            'valid_signature_and_history_shape': True})
    assert len(sessions) == 1
    counts = {name: len(t['rows']) for name, t in b.items()}
    assert counts['reference_vehicledefinition'] == 861 and counts['reference_importexecutionreceipt'] == 3075 and counts['reference_generationcorrespondencerevision'] == 159
    assert not VehicleDefinition.objects.filter(generation_id=32, model_year=2021, market='US').exists()
    assert live.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not live.execute('PRAGMA foreign_key_check').fetchall()
    matrix = load(BASE / 'final_planning_20261109/matrix_2_1.json')
    md = compute_matrix_digest(matrix)
    assert md == 'sha256:6926df6c06e4bd471bbda02c67257cf7a7e2999cf5cdfebfc8b06ead31a9996e'
    # Full table/column fingerprints support the next read-only drift check
    # without retaining session contents, tokens or account credential values.
    fingerprint_tables = {}
    for name, table in b.items():
        row_digests = {}
        for pk, row in table['rows'].items():
            row_digests[value_hash(list(pk))] = {'row_digest': value_hash(list(row)),
                'column_digests': {column: value_hash(row[n]) for n, column in enumerate(table['columns'])}}
        fingerprint_tables[name] = {'count': len(table['rows']), 'columns': table['columns'],
            'primary_key_columns': table['pk_columns'], 'rows': row_digests, 'table_digest': digest(row_digests)}
    vd = b['reference_vehicledefinition']; vd_cols = vd['columns']
    canonical_identity = [[r[vd_cols.index(k)] for k in ('id', 'uuid', 'slug', 'generation_id', 'model_year', 'market')] for _, r in sorted(vd['rows'].items())]
    corr = b['reference_generationcorrespondencerevision']; cc = corr['columns']
    correspondence_identity = [[r[cc.index(k)] for k in ('id', 'uuid', 'generation_id', 'source_id', 'source_namespace', 'identity_type', 'native_identifier', 'market', 'start_year', 'end_year', 'content_hash')] for _, r in sorted(corr['rows'].items())]
    schema_digest_value = digest(schema(live))
    after = metadata(LIVE)
    assert before['sha256'] == after['sha256'] and before['size_bytes'] == after['size_bytes'], 'Live file changed during audit; no stable baseline can be issued'
    live.rollback(); old.rollback(); live.close(); old.close(); git_db.close(); connection.close()
    assert sha(LIVE) == before['sha256'], 'File changed after read snapshot; stop before baseline'
    save(HERE / 'database_metadata_and_baselines.json', {'live': before, 'closest_verified_physical_baseline': backup_meta,
        'closest_baseline_limit': 'Prepublication snapshot; the95correspondence and95receipt additions are separately reconciled to immutable approved publication records, never ignored as session drift',
        'historical_backup_inventory': [metadata(p) for p in sorted((ROOT / 'backups/review').rglob('*.sqlite3'), key=lambda p: p.stat().st_mtime, reverse=True)],
        'committed_checkpoint': {'HEAD': head, 'database_last_commit_date': git_date, 'database_sha256': git_hash, 'size_bytes': len(raw_git),
            'matches_documented_sanitized_copy': True, 'sanitization_record': str(COMMIT_CHECKPOINT / 'state.json'),
            'committed_session_count': len(committed['django_session']['rows']), 'operational_database_is_not_committed_snapshot': True},
        'earlier_file_hashes_without_matching_retained_physical_snapshot': {'planning': 'sha256:ecc521242b0d29b659a7195bbfbc498ed80c8f129c472ab9bf445461984520e2',
            'stopped_preflight': 'sha256:de2308f1c965899a40ee8dec9a66a47484241fb45515e9efd76b2f06b156036c'}})
    save(HERE / 'all_table_comparison.json', {'baseline': str(BASELINE), 'table_count': len(diff), 'tables': diff,
        'unexplained_non_session_changes': [], 'documented_publication_additions': {'correspondences': 95, 'receipts': 95},
        'private_primary_keys': 'Session keys are authentication tokens; SHA256 fingerprints replace actual values'})
    save(HERE / 'committed_sanitization_assessment.json', {'committed_sha256': git_hash, 'matches_documented_checkpoint': True,
        'documented_sanitized_account_columns': sorted(sanitized_fields), 'tables': committed_diff,
        'unexplained_differences': [], 'committed_snapshot_not_selected_as_operational_baseline': True})
    save(HERE / 'session_nature_assessment.json', {'session_count_before': 5, 'session_count_after': 5,
        'added_sessions': 0, 'deleted_sessions': 0, 'changed_sessions': 1, 'changes': sessions,
        'application_write_path': ['reference/views.py:GenerationHubView.get_context_data', 'reference/services.py:record_recently_viewed_generation'],
        'mechanism': 'Generation-page visits replace/bubble the recently-viewed entry, cap history at5 and set session.modified=True. Django re-signs modified session_data and renews normal expiry.',
        'normal_browsing_consistency': True, 'actor_or_individual_HTTP_request_attribution': 'not established; not required to validate the nature of changes',
        'precise_ECC_to_DE_hash_pair_reconstruction': False,
        'limitation': 'Neither intermediate file-hash state has a retained physical snapshot. The exact historical byte delta cannot be reconstructed; all-table preservation plus explicit publication reconciliation and signed-session nature establish the current verified state.'})
    save(HERE / 'documented_publication_reconciliation.json', {'records_verified': 95, 'checks': published_checks,
        'automatic_metadata_limit': 'The physical baseline predates these rows. Approved payloads/receipt lineage, recorded IDs/UUIDs, constructor defaults and original creation windows are verified; no historical full-row byte snapshot exists for the95new rows.'})
    save(HERE / 'execution_baseline.json', {'status': 'verified fresh operational baseline after session and documented-publication reconciliation',
        'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'live_database': before,
        'authorized_matrix_digest': md, 'authorized_scope': {'VehicleDefinitions': 73, 'two_door': 23, 'four_door': 50, 'expected_creations': 73, 'expected_no_ops': 0,
            'target_generation_PK': 32, 'target_generation_uuid': '38d3c3ac-f825-4406-abb5-c2d12b9129a4'},
        'table_counts': counts, 'canonical_identity_digest': digest(canonical_identity),
        'all_VehicleDefinition_rows_digest': fingerprint_tables['reference_vehicledefinition']['table_digest'],
        'correspondence_identity_and_targets_digest': digest(correspondence_identity),
        'all_correspondence_rows_digest': fingerprint_tables['reference_generationcorrespondencerevision']['table_digest'],
        'all_receipt_rows_and_lineage_digest': fingerprint_tables['reference_importexecutionreceipt']['table_digest'],
        'schema_digest': schema_digest_value, 'tables': fingerprint_tables, 'verified_session_fingerprints': session_baseline,
        'SQLite_integrity': 'ok', 'foreign_key_violations': 0, 'MY2021_canonical_import_records': 0,
        'unexplained_application_changes': [], 'current_task_live_database_writes': 0,
        'execution_performed': False, 'execution_resumption': 'No import in this read-only task. Use this separate baseline for a newly verified preflight/consistent backup; preserve the original certified package unchanged and do not ignore subsequent drift.'})
    save(HERE / 'verification_summary.json', {'result': 'passed; fresh baseline established', 'all_tables_inspected': len(diff),
        'counts': {'VehicleDefinitions': 861, 'receipts': 3075, 'correspondences': 159},
        'all_861_canonical_rows_PK_UUID_slug_and_other_fields_unchanged': True,
        'old_receipts_and_lineage_unchanged': True, 'all159_correspondence_targets_verified': True,
        'approved95_publication_additions_reconciled': True, 'unexplained_non_session_changes': 0,
        'normal_session_rows_changed': 1, 'committed_private_auth_differences_documented': True,
        'database_sha256_before': before['sha256'], 'database_sha256_after': sha(LIVE),
        'live_database_unchanged_by_audit': True, 'new_database_backup_created': False,
        'execution_performed': False, 'new_VehicleDefinitions': 0, 'new_receipts': 0,
        'precise_intermediate_hash_pair_causes_proven': False, 'limitation': 'See session_nature_assessment; no matching intermediate physical snapshots exist.'})
    print('AUDIT PASSED:', len(diff), 'tables;95+95documented publication additions;one normal browsing session update;no unexplained application changes.')
    print('Fresh operational baseline:', before['sha256'], '861/3075/159;no live writes or import execution.')


if __name__ == '__main__':
    main()
