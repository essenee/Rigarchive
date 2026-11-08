"""MY2019 review artifacts only. Run from repository root; never publish/import.

Uses inspected PDFs in /private/tmp for compact evidence retention. Refuses to
replace an output revision. All live database access is SQLite URI mode=ro.
"""
import copy
import csv
import hashlib
import json
import os
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['RIGARCHIVE_TEST_DB_PATH'] = ':memory:'
import django
django.setup()
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connections
from pypdf import PdfReader
from reference.ingestion.contracts import (Envelope, SourceMetadata, SourceApplicability,
    ExtractionProvenance, SourceAssertion, SourceAssertionSet, NormalizedInterpretation)
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.serialization import serialize_artifact, deserialize_artifact, candidate_config_doc_to_dict
from reference.ingestion.validation import validate_candidate_configuration, validate_source_assertion_set
from reference.ingestion.generation_correspondence import digest, validate_documents, validate_review_payload, resolve_generation
from reference.ingestion.importing.powertrain_identity import candidate_powertrain, identity_proof
from reference.ingestion.importing.planner import plan_candidate_import
from reference.models import Generation, GenerationCorrespondenceRevision, VehicleDefinition, ImportExecutionReceipt

BASE = ROOT / 'docs/implementation/handoffs/MY2019_JL/director_review'
OLD = BASE / 'compact_evidence_revision_2'
OUT = BASE / 'evidence_review_20261108'
if OUT.exists():
    raise SystemExit('Refusing to overwrite an existing review revision.')
baseline = hashlib.sha256((ROOT / 'db.sqlite3').read_bytes()).hexdigest()
prior = {str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest()
         for p in BASE.rglob('*') if p.is_file()}
connections.close_all()
settings.DATABASES['default']['NAME'] = 'file:' + str(ROOT / 'db.sqlite3') + '?mode=ro'
settings.DATABASES['default']['OPTIONS'] = {'uri': True}
with connections['default'].cursor() as cursor:
    cursor.execute('PRAGMA query_only=ON')
    cursor.execute('PRAGMA query_only')
    assert cursor.fetchone()[0] == 1
now = datetime.now(timezone.utc).isoformat()
generation = Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32)
vm = generation.vehicle_model
assert generation.name == 'JL' and generation.is_active and generation.start_year <= 2019
assert generation.end_year is None or generation.end_year >= 2019

# Validate all existing inputs without rewriting them.
originals = []
source_count = 0
for cp in sorted(OLD.glob('*.candidate.json')):
    c = deserialize_artifact(cp.read_text())
    validate_candidate_configuration(c)
    candidate_powertrain(c, verify_bytes=True)
    assert serialize_artifact(deserialize_artifact(serialize_artifact(c))) == serialize_artifact(c)
    sets = [deserialize_artifact(p.read_text()) for p in sorted(OLD.glob(cp.stem.split('.')[0] + '.source_assertion_set_*.json'))]
    for s in sets:
        validate_source_assertion_set(s)
    source_count += len(sets)
    originals.append((cp.name.split('.')[0], c, sets))
assert len(originals) == 19 and source_count == 32

# Inspect printed applicability, not the URL locale or a search-engine rewrite.
manual_url = 'https://vehicleinfo.mopar.com/assets/publications/en-ca/Jeep/2019/Wrangler/10387.pdf'
spec_url = 'https://s3.amazonaws.com/chryslermedia.iconicweb.com/mediasite/specs/2019_JP_Wrangler_SPmk1alba10mregeqq9v39oek881.pdf'
manual = PdfReader('/private/tmp/rigarchive-2019-wrangler-userguide.pdf')
cover = manual.pages[0].extract_text()
fuel = manual.pages[247].extract_text()
spec = PdfReader('/private/tmp/rigarchive-2019-wrangler-specs.pdf')
spec1 = spec.pages[0].extract_text(extraction_mode='layout')
assert '19JL-926-AA' in cover and '2019' in cover and 'Jeep.com (U.S.)' in cover
assert '2.0L Engine' in fuel and '3.6L Engine' in fuel
assert 'gasoline' in fuel.split('3.6L Engine')[0] and 'gasoline' in fuel.split('3.6L Engine')[1]
assert '2019' in spec1 and 'four-wheel drive' in spec1 and '(2-door)' in spec1 and '(4-door)' in spec1
OUT.mkdir()
(OUT / 'evidence').mkdir()
(OUT / 'candidates').mkdir()
(OUT / 'correspondence_proposals').mkdir()

def write(name, value):
    p = OUT / name
    p.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    return p

fuel_path = write('evidence/mopar_2019_fuel_selected_facts.json', {
    'representation': 'Reviewed selected facts and short source lexemes; not original PDF bytes',
    'source_url': manual_url, 'retrieved_at': now, 'publisher': 'FCA US LLC / Mopar',
    'title': '2019 New Wrangler User Guide', 'edition': '19JL-926-AA, First Edition',
    'applicability': 'Printed cover identifies MY2019 New Wrangler, US and Canada owner resources; body-neutral engine instructions.',
    'printed_page': 246, 'pdf_page_one_based': 248,
    'facts': [{'engine_heading': '2.0L Engine', 'fuel_type_lexeme': 'gasoline'},
              {'engine_heading': '3.6L Engine', 'fuel_type_lexeme': 'gasoline'}],
    'review': 'Both engine subsections expressly prescribe regular unleaded gasoline; the 2.0L subsection additionally recommends premium for performance. No fuel inferred from a fuel-door/tank label.',
    'join_basis': 'Manufacturer MY2019 model-wide instructions for the two named engines, corroborated by MY2019 manufacturer specifications identifying these engines as standard/available across all models and both body styles. Existing accepted order-guide inventory establishes their actual trim offerings; no cross-product construction.',
    'original_pdf_retained_for_contract': False,
})
drive_path = write('evidence/jeep_2019_specification_selected_facts.json', {
    'representation': 'Reviewed selected facts and short source lexemes; not original PDF bytes',
    'source_url': spec_url, 'retrieved_at': now, 'publisher': 'FCA US LLC / Jeep',
    'title': '2019 Jeep Wrangler Specifications', 'printed_revision_date': None,
    'printed_page': 1, 'layout_lexeme': 'Longitudinal front engine, four-wheel drive',
    'body_scope': 'The same page explicitly lists both two-door and four-door tank capacities and towing weights.',
    'engine_scope': 'Manufacturer specifications identify the 3.6L as standard on all models and the 2.0L as available on all models (pages 1 and 2).',
    'interpretation': '4WD, independent of transfer-case subtype and transmission.',
    'limitations': 'No naturally aspirated or nonhybrid assertion is present. Do not infer either from silence. Printed title is MY2019; the web search viewer incorrectly rewrote this URL to a MY2018 document, so downloaded bytes and printed heading were checked directly.',
    'original_pdf_retained_for_contract': False,
})

def new_set(source_id, path, set_id, assertions, applicability, locator, revision):
    h = 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
    return SourceAssertionSet(Envelope('rigarchive.source_assertion_set.v1', '1.1.0', created_at=now),
        SourceMetadata(source_id, source_type='manufacturer_specification' if source_id != 'reviewed_jeep_order_guide_inventory' else 'reviewed_research_transcription',
            source_locator=locator, retrieved_at=now, native_record_id=set_id,
            acquisition_method='local_file', review_status='reviewed_selected_facts',
            source_use_notes='Hash verifies retained representation; not a PDF hash or independent corroboration.',
            source_applicability=SourceApplicability(market='US', applicability_scope='model_year', applicability_basis=applicability),
            extraction_provenance=ExtractionProvenance(h, str(path.relative_to(ROOT)), 'my2019_reviewed_selected_facts', '1.0.0', 'manually_verified_transcription'),
            unknown_fields={'publication_revision': revision}), assertions)

fuel_set = new_set('mopar_2019_wrangler_user_guide', fuel_path, 'MY2019-JL-fuel', [
    SourceAssertion('fuel_ec3', 'fuel_type', 'gasoline', manual_url + '; printed p246, 2.0L Engine; US/Canada edition 19JL-926-AA'),
    SourceAssertion('fuel_erc', 'fuel_type', 'gasoline', manual_url + '; printed p246, 3.6L Engine; US/Canada edition 19JL-926-AA'),
], 'Printed MY2019 US/Canada cover; named engine sections apply across body styles; accepted inventory establishes offering linkage.', manual_url, '19JL-926-AA First Edition')
drive_set = new_set('jeep_2019_wrangler_specifications', drive_path, 'MY2019-JL-drive', [
    SourceAssertion('drive_all_models', 'drive_descriptor', 'Longitudinal front engine, four-wheel drive', spec_url + '; printed p1 BODY/CHASSIS Layout; same page explicitly covers both body styles'),
], 'MY2019 US manufacturer model specifications, all models and both bodies; commercial market independently established by retained US order guides.', spec_url, 'MY2019; no printed revision date')
for name, s in [('fuel', fuel_set), ('drive', drive_set)]:
    validate_source_assertion_set(s)
    (OUT / (name + '.source_assertion_set.json')).write_text(serialize_artifact(s) + '\n')

# A common selector document makes one review per model code usable for every
# affected candidate. It references the same accepted inventory, never a new source.
common = {}
old_mapping = {}
for rid, c, sets in originals:
    code = next(a.raw_value for a in sets[0].source_assertions if a.attribute_key == 'source_model_code')
    if code in common:
        continue
    prior_revision = GenerationCorrespondenceRevision.objects.get(
        source_id='jeep_usa', source_namespace='source_model_code', native_identifier=code,
        start_year=2018, end_year=2018, finding='established', generation=generation)
    assert prior_revision.content_hash == digest(prior_revision.review_payload())
    validate_documents(prior_revision.evidence, verify_bytes=True)
    old_mapping[code] = {'uuid': str(prior_revision.uuid), 'hash': prior_revision.content_hash,
                         'year_scope': [2018, 2018], 'generation_uuid': str(generation.uuid)}
    ep = sets[0].provenance.extraction_provenance
    common[code] = new_set('reviewed_jeep_order_guide_inventory', ROOT / ep.raw_artifact_reference,
        'MY2019-common-' + code, [SourceAssertion('common_model_code', 'source_model_code', code,
        'Accepted MY2019 US JL inventory, manufacturer model-code column; common selector shared across this model-code group.')],
        'Director-accepted MY2019 US JL dated-revision inventory; scope is exactly this retained manufacturer model code.',
        sets[0].provenance.source_locator, 'Accepted MY2019 union; historical edition details remain in original inventory')
    validate_source_assertion_set(common[code])
    (OUT / (code + '.source_assertion_set.json')).write_text(serialize_artifact(common[code]) + '\n')

rows, proofs, candidates = [], [], []
for rid, previous, old_sets in originals:
    code = next(a.raw_value for a in old_sets[0].source_assertions if a.attribute_key == 'source_model_code')
    ec3 = previous.canonical_powertrain['engine_displacement_liters'] == '2'
    interps = copy.deepcopy(previous.normalized_assertions)
    for i in interps:
        qualifier, local = i.source_assertion_ref.rsplit('|', 1)
        i.source_assertion_ref = local
        i.interpretation_id = i.interpretation_id.rsplit('|', 1)[-1]
        i.unknown_fields['document_qualifier'] = qualifier + '|'
    interps.append(NormalizedInterpretation('i_verified_fuel', 'fuel_ec3' if ec3 else 'fuel_erc', 'fuel_type',
        'gasoline', raw_source_value='gasoline', normalization_notes='Explicit named-engine gasoline statement, printed p246; no inference from tank equipment.'))
    if code.endswith('72'):
        interps.append(NormalizedInterpretation('i_verified_drive', 'drive_all_models', 'generic_drive_classification',
            '4WD', raw_source_value='Longitudinal front engine, four-wheel drive',
            normalization_notes='Manufacturer model-wide MY2019 statement explicitly covering both body styles; no four-door order-guide extrapolation.'))
    sources = old_sets + [fuel_set, drive_set, common[code]]
    c = construct_candidate_configuration(previous.candidate_identity, sources, interps,
        candidate_reference=previous.candidate_reference + '-review-r3', created_at=now, schema_version='2.1.0')
    validate_candidate_configuration(c)
    candidate_powertrain(c, verify_bytes=True)
    text = serialize_artifact(c)
    assert serialize_artifact(deserialize_artifact(text)) == text
    (OUT / 'candidates' / (rid + '.candidate.json')).write_text(text + '\n')
    plan = plan_candidate_import(c)
    peers = list(VehicleDefinition.objects.filter(generation=generation, model_year=2019,
        market='US', trim_name=c.candidate_identity.trim_name, drivetrain='4WD').order_by('pk'))
    try:
        proof = identity_proof(c, peers)
        proof_error = None
    except ValidationError as e:
        proof, proof_error = None, e.messages
    row = {'row_id': rid, 'trim_name': c.candidate_identity.trim_name,
        'body': 'two-door' if code.endswith('72') else 'four-door', 'engine_code': 'EC3' if ec3 else 'ERC',
        'source_model_code': code, 'candidate_reference': c.candidate_reference,
        'candidate_digest': digest(candidate_config_doc_to_dict(c)),
        'candidate_valid': True, 'retained_bytes_verified': True, 'round_trip_verified': True,
        'canonical_powertrain': c.canonical_powertrain, 'drivetrain': '4WD',
        'engine_tuple_complete': proof is not None, 'engine_proof_error': proof_error,
        'peer_ids': [p.pk for p in peers], 'planner_action': plan.planned_action.value,
        'planner_reasons': plan.reasons, 'status': 'blocked',
        'blockers': ([] if ec3 else ['ERC naturally aspirated evidence', 'ERC nonhybrid evidence']) + ['Unpublished MY2019 generation correspondence'],
        'existing_revision': str((OLD / (rid + '.candidate.json')).relative_to(ROOT))}
    assert plan.planned_action.value not in ('create', 'no_op_exact_match')
    rows.append(row)
    proofs.append({'row_id': rid, 'engine_proof_2_0': proof, 'error': proof_error,
        'scope': 'Read-only standalone candidate/peer sub-assessment, not a resolved plan or import authorization.'})
    candidates.append(c)

for code, s in common.items():
    doc = next(d for c in candidates for d in c.evidence_documents if d['assertion_set_id'] == s.provenance.native_record_id)
    payload = {'review_version': '1.0', 'revision_uuid': str(uuid.uuid4()), 'correspondence_uuid': str(uuid.uuid4()),
        'revision_number': 1, 'supersedes_uuid': None, 'vehicle_model_uuid': str(vm.uuid),
        'generation_uuid': str(generation.uuid), 'source_id': s.provenance.source_id,
        'source_namespace': 'source_model_code', 'identity_type': 'model_code', 'native_identifier': code,
        'market': 'US', 'start_year': 2019, 'end_year': 2019, 'restrictions': {}, 'evidence': [doc],
        'finding': 'established', 'reviewer': 'Codex implementation evidence review; unpublished proposal for human review',
        'reviewed_at': now, 'review_notes': 'MY2019 JL inventory explicitly accepted by director; retained exact manufacturer model code agrees with the verified MY2018 published code-to-JL correspondence ' + old_mapping[code]['uuid'] + ' (' + old_mapping[code]['hash'] + '). Same existing JL target and parents; fresh 2019-only chain, not reuse of the 2018 source revision. Group common document retains the identical inventory bytes. No finding based solely on Wrangler/JL name similarity. No publication or human authorization is claimed.'}
    validate_review_payload(payload)
    validate_documents(payload['evidence'], verify_bytes=True)
    for c in candidates:
        if any(i['native_identifier'] == code for i in c.generation_evidence):
            assert doc in c.evidence_documents
    write('correspondence_proposals/' + code + '.review.json', {'review': payload, 'content_hash': digest(payload)})

namespace = list(VehicleDefinition.objects.filter(generation=generation, model_year=2019).values(
    'id', 'uuid', 'trim_name', 'engine_name', 'drivetrain', 'market', 'slug', 'is_active'))
assert not namespace
assert len({(r['trim_name'], tuple(r['canonical_powertrain'].values())) for r in rows}) == 19
write('candidate_review.json', {'created_at': now, 'input_candidates_validated': 19, 'input_assertion_sets_validated': source_count,
    'valid_candidates': 19, 'eligible': 0, 'blocked': 19, 'conflicting': 0, 'rows': rows})
write('engine_proof_assessment.json', {'created_at': now, 'contract': 'engine proof 2.0',
    'complete_standalone_assessments': sum(p['engine_proof_2_0'] is not None for p in proofs),
    'resolved_plan_proofs': 0, 'rows': proofs})
write('matrix_readiness.json', {'created_at': now, 'requested_contract': 'Matrix 2.1', 'status': 'blocked',
    'matrix_generated': False, 'reason': 'All 19 rows lack published correspondence; 10 ERC rows also lack a complete five-field tuple. Matrix 2.1 requires complete target tuples and cannot express blocked rows. No unknown was replaced by a guessed value, and no unpublished proposal was represented as a live correspondence.',
    'resolution_contract': '1.1', 'resolved_plans': 0, 'eligible': 0, 'blocked': 19})
write('live_peer_assessment.json', {'created_at': now, 'access': 'SQLite URI mode=ro plus PRAGMA query_only=ON',
    'db_sha256': baseline, 'jl_generation': {'pk': generation.pk, 'uuid': str(generation.uuid), 'slug': generation.slug,
        'start_year': generation.start_year, 'end_year': generation.end_year, 'model_uuid': str(vm.uuid)},
    'my2019_namespace': namespace, 'jl_existing_year_counts': {str(y): VehicleDefinition.objects.filter(generation=generation, model_year=y).count() for y in VehicleDefinition.objects.filter(generation=generation).values_list('model_year', flat=True).distinct()},
    'vehicle_definitions': VehicleDefinition.objects.count(), 'receipts': ImportExecutionReceipt.objects.count(),
    'prior_verified_model_code_correspondences': old_mapping,
    'my2019_published_research_correspondences': GenerationCorrespondenceRevision.objects.filter(source_id='reviewed_jeep_order_guide_inventory', start_year__lte=2019, end_year__gte=2019).count()})
with (OUT / 'director_review_19_rows_BLOCKED.csv').open('w', newline='') as f:
    fields = ['row_id','body','trim_name','engine_code','source_model_code','candidate_valid','engine_tuple_complete','planner_action','status','blockers']
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: '; '.join(r[k]) if isinstance(r[k], list) else r[k] for k in fields})
assert hashlib.sha256((ROOT / 'db.sqlite3').read_bytes()).hexdigest() == baseline
assert all(hashlib.sha256((BASE / p).read_bytes()).hexdigest() == h for p, h in prior.items())
write('preservation.json', {'database_sha256_before_and_after': baseline, 'prior_review_files_preserved': len(prior),
    'no_database_writes': True, 'prior_review_file_sha256': prior})
print('19 original candidates and 32 assertion sets valid; 19 revised candidates valid.')
print('Fuel evidence bound for all 19; explicit 4WD added for six two-door rows.')
print('9 complete standalone engine proofs; 10 ERC tuples incomplete; all 19 blocked by correspondence publication.')
print('5 correspondence review proposals validated, none published. Database and prior review bytes unchanged.')
