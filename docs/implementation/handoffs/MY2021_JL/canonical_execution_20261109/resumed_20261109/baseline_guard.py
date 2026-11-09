"""Read-only reconciled-state guard. Tolerate only verified browsing sessions.

No canonical eligibility/resolver/import rules are replaced. Every non-session
table is checked against the fresh baseline before execution. After execution,
only the73authorized definition/receipt additions and sequences are allowed.
"""
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core import signing
from django.contrib.sessions.backends.db import SessionStore

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = next(p for p in HERE.parents if (p / 'manage.py').is_file())
RECONCILIATION = BASE / 'session_reconciliation_20261109'
BASELINE_FILE = RECONCILIATION / 'execution_baseline.json'
BASELINE_SHA = 'sha256:058bbd44e0811c83bf67c916ae92e27b6a0b062c26be031876e9582190e01473'


def digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def sha(path):
    return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprints(table):
    rows = {}
    for pk, row in table['rows'].items():
        rows[digest(list(pk))] = {'row_digest': digest(list(row)),
            'column_digests': {name: digest(row[n]) for n, name in enumerate(table['columns'])}}
    return {'count': len(rows), 'columns': table['columns'], 'primary_key_columns': table['pk_columns'],
            'rows': rows, 'table_digest': digest(rows)}


def changed_columns(before, after):
    assert set(before['column_digests']) == set(after['column_digests']), 'Session columns changed'
    return [k for k in before['column_digests'] if before['column_digests'][k] != after['column_digests'][k]]


def verify_session_change(previous, values, columns, *, known_history, baseline_time, now):
    """Pure signed-session check; report no raw keys, contents or signatures."""
    store = SessionStore()
    raw = values[columns.index('session_data')]
    expiry_raw = values[columns.index('expire_date')]
    try:
        data = signing.loads(raw, salt=store.key_salt, serializer=store.serializer)
    except signing.BadSignature:
        raise AssertionError('Changed session signature is invalid') from None
    assert sorted(data) == previous['decoded_key_names'], 'Session decoded keys changed'
    assert digest({k: v for k, v in data.items() if k != 'recently_viewed_generations'}) == previous['decoded_non_history_digest'], 'Session authentication/non-history values changed'
    history = data.get('recently_viewed_generations', [])
    assert isinstance(history, list) and len(history) <= 5, 'Session history exceeds approved schema'
    keys = {'manufacturer_name', 'model_name', 'generation_name', 'generation_number', 'year_span', 'url', 'image_url'}
    urls = []
    for item in history:
        assert isinstance(item, dict) and set(item) == keys, 'Session history schema changed'
        assert item['url'] in known_history, 'Session history references unknown generation'
        expected = known_history[item['url']]
        assert all(item[k] == expected[k] for k in keys - {'image_url'}), 'Session history canonical metadata mismatch'
        assert item['image_url'] is None or isinstance(item['image_url'], str), 'Invalid session image metadata'
        urls.append(item['url'])
    assert len(urls) == len(set(urls)), 'Duplicate session history entry'
    signed = signing.b62_decode(raw.rsplit(':', 2)[1])
    expiry = datetime.fromisoformat(expiry_raw)
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    assert int(baseline_time.timestamp()) <= signed <= int(now.timestamp()) + 2, 'Session signing time outside current browsing window'
    assert 0 <= expiry.timestamp() - signed - settings.SESSION_COOKIE_AGE < 2, 'Session expiry differs from normal lifetime'
    return {'valid_signature': True, 'only_recently_viewed_decoded_data_may_differ': True,
            'authentication_values_unchanged': True, 'history_schema_and_canonical_metadata_valid': True,
            'normal_expiry_verified': True, 'history_count': len(history)}


def verify_tables(baseline, current, *, session_rows, known_history, baseline_time, now, post_execution=False):
    assert set(baseline['tables']) == set(current), 'Database table inventory changed'
    allowed_post = {'reference_vehicledefinition', 'reference_importexecutionreceipt', 'sqlite_sequence'} if post_execution else set()
    updates = []
    for name, actual in current.items():
        expected = baseline['tables'][name]
        assert actual['columns'] == expected['columns'] and actual['primary_key_columns'] == expected['primary_key_columns'], 'Database schema changed'
        if name in allowed_post:
            continue  # Separately reconciled against backup with exact73+73 additions.
        if name != 'django_session':
            assert actual == expected, 'Non-session application data changed in ' + name
            continue
        assert actual['rows'].keys() == expected['rows'].keys(), 'New/deleted session requires independent lifecycle review'
        for pk, row in actual['rows'].items():
            old = expected['rows'][pk]
            if row == old:
                continue
            columns = changed_columns(old, row)
            assert columns and set(columns) <= {'session_data', 'expire_date'}, 'Unexpected changed session column'
            private = next(s for s in baseline['verified_session_fingerprints'] if s['PK_fingerprint'] == pk)
            checks = verify_session_change(private, session_rows[pk], actual['columns'], known_history=known_history,
                baseline_time=baseline_time, now=now)
            updates.append({'PK_fingerprint': pk, 'changed_columns': columns, **checks})
    return updates


def verify_reconciled_state(phase, *, post_execution=False):
    from docs.implementation.handoffs.MY2021_JL.session_reconciliation_20261109.audit_sessions import tables, schema, ro
    from reference.models import Generation
    for p, h in json.loads((RECONCILIATION / 'artifact_hashes.json').read_text()).items():
        assert sha(RECONCILIATION / p) == h, 'Reconciliation artifact changed'
    b = json.loads(BASELINE_FILE.read_text())
    assert b['live_database']['sha256'] == BASELINE_SHA
    assert b['authorized_matrix_digest'] == 'sha256:6926df6c06e4bd471bbda02c67257cf7a7e2999cf5cdfebfc8b06ead31a9996e'
    c = ro(ROOT / 'db.sqlite3'); c.execute('BEGIN')
    raw = tables(c)
    assert digest(schema(c)) == b['schema_digest'], 'Database schema drift'
    actual = {name: fingerprints(t) for name, t in raw.items()}
    baseline_time = datetime.fromisoformat(b['live_database']['modification_time']['UTC'])
    known = {}
    for g in Generation.objects.select_related('vehicle_model__manufacturer'):
        url = g.get_absolute_url()
        known[url] = {'manufacturer_name': g.vehicle_model.manufacturer.name, 'model_name': g.vehicle_model.name,
            'generation_name': g.name, 'generation_number': g.generation_number,
            'year_span': f'{g.start_year}–{g.end_year}' if g.end_year else f'{g.start_year}–present', 'url': url}
    sessions = {digest(list(pk)): value for pk, value in raw['django_session']['rows'].items()}
    changes = verify_tables(b, actual, session_rows=sessions, known_history=known, baseline_time=baseline_time,
        now=datetime.now(timezone.utc), post_execution=post_execution)
    if not post_execution:
        vd = raw['reference_vehicledefinition']; cols = vd['columns']
        identities = [[row[cols.index(k)] for k in ('id','uuid','slug','generation_id','model_year','market')]
                      for _, row in sorted(vd['rows'].items())]
        co = raw['reference_generationcorrespondencerevision']; cols = co['columns']
        correspondence = [[row[cols.index(k)] for k in ('id','uuid','generation_id','source_id','source_namespace','identity_type','native_identifier','market','start_year','end_year','content_hash')]
                          for _, row in sorted(co['rows'].items())]
        assert digest(identities) == b['canonical_identity_digest']
        assert digest(correspondence) == b['correspondence_identity_and_targets_digest']
        assert actual['reference_importexecutionreceipt']['table_digest'] == b['all_receipt_rows_and_lineage_digest']
    assert c.execute('PRAGMA integrity_check').fetchone()[0] == 'ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
    current_hash = sha(ROOT / 'db.sqlite3')
    c.rollback(); c.close()
    result = {'phase': phase, 'reconciled_baseline': str(BASELINE_FILE.relative_to(ROOT)), 'baseline_file_sha256': sha(BASELINE_FILE),
        'accepted_baseline_database_sha256': BASELINE_SHA, 'current_file_sha256': current_hash,
        'byte_hash_differs': current_hash != BASELINE_SHA, 'verified_normal_session_changes': changes,
        'non_session_application_data_matches_baseline': not post_execution,
        'post_execution_additions_require_separate_backup_reconciliation': post_execution,
        'schema_identity_and_receipt_digest_checks': 'passed' if not post_execution else 'non-mutated tables passed;73+73 additions separately reconciled',
        'SQLite_integrity': 'ok', 'foreign_key_violations': 0, 'live_database_writes': 0}
    path = HERE / (phase + '_baseline_check.json')
    with path.open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    return result


def reconcile_preserving_authentication(before, after, additions):
    """Verify all original rows; independently check any browsing-only sessions."""
    assert before['schema_digest'] == after['schema_digest']
    assert set(before['tables']) == set(after['tables'])
    session_checks = verify_reconciled_state('post_import_session_assessment', post_execution=True)
    results = {}
    for name, original in before['tables'].items():
        actual = after['tables'][name]
        assert actual['columns'] == original['columns']
        same = all(actual['rows'].get(k) == h for k, h in original['rows'].items())
        if name != 'django_session':
            assert same, 'Preexisting application row changed in ' + name
        assert actual['count'] == original['count'] + additions.get(name, 0), 'Unexpected row count in ' + name
        results[name] = {'before': original['count'], 'after': actual['count'], 'all_preexisting_rows_unchanged': same,
            'new_rows': actual['count'] - original['count'],
            **({'ordinary_browsing_changes_verified': True, 'local_authentication_state_preserved': True} if name == 'django_session' else {})}
    assert before['sequences'].keys() == after['sequences'].keys()
    for name, seq in before['sequences'].items():
        assert after['sequences'][name] == seq + additions.get(name, 0)
    return results
