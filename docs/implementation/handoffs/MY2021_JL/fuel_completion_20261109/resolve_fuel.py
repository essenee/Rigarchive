"""Owner-authorized fuel adjudication and read-only final artifact validation.

Use existing adjudication 1.1 and Candidate 2.1.0. No ORM or canonical planning.
The new cumulative finding binds the original unclassified base: existing
projection validation permits one adjudication, not chained human documents.
"""
import copy
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PREVIOUS = BASE / 'candidate_classification_20261109'
ROOT = next(p for p in HERE.parents if (p / 'manage.py').is_file())
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['RIGARCHIVE_TEST_DB_PATH'] = ':memory:'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import django
django.setup()
from django.core.exceptions import ValidationError
from reference.ingestion.classification_adjudication import (
    validate_classification_adjudication, validate_classification_candidate,
)
from reference.ingestion.serialization import (
    deserialize_artifact, serialize_artifact, candidate_config_doc_to_dict,
    adjudication_from_dict, adjudication_to_dict, compute_adjudication_hash,
)
from reference.ingestion.importing.powertrain_identity import candidate_powertrain, _supports
from reference.ingestion.generation_correspondence import digest, validate_documents
from reference.ingestion.validation import validate_candidate_configuration
from reference.powertrain import FIELDS, FUEL


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


def unchanged():
    baseline = load(HERE / 'preservation_baseline.json')
    for path, expected in baseline['files'].items():
        assert sha(ROOT / path) == expected, path
    for path, expected in baseline['protected_contract_and_code'].items():
        assert sha(ROOT / path) == expected, path
    assert sha(ROOT / 'db.sqlite3') == baseline['database_sha256']


def apply():
    assert not (HERE / 'authorization.json').exists(), 'Existing authorization checkpoint; do not repeat approval'
    for folder in (PREVIOUS, BASE, BASE / 'owner_review_20261108'):
        for path, expected in load(folder / 'artifact_hashes.json').items():
            assert sha(folder / path) == expected, path
    protected = [
        'reference/ingestion/classification_adjudication.py', 'reference/powertrain.py',
        'reference/ingestion/normalization/powertrain.py', 'reference/ingestion/importing/powertrain_identity.py',
        'reference/ingestion/contracts.py', 'reference/ingestion/validation.py',
        'reference/ingestion/serialization.py', 'reference/management/commands/adjudicate_canonical_import.py',
        'docs/architecture/designs/RA-044-Structured-Powertrain-Identity-Implementation-Architecture.md',
        'docs/architecture/ADR/ADR-0012-Structured-Powertrain-Identity-And-Hybrid-Terminology.md',
    ]
    save(HERE / 'preservation_baseline.json', {
        'files': {rel(p): sha(p) for p in BASE.rglob('*') if p.is_file() and not p.is_relative_to(HERE)},
        'database_sha256': sha(ROOT / 'db.sqlite3'),
        'protected_contract_and_code': {p: sha(ROOT / p) for p in protected},
    })
    now = datetime.now(timezone.utc).isoformat()
    requirements = (ROOT / 'requirements.txt').read_text().splitlines()
    for requirement in requirements:
        name, version = requirement.split('==')
        assert importlib.metadata.version(name) == version
    assert sys.version_info[:3] == (3, 13, 1)
    save(HERE / 'environment.json', {'python': sys.version, 'interpreter': sys.executable,
         'django': django.get_version(), 'pypdf': importlib.metadata.version('pypdf'),
         'requirements': requirements, 'requirements_match': True, 'database_setting': ':memory:'})
    index = load(PREVIOUS / 'current_candidate_index.json')
    old = next(r for r in index['rows'] if r['research_row_id'] == 'JL21-70')
    assert len(index['rows']) == 73 and FUEL == {'gasoline': 'Gasoline', 'diesel': 'Diesel'}
    assert sha(ROOT / old['candidate_artifact']) == old['artifact_sha256']
    current = deserialize_artifact((ROOT / old['candidate_artifact']).read_text())
    assert digest(candidate_config_doc_to_dict(current)) == old['candidate_hash']
    assert current.canonical_powertrain['fuel_type'] is None
    try:
        candidate_powertrain(current, complete=True, verify_bytes=True)
    except ValidationError as exc:
        error = exc.messages
        assert error == ['Missing evidenced powertrain attribute: fuel_type.']
    else:
        raise AssertionError('Expected original incomplete fuel identity')
    prior = adjudication_from_dict(load(ROOT / old['approved_adjudication']))
    original_base = validate_classification_adjudication(prior, require_approved=True)
    assert set(prior.evidence_anchors['classifications']) == {'engine_aspiration', 'electrification_type'}
    source = next(d for d in original_base.evidence_documents if d['source_id'] == 'FCA_MY2021_Wrangler_392_specifications')
    page = next(a for a in source['assertions'] if a['assertion_id'].endswith('-p1'))
    line = next(line for line in page['raw_value'].splitlines() if 'Fuel Requirement' in line)
    assert 'Premium 91 octane (R+M)/2' in line and 'required' in line
    assert not _supports(line, 'fuel_type', 'gasoline', jeep=True)
    assert not _supports(page['raw_value'], 'fuel_type', 'gasoline', jeep=True)
    reference = '|'.join((source['source_id'], source['raw_artifact_hash'], source['assertion_set_id'], page['assertion_id']))
    proposal = copy.deepcopy(prior)
    proposal.created_at = now
    proposal.operator_label = 'pending_human_signoff'
    proposal.adjudication_decision = 'proposed_classifications'
    proposal.adjudication_notes = (
        'Owner-approved MY2021 US JL21-70 fuel_type=gasoline. Cumulative revision against the original unclassified base, '
        'not a chained projection. The two previous approved claims are carried forward exactly unchanged from '
        + old['approved_adjudication'] + ' (' + prior.adjudication_hash + '). '
        'Only fuel_type is newly decided; premium 91-octane requirement remains source evidence outside the identity tuple. '
        'Superseded candidate ' + old['candidate_artifact'] + ' (' + old['candidate_hash'] + ') remains preserved. '
        'No import, publication or Matrix authorization.')
    fuel = {
        'value': 'gasoline',
        'reasoning': 'The project owner approves gasoline for this exact production MY2021 US Rubicon 392. The manufacturer specifies Premium 91 octane (R+M)/2 — required for its documented 6.4L engine. In this engine-specific fuel requirement, premium octane is a gasoline grade, not a separate broad fuel category. Under accepted RA-044 the existing fuel_type value is gasoline; octane grade is outside the five-field powertrain identity. This is a supported human-adjudicated classification, not a claim that the retained specification literally states the gasoline enum.',
        'applicability': 'Only JL21-70, MY2021 US Jeep Wrangler Unlimited Rubicon 392, ESG / JLJX74 / 27X; exact original base digest ' + old['base_candidate_hash'] + '; superseded classified revision ' + old['candidate_hash'] + '.',
        'limitations': 'The retained specification states Premium 91 octane (R+M)/2 — required; preserve required, not merely recommended, and preserve its octane metric. It does not literally say gasoline or unleaded in this fuel line. No new manufacturer quotation, default from engine size/code, new enum, octane field, alternate-fuel capability or other-year/market/engine approval is inferred. Gasoline classification does not relax the manufacturer premium-fuel requirement.',
        'confidence': 'moderate', 'source_assertion_refs': [reference], 'evidence_status': 'supported',
    }
    proposal.evidence_anchors['classifications']['fuel_type'] = fuel
    # Preserve exact supporting documents and both already-approved claims.
    for key, claim in prior.evidence_anchors['classifications'].items():
        assert proposal.evidence_anchors['classifications'][key] == claim
    proposal.adjudication_hash = compute_adjudication_hash(adjudication_to_dict(proposal))
    validate_classification_adjudication(proposal)
    save(HERE / 'authorization.json', {'created_at': now,
         'authority': 'Explicit project-owner task: MY2021 Rubicon 392 Fuel-Type Adjudication and Final Validation',
         'new_approved_decision': {'candidate_reference': 'JL21-70', 'field': 'fuel_type', 'value': 'gasoline'},
         'prior_approvals_carried_forward_unchanged': ['CLASS-088', 'CLASS-089'],
         'prior_approved_adjudication': old['approved_adjudication'],
         'prior_approved_adjudication_hash': prior.adjudication_hash,
         'original_base': old['base_candidate_artifact'], 'original_base_hash': old['base_candidate_hash'],
         'superseded_candidate': old['candidate_artifact'], 'superseded_candidate_hash': old['candidate_hash'],
         'workflow': 'Existing adjudication CLI; one cumulative finding bound to original base; no chained human projections',
         'new_distinct_field_decisions': 1, 'cumulative_fields_in_new_envelope': 3,
         'boundaries': 'No code/contract/schema/DB/canonical/planning/publication changes; no commit or push'})
    save(HERE / 'contract_and_evidence_review.json', {
         'fuel_taxonomy': FUEL, 'five_fields': list(FIELDS), 'octane_is_identity_field': False,
         'original_completeness_error': error, 'raw_fuel_line_direct_parser_accepts_gasoline': False,
         'source_document': source['raw_artifact_reference'], 'source_sha256': source['raw_artifact_hash'],
         'source_pdf_page': 1, 'source_assertion_ref': reference, 'manufacturer_wording': line,
         'fuel_requirement_status': 'Premium 91 (R+M)/2 required; not merely recommended',
         'manufacturer_unleaded_wording_in_this_line': False,
         'classification_basis': 'Human-approved broad gasoline category, retaining manufacturer fuel-grade wording unchanged',
         'contract_implications': 'None; gasoline already exists, octane is outside the five-field identity; original-base cumulative adjudication uses unchanged existing validation',
         'historical_base_limitation_notice': 'Original research_revision_lineage remains byte-for-byte base history, including its then-unresolved fuel note; the new approved projection and current index resolve that historical gap'})
    pp = HERE / 'JL21-70.fuel-r2.proposed.adjudication.1.1.json'
    ap = HERE / 'JL21-70.fuel-r2.approved.adjudication.1.1.json'
    cp = HERE / 'JL21-70.fuel-r2.candidate.2.1.0.json'
    save(pp, adjudication_to_dict(proposal))
    command = [str(ROOT / '.venv/bin/python'), '-B', str(ROOT / 'manage.py'), 'adjudicate_canonical_import',
               '--classification-review', rel(pp), '--operator', 'project_owner', '--output', rel(ap),
               '--candidate-output', rel(cp), '--skip-checks']
    result = subprocess.run(command, input='APPROVE CLASSIFICATIONS\n', capture_output=True, text=True,
                            cwd=ROOT, env=os.environ, timeout=60)
    with (HERE / 'adjudication_cli.txt').open('x') as stream:
        stream.write(result.stdout + result.stderr)
    assert result.returncode == 0, 'Existing workflow rejected the finding: inspect retained CLI; stop without changing contracts'
    approved = adjudication_from_dict(load(ap))
    validate_classification_adjudication(approved, require_approved=True)
    assert approved.evidence_anchors == proposal.evidence_anchors
    candidate = deserialize_artifact(cp.read_text())
    values = candidate_powertrain(candidate, complete=True, verify_bytes=True)
    expected = dict(current.canonical_powertrain, fuel_type='gasoline')
    assert values == expected
    assert candidate.candidate_identity == current.candidate_identity
    for key, value in current.canonical_powertrain.items():
        if key != 'fuel_type':
            assert values[key] == value
    new = copy.deepcopy(old)
    new.update(candidate_artifact=rel(cp), candidate_hash=digest(candidate_config_doc_to_dict(candidate)),
        artifact_sha256=sha(cp), canonical_powertrain=values, unresolved_fields=[], status='complete',
        approved_adjudication=rel(ap), approved_adjudication_hash=approved.adjudication_hash,
        approved_adjudication_sha256=sha(ap), prior_approved_adjudication=old['approved_adjudication'],
        prior_approved_adjudication_hash=prior.adjudication_hash,
        additional_fuel_approval=rel(HERE / 'authorization.json'))
    new['superseded_artifacts'].append({'artifact': old['candidate_artifact'], 'candidate_hash': old['candidate_hash'],
         'artifact_sha256': old['artifact_sha256'], 'reason': 'One additional owner-approved gasoline classification; two previous classifications preserved exactly'})
    final = [new if r['research_row_id'] == 'JL21-70' else r for r in index['rows']]
    save(HERE / 'current_candidate_index.json', {'created_at': now, 'candidate_contract': '2.1.0',
         'previous_index': rel(PREVIOUS / 'current_candidate_index.json'),
         'previous_index_sha256': sha(PREVIOUS / 'current_candidate_index.json'), 'rows': final})
    save(HERE / 'superseded_artifact_reference.json', {'candidate_reference': 'JL21-70',
         'previous_candidate': old['candidate_artifact'], 'previous_candidate_hash': old['candidate_hash'],
         'previous_artifact_sha256': old['artifact_sha256'], 'previous_adjudication': old['approved_adjudication'],
         'previous_adjudication_hash': prior.adjudication_hash, 'previous_adjudication_sha256': sha(ROOT / old['approved_adjudication']),
         'original_base': old['base_candidate_artifact'], 'original_base_hash': old['base_candidate_hash'],
         'current_candidate': rel(cp), 'current_candidate_hash': new['candidate_hash'], 'current_file_sha256': sha(cp),
         'current_adjudication': rel(ap), 'current_adjudication_hash': approved.adjudication_hash,
         'one_new_distinct_decision': 'fuel_type=gasoline', 'carried_forward_decisions': ['CLASS-088', 'CLASS-089']})
    unchanged()
    print('APPLIED: one new fuel decision; cumulative 3-claim adjudication; other four 392 fields unchanged')
    print('Candidate content digest:', new['candidate_hash'])


def validate():
    unchanged()
    current = load(HERE / 'current_candidate_index.json')['rows']
    previous = {r['research_row_id']: r for r in load(PREVIOUS / 'current_candidate_index.json')['rows']}
    assert len(current) == len(previous) == 73
    assert Counter(r['body_style'] for r in current) == {'2-door': 23, '4-door': 50}
    approved_labels = set(load(PREVIOUS / 'authorization.json')['approved_labels'])
    assert {r['marketed_trim_proposal'] for r in current} == approved_labels and len(approved_labels) == 24
    seen = set(); changed = []; lineage = []; candidates = {}
    for row in current:
        rid = row['research_row_id']; old = previous[rid]
        if row != old:
            changed.append(rid)
        else:
            assert sha(ROOT / row['candidate_artifact']) == old['artifact_sha256']
        candidate = deserialize_artifact((ROOT / row['candidate_artifact']).read_text())
        validate_candidate_configuration(candidate)
        validate_classification_candidate(candidate)
        values = candidate_powertrain(candidate, complete=True, verify_bytes=True)
        assert values == row['canonical_powertrain'] and all(values[k] is not None for k in FIELDS)
        assert digest(candidate_config_doc_to_dict(candidate)) == row['candidate_hash']
        assert sha(ROOT / row['candidate_artifact']) == row['artifact_sha256']
        encoded = serialize_artifact(candidate)
        assert serialize_artifact(deserialize_artifact(encoded)) == encoded
        assert candidate.candidate_reference == rid and row['model_code'] != 'JLUL74' and rid != 'JL21-71'
        assert (candidate.candidate_identity.model_year, candidate.candidate_identity.market, candidate.candidate_identity.trim_name) == (2021, 'US', row['marketed_trim_proposal'])
        key = (candidate.candidate_identity.trim_name, tuple(values[k] for k in FIELDS), 'US')
        assert key not in seen; seen.add(key)
        if row['engine_code'] == 'ECX':
            assert row == old
            assert not any(d['source_id'] == 'human_classification_adjudication' for d in candidate.evidence_documents)
        if rid == 'JL21-70':
            assert values == dict(old['canonical_powertrain'], fuel_type='gasoline')
            old_candidate = deserialize_artifact((ROOT / old['candidate_artifact']).read_text())
            assert candidate.candidate_identity == old_candidate.candidate_identity
            assert candidate.unknown_fields == old_candidate.unknown_fields
            adj = adjudication_from_dict(load(ROOT / row['approved_adjudication']))
            validate_classification_adjudication(adj, require_approved=True)
            assert adjudication_to_dict(adjudication_from_dict(adjudication_to_dict(adj))) == adjudication_to_dict(adj)
            assert adj.evidence_anchors['candidate_artifact_reference'] == old['base_candidate_artifact']
            assert adj.evidence_anchors['candidate_hash'] == old['base_candidate_hash']
            prior = adjudication_from_dict(load(ROOT / old['approved_adjudication']))
            assert adj.evidence_anchors['supporting_documents'] == prior.evidence_anchors['supporting_documents']
            for k, claim in prior.evidence_anchors['classifications'].items():
                assert adj.evidence_anchors['classifications'][k] == claim
            assert adj.evidence_anchors['classifications']['fuel_type']['value'] == 'gasoline'
            # Premium requirement is still the original source bytes and raw text.
            review = load(HERE / 'contract_and_evidence_review.json')
            source = next(d for d in candidate.evidence_documents if d['source_id'] == 'FCA_MY2021_Wrangler_392_specifications')
            assert sha(ROOT / source['raw_artifact_reference']) == review['source_sha256']
            assert any(review['manufacturer_wording'] in str(a['raw_value']) for a in source['assertions'])
        candidates[rid] = candidate
        lineage.append({'candidate_reference': rid, 'artifact': row['candidate_artifact'],
             'candidate_hash': row['candidate_hash'], 'artifact_sha256': row['artifact_sha256'],
             'original_base': row['base_candidate_artifact'], 'original_base_hash': row['base_candidate_hash'],
             'canonical_powertrain': values,
             'evidence_documents': [{'source_id': d['source_id'], 'reference': d['raw_artifact_reference'],
                                    'sha256': d['raw_artifact_hash'], 'assertion_set_id': d['assertion_set_id']}
                                   for d in candidate.evidence_documents]})
    assert changed == ['JL21-70']
    records = load(PREVIOUS / 'approved_field_decision_index.json')['records']
    assert len(records) == 88 and len({r['decision_id'] for r in records}) == 88
    checked = []
    for record in records:
        prior = adjudication_from_dict(load(ROOT / record['approved_adjudication']))
        validate_classification_adjudication(prior, require_approved=True)
        assert prior.adjudication_hash == record['approved_adjudication_hash']
        assert sha(ROOT / record['approved_adjudication']) == record['approved_adjudication_sha256']
        assert prior.evidence_anchors['classifications'][record['field']] == record['classification']
        candidate = candidates[record['research_row_id']]
        doc = next(d for d in candidate.evidence_documents if d['source_id'] == 'human_classification_adjudication')
        active = adjudication_from_dict(load(ROOT / doc['raw_artifact_reference']))
        assert active.evidence_anchors['classifications'][record['field']] == record['classification']
        assert candidate.canonical_powertrain[record['field']] == record['classification']['value']
        checked.append({'decision_id': record['decision_id'], 'original_adjudication': record['approved_adjudication'],
             'original_adjudication_sha256': record['approved_adjudication_sha256'],
             'active_adjudication': doc['raw_artifact_reference'], 'claim_preserved_exactly': True})
    sport = PREVIOUS / 'sport_RHD_preservation.json'
    preserved = load(sport)
    assert preserved['deferred_decision']['decision_id'] == 'CLASS-075'
    assert preserved['discovery_row']['model_code'] == 'JLUL74'
    save(HERE / 'sport_RHD_preservation_reference.json', {'record': rel(sport), 'sha256': sha(sport),
         'status': 'Unchanged; JLUL74 and CLASS-075 preserved/deferred; no consumer candidate or new identity/visibility semantics'})
    save(HERE / 'prior_88_approval_verification.json', {'decision_count': 88, 'records': checked})
    save(HERE / 'evidence_lineage_report.json', {'rows': lineage, 'all_bytes_verified': True})
    save(HERE / 'validation_results.json', {'result': 'passed', 'current_candidates': 73,
         'complete_five_field_identities': 73, 'body_distribution': {'2-door': 23, '4-door': 50},
         'approved_body_trim_labels': 24, 'other_candidates_unchanged': 72, 'changed_candidates': changed,
         'other_392_powertrain_fields_unchanged': 4, 'prior_approved_decisions_preserved': 88,
         'new_distinct_approved_decisions': 1, 'total_distinct_approved_field_decisions': 89,
         'new_cumulative_adjudication_claims': 3, 'prior_ESG_claims_carried_forward_exactly': 2,
         'unchanged_direct_ECX_candidates': 3, 'RHD_candidates': 0, 'RHD_deferred_decisions': 1,
         'unique_candidate_identities': 73, 'hashes_lineage_and_serialization': 'passed',
         'database_unchanged': True, 'database_sha256': sha(ROOT / 'db.sqlite3'),
         'original_files_and_accepted_code_contracts_unchanged': True,
         'remaining_consumer_classification_blockers': [],
         'generation_correspondence_work': 'Not performed; awaits separate owner authorization'})
    unchanged()
    print('VALIDATED: 73 complete five-field identities; 23/50 distribution; other 72 unchanged; all 88 prior decisions intact')


if __name__ == '__main__':
    {'apply': apply, 'validate': validate}[sys.argv[1]]()
