"""Independent offline artifact checks and explicitly read-only eligibility check."""
import copy
import csv
import hashlib
import json
import os
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

START=time.perf_counter()
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'manage.py').is_file())
BASE=HERE.parent/'discovery_20261109'; ED=HERE.parent/'edmunds_comparison_20261109'
sys.path.insert(0,str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE']='config.settings';os.environ['RIGARCHIVE_TEST_DB_PATH']=':memory:'
URI='file:'+str(ROOT/'db.sqlite3')+'?mode=ro'
CONNECT=sqlite3.connect;OPENS=0;DB_PHASE=False

def guard(database,*args,**kwargs):
    global OPENS
    if not DB_PHASE or str(database)!=URI or not kwargs.get('uri'):
        raise RuntimeError('Rejected non-read-only or out-of-phase SQLite connection')
    c=CONNECT(database,*args,**kwargs);c.execute('PRAGMA query_only=ON');OPENS+=1
    return c
sqlite3.connect=guard;sqlite3.dbapi2.connect=guard
import django
django.setup()
from django.conf import settings
from django.core.exceptions import ValidationError
from reference.ingestion.serialization import deserialize_artifact,serialize_artifact,candidate_config_doc_to_dict
from reference.ingestion.validation import validate_candidate_configuration,validate_source_assertion_set
from reference.ingestion.generation_correspondence import digest,validate_generation_evidence
from reference.ingestion.importing.powertrain_identity import candidate_powertrain,identity_proof

def load(p):return json.loads(p.read_text())
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def preserved():
    baseline=load(HERE/'preservation_baseline.json')
    for name,h in baseline['files'].items():assert sha(ROOT/name)==h,name
    for name,h in baseline['sqlite_files'].items():assert sha(ROOT/name)==h,name
    assert {str(p.relative_to(ROOT)) for p in ROOT.glob('db.sqlite3*') if p.is_file()}==set(baseline['sqlite_files'])

preserved()
rows=load(BASE/'provisional_configuration_inventory.json');byid={r['research_row_id']:r for r in rows}
with (ED/'row_comparison.csv').open() as f:comparisons={r['manufacturer_row']:r for r in csv.DictReader(f)}
family={r['engine_code']:r for r in load(BASE/'powertrain_evidence_matrix.json')}
index=load(HERE/'candidate_inventory.json')['rows']
assert len(index)==len({r['candidate_reference'] for r in index})==55
assert {r['candidate_reference'] for r in index}=={r['research_row_id'] for r in rows if r['scope_status']=='provisional_consumer'}
assert Counter(r['edmunds_outcome'] for r in index)=={'Exact match':44,'Equivalent configuration with different naming':11}
assert Counter(r['body_style'] for r in index)=={'2-door':15,'4-door':40}
candidates=[]
for r in index:
    path=ROOT/r['candidate_artifact'];assert sha(path)==r['artifact_sha256']
    c=deserialize_artifact(path.read_text());validate_candidate_configuration(c)
    assert serialize_artifact(c)+'\n'==path.read_text()
    assert digest(candidate_config_doc_to_dict(c))==r['candidate_hash']
    assert c.candidate_reference==r['candidate_reference']==byid[r['candidate_reference']]['research_row_id']
    assert c.candidate_identity.model_year==2022 and c.candidate_identity.market=='US'
    assert r['manufacturer_model_code']!='JLUL74'
    assert c.canonical_powertrain==family[r['engine_code']]['research_values']
    assert candidate_powertrain(c,verify_bytes=True)==c.canonical_powertrain
    validate_generation_evidence(c.generation_evidence,c.evidence_documents)
    lineage=c.unknown_fields['research_revision_lineage']
    assert lineage['research_row']==byid[c.candidate_reference]
    assert lineage['edmunds_mapping']==comparisons[c.candidate_reference]
    assert lineage['research_matrix_sha256']==sha(BASE/'provisional_configuration_inventory.json')
    assert lineage['edmunds_matrix_sha256']==sha(ED/'row_comparison.csv')
    assert c.reconciliation_and_review.requires_human_review
    assert c.normalized_technical_details.drivetrain_details.generic_classification=='4WD'
    assert any('four-wheel drive' in str(a['raw_value']).lower() for d in c.evidence_documents if d['source_id']=='2022_JP_Wrangler_SP' for a in d['assertions'])
    try:identity_proof(c,[])
    except ValidationError:pass
    else:raise AssertionError('An incomplete candidate obtained an Engine Proof')
    candidates.append(c)
for path in (HERE/'assertion_sets').glob('*.json'):
    sas=deserialize_artifact(path.read_text());validate_source_assertion_set(sas)
    assert serialize_artifact(sas)+'\n'==path.read_text()
    ep=sas.provenance.extraction_provenance;assert sha(ROOT/ep.raw_artifact_reference)==ep.raw_artifact_hash
assert len(list((HERE/'assertion_sets').glob('*.json')))==128
unresolved=load(HERE/'unresolved_classification_register.json')
expected={(c.candidate_reference,k) for c in candidates for k,v in c.canonical_powertrain.items() if v is None}
assert len(unresolved)==len(expected)==112
assert {(r['candidate_reference'],r['field']) for r in unresolved}==expected
assert len(load(HERE/'transmission_QOP_review_items.json'))==8
for r in load(HERE/'transmission_QOP_review_items.json'):
    assert r['quick_order_package'] in comparisons[r['candidate_reference']]['manufacturer_QOPs_not_observed_on_Edmunds'].split('|')
    assert r['evidence'] and all(c['quick_order_package']==r['quick_order_package'] and c['transmission_code']=='DFT' for c in r['evidence'])
assert load(HERE/'engine_proofs_index.json')==[]
assert len(load(HERE/'engine_proof_assessment.json'))==55
assert load(HERE/'deferred_RHD.json')['candidate_created'] is False
assert len(load(HERE/'duplicate_identity_review.json')['possible_overlap_pairs'])==13
assert load(HERE/'duplicate_identity_review.json')['confirmed_complete_duplicates']==[]
# Negative contract controls: filling a null without support or altering evidence
# must fail, even though the ordinary provisional candidate is schema-valid.
for c in [candidates[0],next(c for c in candidates if 'PHEV' in str(c.unknown_fields['research_revision_lineage']['research_row']['engine_code']) or c.unknown_fields['research_revision_lineage']['research_row']['engine_code']=='ECX')]:
    changed=copy.deepcopy(c);changed.canonical_powertrain['fuel_type']='gasoline'
    try:validate_candidate_configuration(changed)
    except (ValidationError,ValueError):pass
    else:raise AssertionError('Unsupported null fill accepted')
changed=copy.deepcopy(candidates[0]);changed.generation_evidence[0]['native_identifier']='UNSUPPORTED-CODE'
try:validate_candidate_configuration(changed)
except (ValidationError,ValueError):pass
else:raise AssertionError('Changed source-to-generation projection accepted')
assert OPENS==0
try:sqlite3.connect(str(ROOT/'db.sqlite3'))
except RuntimeError:pass
else:raise AssertionError('Writable operational connection accepted')
DB_PHASE=True
settings.DATABASES['default']['NAME']=URI;settings.DATABASES['default']['OPTIONS']={'uri':True}
from django.db import connection
from reference.ingestion.importing.planner import plan_candidate_import
assessments=load(HERE/'eligibility_assessment.json')
for c,expected in zip(candidates,assessments):
    p=plan_candidate_import(c)
    assert p.eligibility_status.value==expected['eligibility_status']=='requires_review'
    assert p.review_category.value==expected['review_category']=='generation_correspondence'
    assert p.reasons==expected['reasons']
with connection.cursor() as cursor:
    cursor.execute('PRAGMA query_only');assert cursor.fetchone()[0]==1
    cursor.execute('SELECT count(*) FROM reference_vehicledefinition');assert cursor.fetchone()[0]==934
    cursor.execute('SELECT count(*) FROM reference_vehicledefinition WHERE generation_id=32 AND model_year=2022');assert cursor.fetchone()[0]==0
connection.close();DB_PHASE=False
assert OPENS==1
preserved()
report={'status':'passed','schema_valid_candidates':55,'roundtrips':55,'manufacturer_Edmunds_lineage_checks':55,
 'source_assertion_sets_validated':128,'null_field_instances_preserved':112,'unsupported_null_fill_controls_rejected':2,
 'changed_generation_projection_control_rejected':1,'incomplete_engine_proof_rejections':55,
 'construction_phase_SQLite_connections':0,'guarded_read_only_SQLite_connections':OPENS,
 'writable_SQLite_connection_control_rejected':True,'query_only_pragma':True,'actual_planner_review_required':55,
 'database_hash_preserved':True,'source_and_contract_hashes_preserved':True,
 'elapsed_seconds':round(time.perf_counter()-START,6),'full_Django_suite_run':False}
(HERE/'validation_results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
