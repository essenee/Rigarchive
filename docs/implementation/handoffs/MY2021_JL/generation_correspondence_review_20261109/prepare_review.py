"""Prepare unpublished MY2021 correspondences; live SQLite is read-only.

Only the accepted resolver's revision lookup is supplied with unsaved proposals
for simulation. Its evidence, restrictions, target and integrity guards run
unchanged. No publish/save/import/plan operation is called.
"""
import copy
import csv
import hashlib
import importlib.metadata
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
LATEST = BASE / 'fuel_completion_20261109'
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
from django.core.exceptions import ValidationError
from reference.models import Generation, GenerationCorrespondenceRevision as Revision, VehicleDefinition, ImportExecutionReceipt
from reference.ingestion.serialization import deserialize_artifact, serialize_artifact, candidate_config_doc_to_dict, adjudication_from_dict
from reference.ingestion.validation import validate_candidate_configuration
from reference.ingestion.classification_adjudication import validate_classification_adjudication
from reference.ingestion.importing.powertrain_identity import candidate_powertrain
from reference.ingestion.generation_correspondence import (
    digest, validate_documents, validate_generation_evidence, validate_review_payload,
    resolve_generation, _applicable_revisions, parent_snapshot,
)
from reference.powertrain import FIELDS


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


def key(identity):
    return tuple(identity[k] for k in ('source_id', 'source_namespace', 'identity_type', 'native_identifier'))


def revision_key(row):
    return row.source_id, row.source_namespace, row.identity_type, row.native_identifier


def main():
    assert not (HERE / 'preservation_baseline.json').exists(), 'Preserve existing review checkpoint; no automatic rerun'
    now = datetime.now(timezone.utc).isoformat()
    dbhash = sha(ROOT / 'db.sqlite3')
    connection.cursor().execute('PRAGMA query_only=ON')
    counts = {'VehicleDefinitions': VehicleDefinition.objects.count(), 'audit_receipts': ImportExecutionReceipt.objects.count(), 'published_correspondences': Revision.objects.count()}
    assert counts == {'VehicleDefinitions': 861, 'audit_receipts': 2980, 'published_correspondences': 64}, 'Material database discrepancy: stop before proposals'
    gen = Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32, uuid='38d3c3ac-f825-4406-abb5-c2d12b9129a4')
    vm = gen.vehicle_model
    assert gen.name == 'JL' and gen.is_active and vm.is_active and vm.manufacturer.is_active
    assert (vm.name, vm.manufacturer.name) == ('Wrangler', 'Jeep')
    assert gen.start_year <= 2021 and (gen.end_year is None or gen.end_year >= 2021)
    assert sys.version_info[:3] == (3, 13, 1)
    requirements = (ROOT / 'requirements.txt').read_text().splitlines()
    for item in requirements:
        name, version = item.split('==')
        assert importlib.metadata.version(name) == version
    # Inspect/verify every file in the latest complete checkpoint, and preserve
    # every older handoff byte before any preparation output is written.
    for path, expected in load(LATEST / 'artifact_hashes.json').items():
        assert sha(LATEST / path) == expected, path
    latest_json = {p.name: load(p) for p in LATEST.glob('*.json')}
    assert latest_json['validation_results.json']['complete_five_field_identities'] == 73
    baseline = {rel(p): sha(p) for p in BASE.rglob('*') if p.is_file() and not p.is_relative_to(HERE)}
    protected = ['reference/models.py', 'reference/ingestion/generation_correspondence.py',
                 'reference/ingestion/normalization/generation.py', 'reference/ingestion/contracts.py',
                 'reference/ingestion/validation.py', 'reference/ingestion/serialization.py',
                 'reference/ingestion/classification_adjudication.py',
                 'reference/management/commands/publish_generation_correspondence.py']
    save(HERE / 'preservation_baseline.json', {'files': baseline, 'database_sha256': dbhash,
         'code_and_contract_hashes': {p: sha(ROOT / p) for p in protected},
         'current_state_before_sha256': sha(ROOT / 'docs/implementation/CURRENT_STATE.md'),
         'changelog_before_sha256': sha(ROOT / 'CHANGELOG.md')})
    save(HERE / 'environment.json', {'python': sys.version, 'interpreter': sys.executable,
         'django': django.get_version(), 'pypdf': importlib.metadata.version('pypdf'),
         'requirements': requirements, 'requirements_match': True, 'live_database_access': 'SQLite mode=ro plus PRAGMA query_only=ON'})
    published = list(Revision.objects.select_related('vehicle_model__manufacturer', 'generation', 'supersedes').all())
    existing_review = []
    for r in published:
        r.clean()
        assert r.content_hash == digest(r.review_payload())
        validate_documents(r.evidence, verify_bytes=True)
        existing_review.append({'PK': r.pk, 'uuid': str(r.uuid), 'key': list(revision_key(r)),
             'market': r.market, 'start_year': r.start_year, 'end_year': r.end_year,
             'generation_PK': r.generation_id, 'content_hash': r.content_hash,
             'review_payload': r.review_payload(), 'reusable_for_MY2021': False,
             'reason': 'Published year scope excludes MY2021; its exact source/model identity must also match, not merely the model code'})
    assert not Revision.objects.filter(vehicle_model=vm, market='US', start_year__lte=2021, end_year__gte=2021, successor__isnull=True).exists()
    historical = []
    for path in [ROOT / 'docs/implementation/handoffs/MY2019_JL/director_review/generation_publication_20261108/README.md',
                 ROOT / 'docs/implementation/handoffs/MY2020_JL/generation_publication_20261108/README.md',
                 ROOT / 'docs/implementation/handoffs/MY2020_JL/generation_correspondence_review_20261108/verify_coverage.py',
                 ROOT / 'docs/implementation/handoffs/MY2020_JL/selector_packaging_repair_20261108/repair_selectors.py']:
        path.read_text()
        historical.append({'path': rel(path), 'sha256': sha(path)})
    save(HERE / 'repository_and_database_state.json', {'counts': counts, 'target': parent_snapshot(vm, gen),
         'database_sha256': dbhash, 'material_discrepancies': [],
         'published_scope_counts': [{'start_year': a, 'end_year': b, 'revisions': n} for (a, b), n in sorted(Counter((r.start_year, r.end_year) for r in published).items())],
         'all_64_published_payloads_and_evidence_valid': True,
         'MY2019_MY2020_successful_publication_receipts': ImportExecutionReceipt.objects.filter(operation_type='correspondence_publication', correspondence_revision_id__gte=9, correspondence_revision_id__lte=64, execution_outcome='created').count(),
         'historical_workflows_reviewed': historical})
    rows = latest_json['current_candidate_index.json']['rows']
    assert len(rows) == 73 and Counter(r['body_style'] for r in rows) == {'2-door': 23, '4-door': 50}
    assert len({r['marketed_trim_proposal'] for r in rows}) == 24
    groups = defaultdict(dict); candidates = {}; rowmap = {}; current_coverage = []
    source_inventory = {s['source_id']: s for s in load(BASE / 'source_revision_inventory.json')}
    excerpts = {(e['source_id'], e['model_code']): e for e in load(BASE / 'evidence_index.json')}
    for row in rows:
        rid = row['research_row_id']; rowmap[rid] = row
        assert sha(ROOT / row['candidate_artifact']) == row['artifact_sha256']
        candidate = deserialize_artifact((ROOT / row['candidate_artifact']).read_text())
        validate_candidate_configuration(candidate)
        candidate_powertrain(candidate, complete=True, verify_bytes=True)
        validate_generation_evidence(candidate.generation_evidence, candidate.evidence_documents)
        assert digest(candidate_config_doc_to_dict(candidate)) == row['candidate_hash']
        assert serialize_artifact(deserialize_artifact(serialize_artifact(candidate))) == serialize_artifact(candidate)
        assert (candidate.candidate_identity.manufacturer_name, candidate.candidate_identity.vehicle_model_name,
                candidate.candidate_identity.model_year, candidate.candidate_identity.market) == ('Jeep', 'Wrangler', 2021, 'US')
        assert row['model_code'] != 'JLUL74' and rid != 'JL21-71'
        for identity in candidate.generation_evidence:
            k = key(identity)
            assert k[1:] == ('source_model_code', 'model_code', row['model_code'])
            groups[k][rid] = candidate
        try:
            resolve_generation(vm, 2021, 'US', candidate.generation_evidence, candidate.evidence_documents,
                               {'trim_name': candidate.candidate_identity.trim_name, 'drivetrain': '4WD'})
        except ValidationError as exc:
            assert exc.messages == ['Missing reviewed generation correspondence.']
            error = exc.messages
        else:
            raise AssertionError('Unexpected existing coverage; reassess before proposals')
        current_coverage.append({'candidate_reference': rid, 'published_resolution': 'unresolved', 'reason': error})
        candidates[rid] = candidate
    assert len(groups) == 95
    save(HERE / 'current_candidate_references.json', {'source_index': rel(LATEST / 'current_candidate_index.json'),
         'source_index_sha256': sha(LATEST / 'current_candidate_index.json'), 'candidate_revisions_are_unchanged': True, 'rows': rows})
    proposals = []; objects = []; coverage = []; selectors = []; inventory = {}
    published_keys = {revision_key(r) for r in published}
    for k, byrow in sorted(groups.items()):
        # Equality is the exact document dictionary, not raw-PDF hash alone.
        common = set.intersection(*[{json.dumps(d, sort_keys=True, ensure_ascii=False) for d in c.evidence_documents} for c in byrow.values()])
        matching = [json.loads(raw) for raw in common if json.loads(raw)['source_id'] == k[0]
                    and any(a['attribute_key'] == k[1] and str(a['raw_value']).strip() == k[3] for a in json.loads(raw)['assertions'])]
        assert len(matching) == 1, 'Contract incompatibility: no unique common selector; stop without revising candidates'
        selector = matching[0]
        assert all(selector in c.evidence_documents for c in byrow.values())
        validate_documents([selector], verify_bytes=True)
        guide = source_inventory[k[0]]; excerpt = excerpts[(k[0], k[3])]
        assert selector['raw_artifact_hash'] == sha(ROOT / guide['retained_path']) == excerpt['document_sha256']
        assert selector['raw_artifact_reference'] == guide['retained_path']
        pages = load(ROOT / guide['extraction_path'])
        assert 'United States' in pages[0] and '2021' in pages[0] and 'WRANGLER' in pages[0]
        assert k[3] in pages[excerpt['pdf_page_1_based'] - 1]
        assert any(a['attribute_key'] == 'factory_powertrain_table' and a['raw_value'] == excerpt['powertrain_table_text'] for a in selector['assertions'])
        assert k not in published_keys, 'Existing exact key found; assess applicability rather than duplicate'
        sp = HERE / 'shared_selectors' / (k[0] + '-' + k[3] + '.document.json')
        save(sp, selector)
        assert load(sp) == selector
        selector_entry = {'key': list(k), 'path': rel(sp), 'file_sha256': sha(sp), 'selector_content_hash': digest(selector),
             'assertion_set_id': selector['assertion_set_id'], 'already_present_in_all_matching_candidates': True,
             'candidate_references': sorted(byrow), 'candidate_count': len(byrow), 'candidate_revisions_required': 0}
        selectors.append(selector_entry)
        payload = {'review_version': '1.0', 'revision_uuid': str(uuid4()), 'correspondence_uuid': str(uuid4()),
             'revision_number': 1, 'supersedes_uuid': None, 'vehicle_model_uuid': str(vm.uuid), 'generation_uuid': str(gen.uuid),
             'source_id': k[0], 'source_namespace': k[1], 'identity_type': k[2], 'native_identifier': k[3],
             'market': 'US', 'start_year': 2021, 'end_year': 2021, 'restrictions': {}, 'evidence': [selector],
             'finding': 'established', 'reviewer': 'Codex MY2021 evidence review; unpublished proposal; owner publication authorization pending',
             'reviewed_at': now,
             'review_notes': 'Unpublished MY2021 US-only finding for the exact retained manufacturer guide/model key. '
                 'Original United States / 2021 / Wrangler body heading and model-code table establish applicability. '
                 'The owner-reviewed US MY2021 Wrangler JL offering context, manufacturer model/body lineage and active canonical JL target (PK32, starts2018) establish the reviewed relation; not a code-prefix or name-only automatic match. '
                 'Earlier-year publications were inspected but do not authorize reuse: their year scopes and source identities differ. '
                 'For 4xe and 392, retain their manufacturer Wrangler Unlimited family headings; no separate model/Generation is invented. '
                 'The exact existing shared selector document is present in every matching current candidate. '
                 'No candidate, classification, source key or raw evidence is revised. Publication requires separate explicit owner authorization.'}
        validate_review_payload(payload)
        assert json.loads(json.dumps(payload, ensure_ascii=False)) == payload
        ch = digest(payload); pp = HERE / 'new_correspondence_proposals' / (k[0] + '-' + k[3] + '.review.json')
        save(pp, {'review': payload, 'content_hash': ch})
        obj = Revision(uuid=payload['revision_uuid'], correspondence_uuid=payload['correspondence_uuid'],
             revision_number=1, vehicle_model=vm, generation=gen, source_id=k[0], source_namespace=k[1],
             identity_type=k[2], native_identifier=k[3], market='US', start_year=2021, end_year=2021,
             restrictions={}, evidence=[selector], finding='established', reviewer=payload['reviewer'],
             reviewed_at=datetime.fromisoformat(now), review_notes=payload['review_notes'], content_hash=ch)
        obj.full_clean(exclude=['content_hash'])
        assert obj.pk is None and obj.content_hash == digest(obj.review_payload())
        assert obj.review_payload() == payload
        objects.append(obj)
        proposal = {'key': list(k), 'proposal': rel(pp), 'proposal_file_sha256': sha(pp), 'content_hash': ch,
             'revision_uuid': payload['revision_uuid'], 'correspondence_uuid': payload['correspondence_uuid'],
             'candidate_count': len(byrow), 'candidate_references': sorted(byrow), 'target_generation_PK': 32,
             'target_generation_uuid': str(gen.uuid), 'shared_selector': rel(sp)}
        proposals.append(proposal)
        coverage.append({**proposal, 'manufacturer_model_code': k[3],
             'body_styles': sorted({rowmap[rid]['body_style'] for rid in byrow}),
             'trim_variants': sorted({rowmap[rid]['marketed_trim_proposal'] for rid in byrow}),
             'applicability': {'market': 'US', 'start_year': 2021, 'end_year': 2021},
             'manufacturer_document': guide['retained_path'], 'source_sha256': guide['sha256'],
             'source_url': guide['url'], 'printed_revision_date': guide['revision_date_printed'],
             'model_table_pdf_page': excerpt['pdf_page_1_based'],
             'manufacturer_model_headings': sorted({c.unknown_fields['research_revision_lineage']['manufacturer_model_heading_exact'] for c in byrow.values()}),
             'existing_correspondences_reused': 0, 'status': 'new unpublished proposal required; exact shared evidence already present'})
        inventory[guide['retained_path']] = guide['sha256']
        inventory[guide['extraction_path']] = sha(ROOT / guide['extraction_path'])
        print('PROPOSED', k[0], k[3], len(byrow), flush=True)
    assert len({tuple(p['key']) for p in proposals}) == len(proposals) == 95
    assert len({o.uuid for o in objects}) == len({o.correspondence_uuid for o in objects}) == 95
    assert not Revision.objects.filter(uuid__in=[o.uuid for o in objects]).exists()
    assert not Revision.objects.filter(correspondence_uuid__in=[o.correspondence_uuid for o in objects]).exists()
    save(HERE / 'correspondence_coverage_matrix.json', {'keys': coverage})
    with (HERE / 'correspondence_coverage_matrix.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['source_id', 'source_namespace', 'identity_type', 'model_code', 'candidate_count', 'candidate_references', 'body_styles', 'trim_variants', 'target_generation_PK', 'proposal'])
        writer.writeheader()
        for c in coverage:
            writer.writerow({'source_id': c['key'][0], 'source_namespace': c['key'][1], 'identity_type': c['key'][2],
                 'model_code': c['key'][3], 'candidate_count': c['candidate_count'], 'candidate_references': '|'.join(c['candidate_references']),
                 'body_styles': '|'.join(c['body_styles']), 'trim_variants': '|'.join(c['trim_variants']),
                 'target_generation_PK': 32, 'proposal': c['proposal']})
    save(HERE / 'existing_correspondence_reuse_assessment.json', {'published_revisions_inspected': 64,
         'published_years': [2018, 2019, 2020], 'existing_correspondences_reusable': 0,
         'MY2021_candidates_covered_by_existing_only': 0, 'same_exact_keys_in_prior_publications': 0,
         'explanation': 'Matching manufacturer model-code text is insufficient. Accepted lookup also uses source_id/namespace/type/native identifier and US/model-year scope; all earlier publications exclude2021, and no exact MY2021 source/model key is published.',
         'records': existing_review})
    save(HERE / 'new_correspondence_proposal_index.json', {'status': 'unpublished; owner review only', 'total': 95, 'proposals': proposals})
    save(HERE / 'shared_selector_index.json', {'total': 95, 'existing_exact_documents_reused': 95,
         'new_candidate_evidence_documents_added': 0, 'candidate_revisions_required': 0, 'selectors': selectors})
    retained_evidence = {}
    for c in candidates.values():
        for d in c.evidence_documents:
            reference = d['raw_artifact_reference']
            assert sha(ROOT / reference) == d['raw_artifact_hash']
            retained_evidence[reference] = d['raw_artifact_hash']
    save(HERE / 'source_and_evidence_hash_inventory.json', {'manufacturer_documents_and_extractions': inventory,
         'all_current_candidate_retained_evidence': retained_evidence,
         'candidate_source_index': rel(LATEST / 'current_candidate_index.json'), 'candidate_source_index_sha256': sha(LATEST / 'current_candidate_index.json'),
         'selectors': [{'path': s['path'], 'file_sha256': s['file_sha256'], 'selector_content_hash': s['selector_content_hash']} for s in selectors]})
    # Inject unsaved proposals only at the lookup seam. Preserve real published
    # lookup and all resolver validation; no fake success or year fallback.
    omitted = set()
    def lookup(model, year, market, identities):
        original = _applicable_revisions(model, year, market, identities)
        keys = {key(i) for i in identities}
        return original + [o for o in objects if revision_key(o) in keys and revision_key(o) not in omitted
                           and o.vehicle_model_id == model.pk and o.market == market and o.start_year <= year <= o.end_year]
    resolutions = []; negatives = []
    with patch('reference.ingestion.generation_correspondence._applicable_revisions', side_effect=lookup):
        for rid, c in candidates.items():
            result = resolve_generation(vm, 2021, 'US', c.generation_evidence, c.evidence_documents,
                                        {'trim_name': c.candidate_identity.trim_name, 'drivetrain': '4WD'})
            assert result['parents']['generation_id'] == 32 and result['parents']['generation_uuid'] == str(gen.uuid)
            assert result['basis'] == 'reviewed_source_correspondence'
            required = {key(i) for i in c.generation_evidence}
            expected = sorted([{'uuid': str(o.uuid), 'hash': o.content_hash} for o in objects if revision_key(o) in required], key=lambda r: r['uuid'])
            assert result['correspondences'] == expected
            resolutions.append({'candidate_reference': rid, 'candidate_artifact': rowmap[rid]['candidate_artifact'],
                 'candidate_hash': rowmap[rid]['candidate_hash'], 'artifact_sha256': rowmap[rid]['artifact_sha256'],
                 'required_source_model_keys': [list(k) for k in sorted(required)],
                 'source_model_key_count': len(required), 'target_generation_PK': 32, 'target_generation_uuid': str(gen.uuid),
                 'basis': result['basis'], 'correspondences': result['correspondences'], 'simulation_only': True,
                 'existing_reused': 0, 'proposed_used': len(expected)})
        for k in sorted(groups):
            rid = sorted(groups[k])[0]; c = candidates[rid]
            omitted.add(k)
            try:
                resolve_generation(vm, 2021, 'US', c.generation_evidence, c.evidence_documents)
            except ValidationError as exc:
                assert exc.messages == ['Missing reviewed generation correspondence.']
            else:
                raise AssertionError('A missing required proposal was accepted')
            omitted.remove(k)
            # Hypothetical metadata-only copy for a negative control; no candidate
            # artifact or classification is edited or serialized as a revision.
            docs = copy.deepcopy(c.evidence_documents)
            selector = next(o.evidence[0] for o in objects if revision_key(o) == k)
            doc = next(d for d in docs if d == selector)
            doc['retrieved_at'] = '2000-01-01T00:00:00+00:00'
            try:
                resolve_generation(vm, 2021, 'US', c.generation_evidence, docs)
            except ValidationError as exc:
                assert exc.messages == ['Correspondence source revision does not match candidate evidence.']
            else:
                raise AssertionError('Non-exact selector dictionary was accepted')
            negatives.append({'key': list(k), 'affected_candidate': rid, 'missing_proposal_rejected': True, 'nonexact_selector_copy_rejected': True})
    prior_records = load(BASE / 'candidate_classification_20261109/approved_field_decision_index.json')['records']
    assert len(prior_records) == 88
    for record in prior_records:
        a = adjudication_from_dict(load(ROOT / record['approved_adjudication']))
        validate_classification_adjudication(a, require_approved=True)
        assert sha(ROOT / record['approved_adjudication']) == record['approved_adjudication_sha256']
        c = candidates[record['research_row_id']]
        human = next(d for d in c.evidence_documents if d['source_id'] == 'human_classification_adjudication')
        active = adjudication_from_dict(load(ROOT / human['raw_artifact_reference']))
        assert active.evidence_anchors['classifications'][record['field']] == record['classification']
    new392 = candidates['JL21-70']
    assert new392.canonical_powertrain['fuel_type'] == 'gasoline'
    assert digest(candidate_config_doc_to_dict(new392)) == 'sha256:d080dbd70cd54daa4d827114d72afb7127b34fbda95e89c0cf7582ac3f8086bd'
    assert len({(c.candidate_identity.trim_name, tuple(c.canonical_powertrain[k] for k in FIELDS), 'US') for c in candidates.values()}) == 73
    assert len([r for r in rows if r['engine_code'] == 'ECX']) == 3
    for r in rows:
        if r['engine_code'] == 'ECX':
            assert not any(d['source_id'] == 'human_classification_adjudication' for d in candidates[r['research_row_id']].evidence_documents)
    for path, expected in baseline.items():
        assert sha(ROOT / path) == expected, path
    assert sha(ROOT / 'db.sqlite3') == dbhash
    after = {'VehicleDefinitions': VehicleDefinition.objects.count(), 'audit_receipts': ImportExecutionReceipt.objects.count(), 'published_correspondences': Revision.objects.count()}
    assert after == counts
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA integrity_check'); assert cursor.fetchone()[0] == 'ok'
        cursor.execute('PRAGMA foreign_key_check'); assert cursor.fetchall() == []
    connection.close()
    assert sha(ROOT / 'db.sqlite3') == dbhash
    save(HERE / 'candidate_resolution_index.json', {'status': 'proposed-state simulation, not published coverage', 'rows': resolutions})
    save(HERE / 'resolution_simulation_report.json', {'result': 'passed', 'candidates': 73, 'resolved_to_generation_32': 73,
         'distinct_source_model_keys': 95, 'distinct_manufacturer_model_codes': 8,
         'existing_correspondences_reused': 0, 'new_proposals': 95, 'shared_selectors_already_present': 95,
         'unmatched_keys_with_combined_state': 0, 'duplicate_proposal_keys': 0, 'conflicting_targets': 0,
         'published_only_current_coverage': current_coverage, 'positive_resolutions': resolutions,
         'negative_controls': negatives, 'negative_control_count': 190,
         'simulation_boundary': 'Only revision lookup is patched to combine unchanged real published lookup with filtered unsaved proposed revisions. Accepted resolver guards and live read-only active parents are unchanged. No publication, model save or receipt function is called.',
         'candidate_modifications': 0, 'classification_modifications': 0, 'candidate_revisions': 0,
         'RHD_dependency': False, 'CLASS_075': 'preserved/deferred', 'database_unchanged': True})
    save(HERE / 'validation_results.json', {'result': 'passed', 'candidate_count': 73, 'complete_five_field_identities': 73,
         'body_distribution': {'2-door': 23, '4-door': 50}, 'body_trim_labels': 24,
         'manufacturer_model_code_candidate_counts': dict(Counter(r['model_code'] for r in rows)),
         'source_model_key_count': 95, 'existing_reusable_correspondences': 0, 'new_proposals': 95,
         'candidate_counts_per_key': [{'key': p['key'], 'candidates': p['candidate_count']} for p in proposals],
         'exact_shared_selector_documents': 95, 'all_73_simulate_to_PK32': True,
         'negative_simulation_controls_passed': 190, 'prior_88_decisions_preserved': True,
         'additional_392_fuel_approval_preserved': True, 'serialization_round_trips': 'passed',
         'source_bytes_and_lineage': 'passed', 'candidate_hashes_unchanged': 73,
         'database_counts_before_and_after': counts, 'database_sha256_before_and_after': dbhash,
         'SQLite_integrity_and_foreign_keys': 'passed', 'preexisting_files_preserved': len(baseline),
         'new_publications': 0, 'new_publication_receipts': 0, 'new_candidates': 0,
         'remaining_contract_incompatibilities': [], 'publication_requires_separate_owner_authorization': True})
    save(HERE / 'publication_recommendations.json', {'status': 'owner review required; not authorization',
         'recommendation': 'Review exactly95 US MY2021-only proposals, then separately authorize publication through the existing workflow if accepted. Fresh applicability/UUID/hash/selector/database checks are required before publication.',
         'existing_correspondences_to_reuse': 0, 'new_correspondences_recommended': 95,
         'candidate_revisions_required': 0, 'unresolved_questions': [],
         'RHD': 'Outside consumer scope; preserve JLUL74/CLASS-075 and do not extend proposal coverage to it',
         'future_boundary': 'No publication, Matrix certification, executable canonical plan, import or backfill is authorized by this package'})
    print('SUCCESS: 73/73 resolve to JL32 in simulation; 95 new proposals; 0 reusable; no candidate or DB changes', flush=True)


if __name__ == '__main__':
    main()
