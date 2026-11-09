"""Bounded MY2021 artifact work using existing builders, contracts and review CLI.

Stages are exclusive: base, approve, validate. No ORM queries or import planning.
All management-command processes use an isolated in-memory database setting.
"""
import copy
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
REVIEW = BASE / 'owner_review_20261108'
ROOT = next(p for p in HERE.parents if (p / 'manage.py').is_file())
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['RIGARCHIVE_TEST_DB_PATH'] = ':memory:'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import django
django.setup()
from django.core.exceptions import ValidationError
from pypdf import PdfReader
from reference.ingestion.contracts import (
    Envelope, SourceMetadata, SourceApplicability, ExtractionProvenance,
    SourceAssertion, SourceAssertionSet, NormalizedInterpretation,
    TechnicalValue, CandidateIdentity, CanonicalImportAdjudication,
)
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.serialization import (
    serialize_artifact, deserialize_artifact, candidate_config_doc_to_dict,
    adjudication_to_dict, adjudication_from_dict, compute_adjudication_hash,
)
from reference.ingestion.validation import validate_candidate_configuration, validate_source_assertion_set
from reference.ingestion.classification_adjudication import (
    validate_classification_adjudication, validate_classification_candidate,
)
from reference.ingestion.importing.powertrain_identity import candidate_powertrain, _supports
from reference.ingestion.generation_correspondence import digest, validate_documents
from reference.powertrain import FIELDS

NOW = datetime.now(timezone.utc).isoformat()
if (HERE / 'authorization.json').exists():
    NOW = json.loads((HERE / 'authorization.json').read_text())['created_at']


def load(p):
    return json.loads(p.read_text())


def rel(p):
    return str(p.relative_to(ROOT))


def sha(p):
    return 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        assert load(p) == value, 'Existing checkpoint differs: ' + rel(p)
        return
    with p.open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False)
        stream.write('\n')


def artifact(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    encoded = serialize_artifact(value)
    assert serialize_artifact(deserialize_artifact(encoded)) == encoded
    if p.exists():
        assert p.read_text() == encoded + '\n', 'Existing artifact differs: ' + rel(p)
        return
    with p.open('x') as stream:
        stream.write(encoded + '\n')


def unchanged():
    baseline = load(HERE / 'preservation_baseline.json')
    for p, expected in baseline['files'].items():
        assert sha(ROOT / p) == expected, p
    assert sha(ROOT / 'db.sqlite3') == baseline['database_sha256']


def reviewed_scope():
    # Reuse the preserved executable preflight; its compatibility finding is
    # retained as an unresolved null, not a reason to omit an authorized base.
    check = subprocess.run([sys.executable, '-B', str(BASE / 'preflight_20261109/verify_preflight.py')],
                           cwd=ROOT, env=os.environ, capture_output=True, text=True, check=True)
    checked = json.loads(check.stdout)
    assert checked['scope_verification'] == 'passed'
    rows = load(REVIEW / 'proposed_consumer_scope.json')['rows']
    approved_ids = {i for g in load(REVIEW / 'owner_approval_table.json')['groups']
                    for i in g['consumer_decision_ids']}
    decisions = [d for d in load(REVIEW / 'classification_review_89_decisions.json')
                 if d['decision_id'] in approved_ids]
    assert len(decisions) == 88 and len({(d['research_row_id'], d['field']) for d in decisions}) == 88
    assert len(rows) == 73 and Counter(r['body_style'] for r in rows) == {'2-door': 23, '4-door': 50}
    assert all(r['model_code'] != 'JLUL74' for r in rows)
    return rows, decisions, checked


def source_set(sid, path, url, native, assertions, *, kind='manufacturer_document', notes=''):
    p = HERE / 'assertion_sets' / (native + '.source_assertion_set.1.1.0.json')
    if p.exists():
        result = deserialize_artifact(p.read_text())
        assert sorted(result.source_assertions, key=lambda a: a.assertion_id) == sorted(assertions, key=lambda a: a.assertion_id)
        result.source_assertions = assertions
        return result
    result = SourceAssertionSet(
        Envelope('rigarchive.source_assertion_set.v1', '1.1.0', NOW, 'MY2021_bounded_construction'),
        SourceMetadata(
            source_id=sid, source_type=kind, source_locator=url, retrieved_at=NOW,
            native_record_id=native, acquisition_method='retained_local_evidence',
            source_use_notes=notes, review_status='reviewed',
            source_applicability=SourceApplicability(
                market='US', applicability_basis='MY2021 US guide applicability; technical/manual joins scoped to exact engine family and source locators',
                publisher_jurisdiction='US', applicability_scope='model_year'),
            extraction_provenance=ExtractionProvenance(
                sha(path), rel(path), 'retained_MY2021_evidence_transcription', '1.0.0',
                'manually_verified_transcription'),
            unknown_fields={'publication_revision': 'Original retained MY2021 source; no cross-year approval propagation'}),
        assertions)
    validate_source_assertion_set(result)
    artifact(p, result)
    return result


def base_stage():
    assert not (HERE / 'base_candidate_index.json').exists(), 'Preserve existing base checkpoint'
    rows, decisions, checked = reviewed_scope()
    files = {rel(p): sha(p) for p in BASE.rglob('*') if p.is_file() and not p.is_relative_to(HERE)}
    save(HERE / 'preservation_baseline.json', {'files': files, 'database_sha256': sha(ROOT / 'db.sqlite3')})
    requirements = (ROOT / 'requirements.txt').read_text().splitlines()
    for requirement in requirements:
        package, version = requirement.split('==')
        assert importlib.metadata.version(package) == version
    save(HERE / 'authorization.json', {
        'created_at': NOW, 'authority': 'Project owner, explicit current-chat MY2021 base construction / classification / final-validation task',
        'scope': '73 US MY2021 Wrangler JL bases, then exact 88 approved field decisions; no publication/planning/import/DB writes',
        'approval_table': rel(REVIEW / 'owner_approval_table.json'),
        'approval_table_sha256': sha(REVIEW / 'owner_approval_table.json'),
        'approved_decision_ids': [d['decision_id'] for d in decisions],
        'approved_labels': sorted({r['marketed_trim_proposal'] for r in rows}),
        'deferred': 'CLASS-075 / JL21-71 / JLUL74; canonical steering/visibility semantics unresolved',
        'workflow': 'Existing Candidate 2.1.0 builder; classification CLI with explicit APPROVE CLASSIFICATIONS under owner authorization',
        'record_count_semantics': '88 individual field decisions bundled in 70 candidate-bound adjudication 1.1 envelopes; one envelope per candidate, no unsupported chaining',
        'fuel_validation_limit': 'JL21-70 fuel_type remains null under explicit unresolved-field rule; premium-octane normalization is not recognized by existing direct-source predicate. No extra fuel adjudication is authorized.',
    })
    save(HERE / 'environment.json', {'python': sys.version, 'executable': sys.executable,
         'django': django.get_version(), 'pypdf': importlib.metadata.version('pypdf'),
         'requirements': requirements, 'requirements_match': True, 'database_setting': ':memory:'})
    save(HERE / 'scope_preflight.json', checked)
    guides = {g['source_id']: g for g in load(BASE / 'source_revision_inventory.json')}
    excerpts = {e['excerpt_id']: e for e in load(BASE / 'evidence_index.json')}
    packages = load(BASE / 'factory_package_availability_excerpts.json')
    cells = load(BASE / 'positive_package_observations.json')
    assessments = {a['engine_code']: a for a in load(REVIEW / 'engine_evidence_assessment.json')}
    trims = {t['normalized_display_name_proposal']: t for t in load(REVIEW / 'trim_edition_review.json')}
    supplementary = {s['source_id']: s for s in load(BASE / 'supplemental_source_inventory.json')}
    additional = {s['source_id']: s for s in load(REVIEW / 'additional_source_index.json')}
    technical_sets = {}
    for sid, source in supplementary.items():
        pages = load(ROOT / source['extraction_path'])
        assertions = [SourceAssertion(f'{sid}-p{n}', 'manufacturer_technical_page', text,
                                     f'PDF page {n}; retained extraction {source["extraction_path"]}')
                      for n, text in enumerate(pages, 1)]
        technical_sets[sid] = source_set(sid, ROOT / source['retained_path'], source['url'], sid, assertions,
            notes='Authentic manufacturer technical PDF. Exact guides govern temporal offering applicability. Page text is preserved; no derived classification asserted.')
    manual_source = additional['Jeep_MY2021_US_owners_manual']
    manual_path = ROOT / manual_source['path']
    manual = PdfReader(manual_path)
    manualset = source_set(manual_source['source_id'], manual_path, manual_source['url'], 'MY2021-manual-fuel-hardware',
        [SourceAssertion(f'manual-p{n}', 'engine_hardware' if n in (143, 145) else 'fuel_requirements',
                         manual.pages[n-1].extract_text(), f'PDF page {n}; Fourth Edition V1, copyright 2022, MY2021 manual; optional equipment does not independently bind engine codes')
         for n in (143, 145, 354)],
        notes='Gasoline fuel section names 2.0L and 3.6L. Hardware sections cover several options; exact code applicability is a human conclusion, never a raw manufacturer assertion. Not a 6.4L fuel source.')
    extra_sets = {}
    for sid in ('Stellantis_MY2021_392_production_release', 'CarAndDriver_MY2021_392_launch', 'CarAndDriver_MY2021_Wrangler_engine_context'):
        source = additional[sid]
        extra_sets[sid] = source_set(sid, ROOT / source['path'], source['url'], sid,
            [SourceAssertion(sid+'-article', 'manufacturer_production_release' if source['kind'].startswith('manufacturer') else 'secondary_technical_report',
                             (ROOT / source['extraction_path']).read_text(), source['locator'])],
            kind=source['kind'], notes=source['scope'] if 'scope' in source else 'Secondary corroboration only; not a direct manufacturer classification.')
    extra_docs = {}
    for sid, source in extra_sets.items():
        from reference.ingestion.normalization.generation import generation_evidence_from_sets
        extra_docs[sid] = generation_evidence_from_sets([source])[1][0]
    save(HERE / 'supporting_documents.json', extra_docs)
    current = []
    for row in rows:
        rid = row['research_row_id']; code = row['engine_code']
        observations = [c for c in cells if (c['model_code'], c['marketed_trim_proposal'], c['engine_code']) ==
                        (row['model_code'], row['marketed_trim_proposal'], code)]
        assert len(observations) == row['positive_observations']
        assert {c['excerpt_id'] for c in observations} == set(row['excerpt_ids'])
        sets = []
        for eid in row['excerpt_ids']:
            e = excerpts[eid]; g = guides[e['source_id']]
            assert e['document_sha256'] == sha(ROOT / e['document']) == g['sha256']
            native = e['source_id'] + '-' + row['model_code']
            observations_here = [c for c in cells if c['excerpt_id'] == eid]
            engine_segments = sorted({(c['engine_code'], c['manufacturer_engine_segment']) for c in observations_here})
            assertions = [SourceAssertion(native+'-table', 'factory_powertrain_table', e['powertrain_table_text'], f'PDF page {e["pdf_page_1_based"]}; manufacturer model heading and named QOP columns'),
                          SourceAssertion(native+'-model', 'source_model_code', row['model_code'], f'PDF page {e["pdf_page_1_based"]}; manufacturer model code'),
                          SourceAssertion(native+'-heading', 'source_document_heading', load(ROOT / g['extraction_path'])[0], 'PDF page 1; United States / MY2021 / Jeep Wrangler / body heading')]
            assertions += [SourceAssertion(native+f'-engine-{n}', 'engine_descriptor', segment,
                             f'PDF page {e["pdf_page_1_based"]}; exact {engine} segment, with transmission/QOP cells retained; no code-only inference')
                           for n, (engine, segment) in enumerate(engine_segments)]
            source = source_set(e['source_id'], ROOT / e['document'], g['url'], native, assertions,
                notes='Manufacturer guide archived copy. Shared model-code selector across marketed grades; grade normalization uses table context, not a code-only identity.')
            sets.append(source)
        primary = sets[-1]
        engine_assertion = next(a for a in primary.source_assertions if a.attribute_key == 'engine_descriptor' and '('+code+')' in a.raw_value)
        table_assertion = next(a for a in primary.source_assertions if a.attribute_key == 'factory_powertrain_table')
        heading = next(a for a in primary.source_assertions if a.attribute_key == 'source_document_heading')
        # Preserve applicable model-specific option/package pages as unmapped
        # evidence. General group/hardware pages are retained by hash/locator in
        # the per-row lineage; they never create extra candidates or mappings.
        model_packages = [p for p in packages if p['source_id'] in row['guide_source_ids'] and p['model_code_context'] == row['model_code']]
        for p in model_packages:
            g = guides[p['source_id']]; native = p['source_id']+f'-package-p{p["pdf_page_1_based"]}'
            sets.append(source_set(p['source_id'], ROOT / g['retained_path'], g['url'], native,
                [SourceAssertion(native, 'factory_package_option_page', p['text'], f'PDF page {p["pdf_page_1_based"]}; model {row["model_code"]}; raw conditions retained, not evaluated')],
                notes='Raw optional-package evidence only. No option/transmission-only baseline is constructed.'))
        relevant_tech = {ref['source_id'] for ref in assessments[code]['source_observation_refs']}
        sets += [technical_sets[sid] for sid in sorted(relevant_tech)]
        if manualset not in sets:
            sets.append(manualset)
        interpretations = []
        values = copy.deepcopy(assessments[code]['directly_supported_normalized_fields'])
        if code == 'ESG':
            values['fuel_type'] = None
        if any(value is not None and not (key == 'fuel_type' and value == 'gasoline')
               and not _supports(engine_assertion.raw_value, key, value, jeep=True)
               for key, value in values.items()):
            # A QOP such as 22L is not engine displacement. Transcribe only the
            # engine column, retaining the original full segment/table as well.
            lines = engine_assertion.raw_value.splitlines()
            boundary = re.search(r'\s{2,}(?:N/C|[\d,]+)\s{2,}', lines[0])
            assert boundary, (rid, 'engine-column boundary unavailable')
            descriptor = '\n'.join(line[:boundary.start()].rstrip() for line in lines)
            narrow = source_set(primary.provenance.source_id,
                ROOT / primary.provenance.extraction_provenance.raw_artifact_reference,
                primary.provenance.source_locator, rid+'-qualified-engine-column',
                [SourceAssertion(rid+'-qualified-engine-column', 'engine_descriptor', descriptor,
                    engine_assertion.source_context+'; engine column only, at original layout boundary; full table/segment separately retained')],
                notes='Faithful engine-column transcription excludes price/transmission/QOP columns; no normalization is inserted into raw manufacturer text.')
            sets.append(narrow)
            engine_assertion = narrow.source_assertions[0]
        for key, value in values.items():
            if value is None:
                continue
            assertion = engine_assertion
            notes = 'Explicit guide engine terminology normalized; exact positive QOP binds engine/transmission/grade. No derived aspiration/nonhybrid conclusion is inserted.'
            if key == 'fuel_type' and value == 'gasoline':
                assertion = next(a for a in manualset.source_assertions if a.assertion_id == 'manual-p354')
                notes = 'Manufacturer gasoline section for the matching 2.0L/3.6L family, joined to exact guide engine and technical unleaded fuel requirement. Chemical fuel only; no hybrid classification from generic manual. 4xe gasoline combustion fuel remains separate from PHEV electrification.'
            assert _supports(assertion.raw_value, key, value, jeep=True), (rid, key)
            interpretations.append(NormalizedInterpretation(rid+'-'+key, assertion.assertion_id, key,
                TechnicalValue(value, 'L', engine_assertion.raw_value) if key == 'engine_displacement_liters' else value,
                raw_source_value=assertion.raw_value, normalization_notes=notes))
        for key, value in [('make', 'Jeep'), ('model', 'Wrangler'), ('model_year', 2021), ('market', 'US')]:
            interpretations.append(NormalizedInterpretation(rid+'-'+key, heading.assertion_id, key, value,
                raw_source_value=heading.raw_value, normalization_notes='Independent US MY2021 manufacturer document heading; not caller-context evidence.'))
        interpretations.append(NormalizedInterpretation(rid+'-trim', table_assertion.assertion_id, 'trim', row['marketed_trim_proposal'],
            raw_source_value=table_assertion.raw_value, normalization_notes='Owner-approved body-aware marketed-grade normalization from exact manufacturer family heading and column/QOP locator; not a verbatim concatenated source quote.'))
        # Four-wheel-drive layout is explicit in each appropriate technical PDF.
        layout_source = next(s for s in sets if s.provenance.source_id in relevant_tech and
                             any('four-wheel drive' in str(a.raw_value).lower() for a in s.source_assertions))
        layout = next(a for a in layout_source.source_assertions if 'four-wheel drive' in str(a.raw_value).lower())
        interpretations.append(NormalizedInterpretation(rid+'-drive', layout.assertion_id, 'generic_drive_classification', '4WD',
            raw_source_value=layout.raw_value, normalization_notes='Manufacturer model/body layout; optional transfer-case equipment does not create a new baseline.'))
        candidate = construct_candidate_configuration(
            CandidateIdentity('Jeep', 'Wrangler', model_year=2021, market='US', trim_name=row['marketed_trim_proposal']),
            sets, interpretations, candidate_reference=rid, created_at=NOW, schema_version='2.1.0')
        trim = trims[row['marketed_trim_proposal']]
        candidate.unknown_fields['research_revision_lineage'] = {
            'research_row': row, 'research_matrix': rel(BASE / 'preliminary_factory_offerings.json'),
            'research_matrix_sha256': sha(BASE / 'preliminary_factory_offerings.json'),
            'manufacturer_model_heading_exact': trim['manufacturer_model_heading_exact'],
            'manufacturer_column_labels_or_locators': trim['manufacturer_column_labels_or_locators'],
            'normalized_display_name': row['marketed_trim_proposal'],
            'normalization_notice': trim['manufacturer_name_notice'],
            'approval_authority': rel(HERE / 'authorization.json'),
            'positive_QOP_observations': observations,
            'package_inventory': rel(BASE / 'factory_package_availability_excerpts.json'),
            'package_inventory_sha256': sha(BASE / 'factory_package_availability_excerpts.json'),
            'applicable_package_page_locators': [{'source_id': p['source_id'], 'source_sha256': p['source_sha256'], 'pdf_page_1_based': p['pdf_page_1_based']}
                for p in packages if p['source_id'] in row['guide_source_ids'] and p['model_code_context'] in (None, row['model_code'])],
            'fuel_validation_limitation': 'Reviewed gasoline normalization cannot pass unchanged premium-octane direct-source predicate; fuel_type deliberately null' if code == 'ESG' else None,
        }
        validate_candidate_configuration(candidate)
        assert candidate_powertrain(candidate, verify_bytes=True) == values
        path = HERE / 'base_candidates' / (rid+'.base-r1.candidate.2.1.0.json')
        artifact(path, candidate)
        entry = {**row, 'candidate_artifact': rel(path), 'candidate_hash': digest(candidate_config_doc_to_dict(candidate)),
                 'artifact_sha256': sha(path), 'canonical_powertrain': values,
                 'unresolved_fields': [k for k, v in values.items() if v is None],
                 'source_assertion_sets': [rel(HERE / 'assertion_sets' / (s.provenance.native_record_id+'.source_assertion_set.1.1.0.json')) for s in sets]}
        current.append(entry)
        print('BASE', rid, entry['unresolved_fields'], flush=True)
    assert len(current) == 73
    assert sum(len(r['unresolved_fields']) for r in current) == 89  # 88 approved plus unapproved fuel validation gap
    save(HERE / 'base_candidate_index.json', {'created_at': NOW, 'candidate_contract': '2.1.0', 'rows': current})
    save(HERE / 'base_validation.json', {'result': 'passed; unresolved values remain null', 'base_candidates': 73,
         'distribution': {'2-door': 23, '4-door': 50}, 'labels': 24, 'serialization_and_evidence_hashes': 'passed',
         'approved_fields_left_null': 88, 'additional_null': 'JL21-70 fuel_type; explicit unresolved-field rule',
         'complete_ECX_bases': 3, 'RHD_candidates': 0})
    unchanged()


def approve_stage():
    assert not (HERE / 'current_candidate_index.json').exists(), 'Preserve current checkpoint'
    rows, decisions, _ = reviewed_scope()
    unchanged()
    base_index = load(HERE / 'base_candidate_index.json')['rows']
    assert load(HERE / 'base_validation.json')['base_candidates'] == 73
    groups = {g['group_id']: g for g in load(REVIEW / 'classification_groups.json')}
    supporting = load(HERE / 'supporting_documents.json')
    current = []; execution = []; individual = []
    for row in base_index:
        rid = row['research_row_id']
        assert sha(ROOT / row['candidate_artifact']) == row['artifact_sha256']
        base = deserialize_artifact((ROOT / row['candidate_artifact']).read_text())
        assert digest(candidate_config_doc_to_dict(base)) == row['candidate_hash']
        candidate_powertrain(base, verify_bytes=True)
        applicable = [d for d in decisions if d['research_row_id'] == rid]
        entry = copy.deepcopy(row)
        entry['base_candidate_artifact'] = row['candidate_artifact']
        entry['base_candidate_hash'] = row['candidate_hash']
        if not applicable:
            assert row['engine_code'] == 'ECX'
            candidate_powertrain(base, complete=True, verify_bytes=True)
            entry.update(status='complete; direct ECX technical evidence retained', superseded_artifacts=[])
            current.append(entry)
            continue
        claims = {}
        # The existing adjudication contract requires a nonempty supporting
        # list even when those authentic technical documents are already in the
        # base. The projector deduplicates identical documents.
        extra = [d for d in base.evidence_documents if d['source_id'].startswith('FCA_MY2021_')]
        for decision in applicable:
            group = groups[decision['group_id']]
            for sid in group['additional_source_ids'] + group['secondary_corroboration_refs']:
                if sid in supporting and supporting[sid] not in extra:
                    extra.append(supporting[sid])
            documents = base.evidence_documents + extra
            refs = ['|'.join((d['source_id'], d['raw_artifact_hash'], d['assertion_set_id'], a['assertion_id']))
                    for d in documents for a in d['assertions']]
            key = decision['field']
            assert key not in claims and base.canonical_powertrain[key] is None
            claims[key] = {'value': decision['proposed_value'], 'reasoning': group['derived_reasoning'],
                'applicability': group['applicability'] + f' Exact candidate {rid}; digest {row["candidate_hash"]}; engine {row["engine_code"]}; model {row["model_code"]}; {row["body_style"]} {row["marketed_trim_proposal"]}; QOP {",".join(row["quick_order_packages"])}.',
                'limitations': group['limitations'], 'confidence': 'moderate',
                'source_assertion_refs': refs, 'evidence_status': 'supported'}
        proposal = CanonicalImportAdjudication(
            adjudication_version='1.1', created_at=NOW, operator_label='pending_human_signoff',
            candidate_reference=rid,
            source_identity={'source_id': 'human_classification_adjudication', 'source_identity_type': 'candidate_digest', 'native_identifier': row['candidate_hash']},
            original_review_category='missing_classification', adjudication_category='evidence_backed_classification',
            adjudication_decision='proposed_classifications', adjudicated_trim_name=row['marketed_trim_proposal'],
            adjudication_notes='Exact owner-approved MY2021 US derived conclusions; retained proposal binds the reviewed field IDs to this base digest. No fuel adjudication or import authorization.',
            evidence_anchors={'candidate_artifact_reference': row['candidate_artifact'], 'candidate_hash': row['candidate_hash'],
                              'supporting_documents': extra, 'classifications': claims})
        proposal.adjudication_hash = compute_adjudication_hash(adjudication_to_dict(proposal))
        validate_classification_adjudication(proposal)
        pp = HERE / 'proposals' / (rid+'.proposed-r1.adjudication.1.1.json')
        save(pp, adjudication_to_dict(proposal))
        ap = HERE / 'adjudications' / (rid+'.approved-r1.adjudication.1.1.json')
        cp = HERE / 'classified_candidates' / (rid+'.approved-r1.candidate.2.1.0.json')
        log = HERE / 'cli_audit' / (rid+'.txt'); log.parent.mkdir(exist_ok=True)
        command = [str(ROOT / '.venv/bin/python'), '-B', str(ROOT / 'manage.py'), 'adjudicate_canonical_import',
                   '--classification-review', rel(pp), '--operator', 'project_owner', '--output', rel(ap),
                   '--candidate-output', rel(cp), '--skip-checks']
        result = subprocess.run(command, input='APPROVE CLASSIFICATIONS\n', capture_output=True, text=True, cwd=ROOT, env=os.environ, timeout=60)
        with log.open('x') as stream:
            stream.write(result.stdout + result.stderr)
        assert result.returncode == 0, 'Approval failed: ' + rel(log)
        approved = adjudication_from_dict(load(ap))
        validate_classification_adjudication(approved, require_approved=True)
        assert approved.evidence_anchors == proposal.evidence_anchors
        before = adjudication_to_dict(proposal); after = adjudication_to_dict(approved)
        assert {k for k in before if before[k] != after[k]} == {'adjudication_decision', 'operator_label', 'created_at', 'adjudication_hash'}
        candidate = deserialize_artifact(cp.read_text())
        validate_classification_candidate(candidate)
        candidate_powertrain(candidate, verify_bytes=True)
        assert candidate.candidate_identity == base.candidate_identity
        expected = dict(base.canonical_powertrain)
        expected.update({k: v['value'] for k, v in claims.items()})
        assert candidate.canonical_powertrain == expected
        assert serialize_artifact(deserialize_artifact(serialize_artifact(candidate))) == serialize_artifact(candidate)
        entry.update(candidate_artifact=rel(cp), candidate_hash=digest(candidate_config_doc_to_dict(candidate)),
                     artifact_sha256=sha(cp), canonical_powertrain=expected,
                     unresolved_fields=[k for k, v in expected.items() if v is None],
                     approved_adjudication=rel(ap), approved_adjudication_hash=approved.adjudication_hash,
                     approved_adjudication_sha256=sha(ap),
                     superseded_artifacts=[{'artifact': row['candidate_artifact'], 'candidate_hash': row['candidate_hash'],
                                            'artifact_sha256': row['artifact_sha256'], 'reason': 'Exact owner-approved human classifications; original base preserved'}],
                     status='complete' if all(v is not None for v in expected.values()) else 'blocked: unresolved fuel_type')
        current.append(entry)
        execution.append({'candidate_reference': rid, 'base': row['candidate_artifact'], 'base_hash': row['candidate_hash'],
             'proposal': rel(pp), 'approved_adjudication': rel(ap), 'approved_adjudication_hash': approved.adjudication_hash,
             'revision': rel(cp), 'revision_hash': entry['candidate_hash'], 'field_decisions': len(claims), 'cli_audit': rel(log), 'exit_code': 0})
        for decision in applicable:
            record = {'decision_id': decision['decision_id'], 'research_row_id': rid, 'engine_code': row['engine_code'],
                      'field': decision['field'], 'classification': claims[decision['field']],
                      'approved_adjudication': rel(ap), 'approved_adjudication_hash': approved.adjudication_hash,
                      'approved_adjudication_sha256': sha(ap), 'base_candidate': row['candidate_artifact'],
                      'base_candidate_hash': row['candidate_hash'], 'current_candidate': rel(cp),
                      'current_candidate_hash': entry['candidate_hash'], 'authority': rel(HERE / 'authorization.json')}
            save(HERE / 'approved_field_decisions' / (decision['decision_id']+'.approved-r1.json'), record)
            individual.append(record)
        assert sha(ROOT / 'db.sqlite3') == load(HERE / 'preservation_baseline.json')['database_sha256']
        print('APPROVED', rid, len(claims), flush=True)
    assert len(current) == 73 and len(execution) == 70 and len(individual) == 88
    assert len({r['decision_id'] for r in individual}) == 88
    save(HERE / 'current_candidate_index.json', {'created_at': NOW, 'candidate_contract': '2.1.0', 'rows': current})
    save(HERE / 'approval_application_index.json', {'approved_field_decisions': 88, 'approved_adjudication_envelopes': 70,
         'candidate_revisions_created': 70, 'unchanged_ECX_candidates': 3, 'executions': execution})
    save(HERE / 'approved_field_decision_index.json', {'records': individual})
    unchanged()


def validate_stage():
    rows, decisions, _ = reviewed_scope()
    unchanged()
    bases = load(HERE / 'base_candidate_index.json')['rows']
    current = load(HERE / 'current_candidate_index.json')['rows']
    expected_ids = {r['research_row_id'] for r in rows}
    assert {r['research_row_id'] for r in current} == {r['research_row_id'] for r in bases} == expected_ids
    assert len(current) == len(bases) == 73
    assert len(list((HERE / 'base_candidates').glob('*.json'))) == 73
    assert len(list((HERE / 'classified_candidates').glob('*.json'))) == 70
    assert len(list((HERE / 'adjudications').glob('*.json'))) == 70
    assert len(list((HERE / 'approved_field_decisions').glob('*.json'))) == 88
    evidence = []; incomplete = []; unique = set(); source_sets = set()
    for row in current:
        assert sha(ROOT / row['candidate_artifact']) == row['artifact_sha256']
        candidate = deserialize_artifact((ROOT / row['candidate_artifact']).read_text())
        validate_candidate_configuration(candidate)
        values = candidate_powertrain(candidate, verify_bytes=True)
        assert digest(candidate_config_doc_to_dict(candidate)) == row['candidate_hash']
        assert values == row['canonical_powertrain']
        assert (candidate.candidate_identity.manufacturer_name, candidate.candidate_identity.vehicle_model_name,
                candidate.candidate_identity.model_year, candidate.candidate_identity.market, candidate.candidate_identity.trim_name) == (
                    'Jeep', 'Wrangler', 2021, 'US', row['marketed_trim_proposal'])
        assert row['model_code'] != 'JLUL74' and candidate.candidate_reference != 'JL21-71'
        assert serialize_artifact(deserialize_artifact(serialize_artifact(candidate))) == serialize_artifact(candidate)
        key = (row['marketed_trim_proposal'], tuple(values[k] for k in FIELDS), 'US')
        assert key not in unique; unique.add(key)
        try:
            candidate_powertrain(candidate, complete=True, verify_bytes=True)
        except ValidationError as exc:
            incomplete.append({'research_row_id': row['research_row_id'], 'fields': row['unresolved_fields'], 'error': exc.messages})
        base_row = next(b for b in bases if b['research_row_id'] == row['research_row_id'])
        assert sha(ROOT / base_row['candidate_artifact']) == base_row['artifact_sha256']
        base = deserialize_artifact((ROOT / base_row['candidate_artifact']).read_text())
        assert digest(candidate_config_doc_to_dict(base)) == base_row['candidate_hash']
        assert base.candidate_identity == candidate.candidate_identity
        lineage = candidate.unknown_fields['research_revision_lineage']
        assert lineage == base.unknown_fields['research_revision_lineage']
        assert lineage['research_row']['research_row_sha256'] == row['research_row_sha256']
        assert lineage['research_matrix_sha256'] == sha(ROOT / lineage['research_matrix'])
        assert lineage['package_inventory_sha256'] == sha(ROOT / lineage['package_inventory'])
        if row['engine_code'] == 'ECX':
            assert row['candidate_artifact'] == base_row['candidate_artifact']
            assert not any(d['source_id'] == 'human_classification_adjudication' for d in candidate.evidence_documents)
            assert values == {'engine_displacement_liters': '2', 'engine_cylinders': 4, 'engine_aspiration': 'turbocharged', 'fuel_type': 'gasoline', 'electrification_type': 'plug_in_hybrid'}
        else:
            adj = adjudication_from_dict(load(ROOT / row['approved_adjudication']))
            validate_classification_adjudication(adj, require_approved=True)
            assert adjudication_to_dict(adjudication_from_dict(adjudication_to_dict(adj))) == adjudication_to_dict(adj)
            assert sha(ROOT / row['approved_adjudication']) == row['approved_adjudication_sha256']
            assert adj.evidence_anchors['candidate_hash'] == base_row['candidate_hash']
            assert adj.evidence_anchors['candidate_artifact_reference'] == base_row['candidate_artifact']
            expected = {d['field']: d['proposed_value'] for d in decisions if d['research_row_id'] == row['research_row_id']}
            assert {k: v['value'] for k, v in adj.evidence_anchors['classifications'].items()} == expected
            assert all(v['confidence'] == 'moderate' and v['reasoning'] and v['limitations'] and v['source_assertion_refs'] for v in adj.evidence_anchors['classifications'].values())
        source_sets.update(row['source_assertion_sets'])
        evidence.append({'candidate_reference': row['research_row_id'], 'current_candidate': row['candidate_artifact'],
             'candidate_hash': row['candidate_hash'], 'base_candidate': base_row['candidate_artifact'],
             'base_candidate_hash': base_row['candidate_hash'], 'manufacturer_model_code': row['model_code'],
             'manufacturer_model_heading_exact': lineage['manufacturer_model_heading_exact'],
             'manufacturer_column_labels_or_locators': lineage['manufacturer_column_labels_or_locators'],
             'normalized_display_name': row['marketed_trim_proposal'],
             'quick_order_packages': row['quick_order_packages'], 'engine_transmission_pairings': row['engine_transmission_pairings'],
             'positive_observation_count': len(lineage['positive_QOP_observations']),
             'evidence_documents': [{'source_id': d['source_id'], 'raw_artifact_reference': d['raw_artifact_reference'],
                                    'raw_artifact_hash': d['raw_artifact_hash'], 'assertion_set_id': d['assertion_set_id'],
                                    'assertion_count': len(d['assertions'])} for d in candidate.evidence_documents]})
    for p in source_sets:
        source = deserialize_artifact((ROOT / p).read_text())
        validate_source_assertion_set(source)
        assert serialize_artifact(deserialize_artifact(serialize_artifact(source))) == serialize_artifact(source)
    records = load(HERE / 'approved_field_decision_index.json')['records']
    assert {d['decision_id'] for d in records} == {d['decision_id'] for d in decisions}
    assert len(records) == 88
    for record in records:
        assert load(HERE / 'approved_field_decisions' / (record['decision_id']+'.approved-r1.json')) == record
        adj = adjudication_from_dict(load(ROOT / record['approved_adjudication']))
        assert adj.evidence_anchors['classifications'][record['field']] == record['classification']
        assert record['approved_adjudication_hash'] == adj.adjudication_hash
        assert record['approved_adjudication_sha256'] == sha(ROOT / record['approved_adjudication'])
    assert incomplete and len(incomplete) == 1 and incomplete[0]['research_row_id'] == 'JL21-70' and incomplete[0]['fields'] == ['fuel_type']
    earlier = load(REVIEW / 'completeness_reconciliation.json')['earlier_only_rows']
    assert len(earlier) == 24 and {r['research_row_id'] for r in earlier} <= expected_ids
    save(HERE / 'evidence_lineage_report.json', {'rows': evidence, 'applicable_assertion_sets_validated': len(source_sets)})
    save(HERE / 'superseded_artifact_index.json', {'rows': [{'candidate_reference': r['research_row_id'], 'current': r['candidate_artifact'], 'superseded': r['superseded_artifacts']} for r in current]})
    save(HERE / 'sport_RHD_preservation.json', {'status': 'preserved and deferred; no Candidate constructed',
         'original_record': rel(REVIEW / 'preserved_RHD_scope.json'), 'original_record_sha256': sha(REVIEW / 'preserved_RHD_scope.json'),
         'discovery_row': next(r for r in load(BASE / 'preliminary_factory_offerings.json') if r['research_row_id'] == 'JL21-71'),
         'deferred_decision': next(d for d in load(REVIEW / 'classification_review_89_decisions.json') if d['decision_id'] == 'CLASS-075'),
         'restrictions': 'No fleet-only/postal-only assertion. Steering/public visibility and canonical representation unresolved.',
         'original_discovery_preservation': rel(HERE / 'preservation_baseline.json')})
    save(HERE / 'validation_results.json', {'status': 'partial: final five-field validation blocked for one candidate',
         'base_candidates': 73, 'current_candidates': 73, 'candidate_revisions': 70,
         'approved_decisions': 88, 'approved_adjudication_envelopes': 70, 'individual_decision_records': 88,
         'body_style_distribution': dict(Counter(r['body_style'] for r in current)),
         'approved_body_trim_labels': len({r['marketed_trim_proposal'] for r in current}),
         'complete_five_field_identities': 72, 'incomplete_candidates': incomplete,
         'earlier_only_combinations_preserved': 24, 'unchanged_ECX_candidates': 3,
         'RHD_candidates': 0, 'deferred_RHD_decisions': 1, 'candidate_uniqueness': 73,
         'contracts_serialization_bytes_and_lineage': 'passed for all 73 current candidates and 73 bases',
         'all_preexisting_files_preserved': True, 'database_unchanged': True,
         'database_sha256': sha(ROOT / 'db.sqlite3'),
         'generation_correspondences_published': 0, 'canonical_records_created': 0, 'executable_import_plans_created': 0,
         'remaining_blocker': 'JL21-70 gasoline fuel normalization rejected by unchanged direct-source predicate; null retained. Separate evidence acquisition or bounded validator correction authorization needed before full completion/correspondence preparation.'})
    unchanged()
    print('VALIDATED: 73 bases, 88 decisions, 70 revisions, 73 current candidates; 72 complete, one fuel_type null', flush=True)


if __name__ == '__main__':
    {'base': base_stage, 'approve': approve_stage, 'validate': validate_stage}[sys.argv[1]]()
