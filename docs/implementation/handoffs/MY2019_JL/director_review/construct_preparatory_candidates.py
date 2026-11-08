"""Build incomplete 2.1.0 review artifacts; never execute or publish anything.

Run with the existing Python 3.13 environment from the repository root.
The snapshot is reviewed research, not an original manufacturer PDF.
"""
import csv
import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings
from django.db import connections
from django.core.exceptions import ValidationError
from reference.ingestion.acquisition.snapshots import RawAcquisitionResult, RawSnapshotManager
from reference.ingestion.contracts import (Envelope, SourceMetadata, SourceApplicability,
    ExtractionProvenance, SourceAssertion, SourceAssertionSet, NormalizedInterpretation,
    TechnicalValue, CandidateIdentity)
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.validation import validate_candidate_configuration, validate_source_assertion_set
from reference.ingestion.serialization import serialize_artifact, deserialize_artifact
from reference.ingestion.importing.powertrain_identity import candidate_powertrain
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.generation_correspondence import resolve_generation
from reference.models import VehicleModel

ROOT = Path(settings.BASE_DIR)
BASE = ROOT / 'docs/implementation/handoffs/MY2019_JL'
OUT = BASE / 'director_review/preparatory_candidates'
if (OUT / 'validation_results.json').exists():
    raise SystemExit('Completed artifacts already exist; use a separately reviewed new output revision.')
OUT.mkdir(exist_ok=True)
# SQLite itself enforces read-only access for all live Django queries.
connections.close_all()
settings.DATABASES['default']['NAME'] = 'file:' + str(ROOT / 'db.sqlite3') + '?mode=ro'
settings.DATABASES['default']['OPTIONS'] = {'uri': True}
before = hashlib.sha256((ROOT / 'db.sqlite3').read_bytes()).hexdigest()
now = datetime.now(timezone.utc).isoformat()
original_rows = list(csv.DictReader((BASE / 'source_index/MY2019_JL_candidate_inventory_PROVISIONAL.csv').open()))
readiness = list(csv.DictReader((BASE / 'readiness/MY2019_19_row_RA044_readiness.csv').open()))
assert len(original_rows) == len(readiness) == 19
# Preserve research lexemes, citations, and explicitly limited director acceptance.
snapshot = {
    'representation': 'locally assembled reviewed-research snapshot; NOT original PDF content',
    'director_acceptance_date': '2026-11-07',
    'director_acceptance': 'The director confirms that the MY2019 Wrangler JL manufacturer order-guide research already completed by ChatGPT is an acceptable basis for the proposed 19-configuration historical inventory.',
    'acceptance_scope': 'Historical offering inventory; provisional five-field classifications are not promoted wholesale.',
    'handoff_text': (BASE / 'MY2019_JL_CODEX_HANDOFF.md').read_text(),
    'inventory_rows': original_rows,
    'citation_rows': readiness,
    'limitations': 'Retained text/JSON hash authenticates this research representation only. No PDF bytes, PDF hashes, printed-date verification or new manufacturer quotations are claimed.',
}
raw = (json.dumps(snapshot, indent=2, sort_keys=True) + '\n').encode()
sa = SourceApplicability(market='US', applicability_basis='director_accepted_MY2019_US_JL_research_inventory',
    applicability_scope='model_year')
status, meta = RawSnapshotManager().store_snapshot(RawAcquisitionResult(
    source_id='reviewed_jeep_order_guide_inventory',
    source_locator=str((BASE / 'MY2019_JL_CODEX_HANDOFF.md').relative_to(ROOT)),
    acquired_at=now, content_type='application/json', raw_bytes=raw,
    source_applicability=sa, acquisition_method='local_file', original_filename='director_accepted_research_snapshot.json'))
(OUT / 'snapshot_reference.json').write_text(json.dumps(asdict(meta), indent=2) + '\n')
vm = VehicleModel.objects.get(name='Wrangler', manufacturer__name='Jeep', is_active=True)
results = []
for row, cite in zip(original_rows, readiness):
    assert row['marketed_trim'] == cite['trim'] and row['manufacturer_model_code'] == cite['model_code']
    rid = cite['review_id']
    context = (f"Director-accepted research inventory row {rid}; "
               f"{cite['june_guide_url']}; reported page {cite['june_page_reported']}. "
               'Page references are inherited research, not a new PDF inspection.')
    # Only accepted offering facts and explicit engine label interpretations.
    values = {'make': 'Jeep', 'model': 'Wrangler', 'model_year': 2019, 'market': 'US',
        'trim': row['marketed_trim'], 'source_model_code': row['manufacturer_model_code'],
        'engine_offering': row['powertrain_label'],
        'engine_displacement_liters': row['engine_displacement_liters'],
        'engine_cylinders': int(row['engine_cylinders'])}
    assertions = [SourceAssertion(k, k, v, context) for k,v in values.items()]
    sas = SourceAssertionSet(Envelope('rigarchive.source_assertion_set.v1', '1.1.0', created_at=now),
        SourceMetadata(meta.source_id, source_type='reviewed_research_transcription',
            source_locator=meta.publisher_locator, retrieved_at=now, native_record_id=rid,
            acquisition_method='local_file', review_status='director_accepted_inventory_only',
            source_use_notes='Prior manufacturer research accepted by director. Not an original PDF; no assertion that all five classifications are certified.',
            source_applicability=sa, extraction_provenance=ExtractionProvenance(meta.content_hash,
                meta.storage_path, 'director_accepted_jl_inventory_projection', '1.0.0', 'manually_verified_transcription'),
            unknown_fields={'publication_revision': 'MY2019 dated-revision union accepted by director; individual printed dates not newly verified'}), assertions)
    validate_source_assertion_set(sas)
    interpretations = []
    for k in ('make','model','model_year','market','trim','engine_displacement_liters','engine_cylinders'):
        value = values[k]
        if k == 'engine_displacement_liters':
            value = TechnicalValue(value, 'L', str(value))
        interpretations.append(NormalizedInterpretation('i_'+k, k, k, value,
            raw_source_value=values[k], normalization_notes='Accepted inventory projection; no code-derived classifications.'))
    if cite['engine_code'] == 'EC3':
        for k, value in [('engine_aspiration','turbocharged'), ('electrification_type','mild_hybrid')]:
            interpretations.append(NormalizedInterpretation('i_'+k, 'engine_offering', k, value,
                raw_source_value=row['powertrain_label'],
                normalization_notes='Explicit turbo/eTorque terminology in accepted offering label; existing Jeep mapping.'))
    candidate = construct_candidate_configuration(CandidateIdentity('Jeep','Wrangler',model_year=2019,
        market='US',trim_name=row['marketed_trim']), [sas], interpretations,
        candidate_reference='MY2019-JL-'+rid+'-preparatory', created_at=now, schema_version='2.1.0')
    validate_candidate_configuration(candidate)
    candidate_powertrain(candidate, verify_bytes=True)
    encoded = serialize_artifact(candidate)
    assert serialize_artifact(deserialize_artifact(encoded)) == encoded
    (OUT / (rid+'.source_assertion_set.json')).write_text(serialize_artifact(sas)+'\n')
    (OUT / (rid+'.candidate.json')).write_text(encoded+'\n')
    plan = plan_candidate_import(candidate)
    try:
        candidate_powertrain(candidate, complete=True, verify_bytes=True)
        completeness_error = None
    except ValidationError as exc:
        completeness_error = exc.messages
    try:
        resolve_generation(vm,2019,'US',candidate.generation_evidence,candidate.evidence_documents,
            {'trim_name': row['marketed_trim']})
        generation_error = None
    except ValidationError as exc:
        generation_error = exc.messages
    results.append({'review_id':rid,'candidate_contract':'VALID_PREPARATORY_2.1.0',
        'source_assertion_set_contract':'VALID_1.1.0','retained_bytes_verified':True,
        'round_trip_verified':True,'canonical_powertrain':candidate.canonical_powertrain,
        'unknown_powertrain_fields':[k for k,v in candidate.canonical_powertrain.items() if v is None],
        'missing_core_evidence':['generic_drive_classification'],
        'planned_action':plan.planned_action.value,'eligibility':plan.eligibility_status.value,
        'planner_reasons':plan.reasons,'complete_powertrain_error':completeness_error,
        'explicit_generation_resolution_error':generation_error,
        'source_url':cite['june_guide_url'],'reported_page':cite['june_page_reported']})
assert all(r['complete_powertrain_error'] and r['explicit_generation_resolution_error'] for r in results)
assert all(r['planned_action'] != 'create' for r in results)
after = hashlib.sha256((ROOT / 'db.sqlite3').read_bytes()).hexdigest()
assert before == after
(OUT/'validation_results.json').write_text(json.dumps({'python': 'Homebrew Python 3.13.2',
    'django':django.get_version(),'database_access':'SQLite mode=ro',
    'database_sha256_before':before,'database_sha256_after':after,'snapshot_status':status,
    'snapshot_hash':meta.content_hash,'results':results},indent=2)+'\n')
print(f'{len(results)} preparatory Candidate 2.1.0 + SourceAssertionSet 1.1.0 pairs validated; bytes and round trips verified.')
print('No import-eligible candidates; live database bytes unchanged.')
print('First planner result:',results[0]['planner_reasons'])
print('Explicit generation result:',results[0]['explicit_generation_resolution_error'])
