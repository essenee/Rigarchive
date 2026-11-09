"""Read-only scope and direct-source compatibility checks; no construction/approval.

Run with .venv/bin/python -B from the repository root. JSON is printed to stdout;
the caller may retain it in this preflight directory. No database connection opens.
"""
import collections
import hashlib
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = next(p for p in HERE.parents if (p / 'manage.py').is_file())
REVIEW = BASE / 'owner_review_20261108'
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['RIGARCHIVE_TEST_DB_PATH'] = ':memory:'
import django
django.setup()
import pypdf
from reference.ingestion.importing.powertrain_identity import _supports


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return 'sha256:' + hashlib.sha256(raw.encode()).hexdigest()


manifests = {}
for directory in (BASE, REVIEW):
    manifest = load(directory / 'artifact_hashes.json')
    for path, expected in manifest.items():
        assert sha(directory / path) == expected, path
    manifests[directory.name] = len(manifest)

table = load(REVIEW / 'owner_approval_table.json')
scope = load(REVIEW / 'proposed_consumer_scope.json')
original = {r['research_row_id']: r for r in load(BASE / 'preliminary_factory_offerings.json')}
rows = {r['research_row_id']: r for r in scope['rows']}
decisions = load(REVIEW / 'classification_review_89_decisions.json')
groups = {g['group_id']: g for g in load(REVIEW / 'classification_groups.json')}
trims = load(REVIEW / 'trim_edition_review.json')
for name, key in [
    ('proposed_consumer_scope.json', 'scope_sha256'),
    ('trim_edition_review.json', 'trim_review_sha256'),
    ('classification_review_89_decisions.json', 'classification_review_sha256'),
    ('classification_groups.json', 'classification_group_file_sha256'),
    ('preserved_RHD_scope.json', 'RHD_scope_file_sha256'),
]:
    assert sha(REVIEW / name) == table[key], name
assert sha(BASE / 'preliminary_factory_offerings.json') == scope['source_matrix_sha256']
assert len(original) == 74 and len(rows) == 73
for rid, row in rows.items():
    assert all(row[k] == v for k, v in original[rid].items())
    assert row['research_row_sha256'] == digest(original[rid])
    assert row['model_year'] == 2021 and row['market'] == 'US'
    assert row['model_code'] != 'JLUL74'
distribution = collections.Counter(r['body_style'] for r in rows.values())
assert distribution == {'2-door': 23, '4-door': 50}
labels = {r['marketed_trim_proposal'] for r in rows.values()}
assert len(labels) == 24
assert {t['normalized_display_name_proposal'] for t in trims
        if t['separate_canonical_trim_recommended']} == labels
assert len({(r['body_style'], r['marketed_trim_proposal'], r['engine_code'])
            for r in rows.values()}) == 73
approved = {i for g in table['groups'] for i in g['consumer_decision_ids']}
deferred = {i for g in table['groups'] for i in g['deferred_decision_ids']}
assert len(approved) == 88 and deferred == {'CLASS-075'}
expected = {
    ('ERC', 'engine_aspiration'): ('naturally_aspirated', 17),
    ('ERC', 'electrification_type'): ('none', 17),
    ('ERG', 'engine_aspiration'): ('naturally_aspirated', 20),
    ('EC1', 'electrification_type'): ('none', 20),
    ('EXJ', 'electrification_type'): ('none', 12),
    ('ESG', 'engine_aspiration'): ('naturally_aspirated', 1),
    ('ESG', 'electrification_type'): ('none', 1),
}
seen = set()
for entry in table['groups']:
    group = groups[entry['group_id']]
    value, count = expected[(group['engine_code'], group['field'])]
    assert entry['proposed_value'] == value
    assert len(entry['consumer_decision_ids']) == count
    for did in entry['consumer_decision_ids']:
        d = next(d for d in decisions if d['decision_id'] == did)
        rid = d['research_row_id']
        assert rid in rows and d['research_row_sha256'] == digest(original[rid])
        assert (d['engine_code'], d['field'], d['proposed_value'], d['confidence']) == (
            group['engine_code'], group['field'], value, 'moderate')
        assert (rid, d['field']) not in seen
        seen.add((rid, d['field']))
assert len({rid for rid, field in seen}) == 70
assert next(d for d in decisions if d['decision_id'] == 'CLASS-075')['research_row_id'] == 'JL21-71'
earlier = load(REVIEW / 'completeness_reconciliation.json')['earlier_only_rows']
assert len(earlier) == 24
assert {r['research_row_id'] for r in earlier} <= set(rows)
for source in load(BASE / 'source_revision_inventory.json'):
    assert sha(ROOT / source['retained_path']) == source['sha256']
for source in load(BASE / 'supplemental_source_inventory.json'):
    assert sha(ROOT / source['retained_path']) == source['document_sha256']
    assert sha(ROOT / source['extraction_path']) == source['extraction_sha256']
for source in load(REVIEW / 'additional_source_index.json'):
    assert sha(ROOT / source['path']) == source['sha256']
    assert sha(ROOT / source['extraction_path']) == source['extraction_sha256']
dbhash = sha(ROOT / 'db.sqlite3')
assert dbhash == load(REVIEW / 'baseline.json')['database_sha256']

# Faithful manufacturer source lexemes must work without inserting a normalized
# fuel enum into raw evidence. This is the actual predicate candidate_powertrain
# applies to every mapped powertrain assertion, including fuel_type.
pdf = BASE / 'source_pdfs/FCA_MY2021_Wrangler_392_specifications.pdf'
page = pypdf.PdfReader(pdf).pages[0].extract_text()
fuel_line = next(line for line in page.splitlines() if 'Fuel Requirement' in line)
accepted = _supports(fuel_line, 'fuel_type', 'gasoline', jeep=True)
assert not accepted
assert not _supports(page, 'fuel_type', 'gasoline', jeep=True)
result = {
    'scope_verification': 'passed',
    'review_manifest_counts': manifests,
    'owner_approval_authority': 'Explicit owner approval in current chat and corrected prerequisite-order task; historical pending artifacts preserved unchanged',
    'consumer_rows': 73, 'body_style_distribution': dict(distribution),
    'approved_body_trim_labels': 24, 'earlier_only_rows_preserved_in_scope': 24,
    'approved_field_decisions_verified': 88, 'affected_candidates': 70,
    'deferred_decision': 'CLASS-075 / JL21-71 / EC1 electrification_type',
    'RHD': 'JLUL74 preserved; no candidate constructed; identity semantics deferred',
    'stage_1': 'blocked before candidate construction',
    'blocking_candidate': 'JL21-70 / Unlimited Rubicon 392 / ESG',
    'blocking_field': 'fuel_type',
    'source': str(pdf.relative_to(ROOT)), 'source_sha256': sha(pdf),
    'source_pdf_page': 1, 'source_fuel_requirement_verbatim': fuel_line,
    'existing_direct_support_predicate_accepts_gasoline': accepted,
    'existing_full_page_predicate_accepts_gasoline': False,
    'explanation': 'The reviewed normalized fuel value is gasoline, but the unchanged direct-source predicate recognizes gasoline/petrol/diesel terms, not premium 91-octane wording. The retained 392 specification has no gasoline/petrol token. The generic manual gasoline section names 2.0L and 3.6L engines, not 6.4L. The retained production release gasoline/diesel phrase describes models outside North America; it is not an applicable US ESG fuel assertion. Secondary research transcription cannot be relabeled as manufacturer evidence.',
    'decisions_applied': 0, 'base_candidates_constructed': 0,
    'candidate_revisions_created': 0, 'final_candidates_delivered': 0,
    'database_unchanged_from_owner_review': True, 'database_sha256': dbhash,
    'python': sys.version, 'interpreter': sys.executable,
    'django': django.get_version(), 'pypdf': pypdf.__version__,
    'requirements': (ROOT / 'requirements.txt').read_text().splitlines(),
    'required_direction': 'Authorize applicable manufacturer fuel-evidence acquisition or separately authorize a bounded direct-source validator change. No raw-evidence rewriting or extra adjudication is authorized.',
}
print(json.dumps(result, indent=2, ensure_ascii=False))
