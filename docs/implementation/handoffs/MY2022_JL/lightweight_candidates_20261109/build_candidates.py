"""MY2022 bounded artifact construction with existing contracts; read-only planning.

No acquisition, adjudication, correspondence publication, Matrix, or importer.
Run from repository root: .venv/bin/python -B <this file>
Existing artifacts are verified rather than overwritten on repeat runs.
"""
import copy
import csv
import hashlib
import json
import os
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

SCRIPT_START = time.perf_counter()
HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p/'manage.py').is_file())
BASE = HERE.parent/'discovery_20261109'
ED = HERE.parent/'edmunds_comparison_20261109'
sys.path.insert(0, str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['RIGARCHIVE_TEST_DB_PATH'] = ':memory:'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
READ_URI = 'file:' + str(ROOT/'db.sqlite3') + '?mode=ro'
SQLITE_CONNECT = sqlite3.connect
DB_PHASE = False
SQLITE_OPENS = 0

def guarded_connect(database, *args, **kwargs):
    global SQLITE_OPENS
    if not DB_PHASE or str(database) != READ_URI or not kwargs.get('uri'):
        raise RuntimeError('Only explicitly read-only operational SQLite inspection is permitted')
    db = SQLITE_CONNECT(database, *args, **kwargs)
    db.execute('PRAGMA query_only=ON')
    SQLITE_OPENS += 1
    return db
sqlite3.connect = guarded_connect
sqlite3.dbapi2.connect = guarded_connect

import django
django.setup()
from django.conf import settings
from django.core.exceptions import ValidationError
from reference.ingestion.contracts import (
    Envelope, SourceMetadata, SourceApplicability, ExtractionProvenance,
    SourceAssertion, SourceAssertionSet, NormalizedInterpretation, TechnicalValue,
    CandidateIdentity, AttributeReconciliationState,
)
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.serialization import serialize_artifact, deserialize_artifact, candidate_config_doc_to_dict
from reference.ingestion.validation import validate_candidate_configuration, validate_source_assertion_set
from reference.ingestion.importing.powertrain_identity import candidate_powertrain, identity_proof, _supports
from reference.ingestion.generation_correspondence import digest, validate_generation_evidence
from reference.powertrain import FIELDS


def load(p): return json.loads(p.read_text())
def sha(p): return 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p): return str(p.relative_to(ROOT))
def emit(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
    if p.exists():
        assert p.read_text() == text, 'Checkpoint differs: '+rel(p)
    else:
        with p.open('x') as f: f.write(text)

def artifact(p, value):
    text = serialize_artifact(value) + '\n'
    assert serialize_artifact(deserialize_artifact(text)) + '\n' == text
    if p.exists(): assert p.read_text() == text, rel(p)
    else:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('x') as f: f.write(text)


def preservation():
    for path, expected in load(HERE/'preservation_baseline.json')['files'].items():
        assert sha(ROOT/path) == expected, 'Preservation failure: '+path
    for path, expected in load(HERE/'preservation_baseline.json')['sqlite_files'].items():
        assert sha(ROOT/path) == expected, 'SQLite preservation failure: '+path
    assert {rel(p) for p in ROOT.glob('db.sqlite3*') if p.is_file()} == set(load(HERE/'preservation_baseline.json')['sqlite_files'])


# Capture before candidate construction; preserve prior evidence, app contracts and governance.
if not (HERE/'preservation_baseline.json').exists():
    files = {rel(p): sha(p) for directory in [BASE, ED, ROOT/'reference/ingestion']
             for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for p in [ROOT/'GEMINI.md', ROOT/'AGENTS.md']:
        if p.is_file(): files[rel(p)] = sha(p)
    files.update({rel(p): sha(p) for p in (ROOT/'docs/architecture/ADR').glob('*.md')})
    emit(HERE/'preservation_baseline.json', {'files': files,
         'sqlite_files': {rel(p):sha(p) for p in ROOT.glob('db.sqlite3*') if p.is_file()}})
preservation()
if not (HERE/'authorization.json').exists():
    emit(HERE/'authorization.json', {
        'created_at': datetime.now(timezone.utc).isoformat(),
        'authority': 'Explicit current-chat owner task: 55 provisional MY2022 consumer Candidate 2.1.0 artifacts and lightweight workflow experiment documentation',
        'classification_approvals': 'None; construction authorization does not approve derived five-field or new-grade findings',
        'generation_target_context': {'pk':32,'uuid':'38d3c3ac-f825-4406-abb5-c2d12b9129a4'},
        'boundaries': 'No acquisition, operational DB writes, adjudication approval, publication, Matrix certification, canonical import, commit or push',
        'interpreter_authority': 'Existing .venv explicitly authorized earlier in this chat when prescribed venv/py313/bin/python was absent',
    })
NOW = load(HERE/'authorization.json')['created_at']
rows = load(BASE/'provisional_configuration_inventory.json')
with (ED/'row_comparison.csv').open() as f: comparisons = list(csv.DictReader(f))
cm = {r['manufacturer_row']:r for r in comparisons}
assert len(rows) == len(cm) == 56
assert Counter(r['outcome'] for r in comparisons) == {'Exact match':45,'Equivalent configuration with different naming':11}
consumer = [r for r in rows if r['scope_status']=='provisional_consumer']
rhd = [r for r in rows if r['model_code']=='JLUL74']
assert len(consumer)==55 and len(rhd)==1 and all(r['model_code']!='JLUL74' for r in consumer)
assert Counter(cm[r['research_row_id']]['outcome'] for r in consumer)=={'Exact match':44,'Equivalent configuration with different naming':11}
source_index = {s['source_id']:s for s in load(BASE/'manufacturer_source_inventory.json')}
assessments = {a['engine_code']:a for a in load(BASE/'powertrain_evidence_matrix.json')}
cells = load(BASE/'positive_package_observations.json')
excerpts = {e['excerpt_id']:e for e in load(BASE/'evidence_index.json')}
packages = load(BASE/'factory_package_availability_excerpts.json')
pages = {sid:load(ROOT/s['extraction_path']) for sid,s in source_index.items()}
for s in source_index.values():
    assert sha(ROOT/s['retained_path'])==s['sha256']
    assert sha(ROOT/s['extraction_path'])==s['extraction_sha256']

SETS = {}

def source_set(sid, native, path, locator, assertions, *, revision=None, acquired=None, notes='', source_type='manufacturer_document'):
    if native in SETS:
        assert SETS[native].source_assertions==assertions
        return SETS[native]
    sas = SourceAssertionSet(
        Envelope('rigarchive.source_assertion_set.v1','1.1.0',NOW,'MY2022_lightweight_retained_evidence'),
        SourceMetadata(source_id=sid, source_type=source_type, source_locator=locator,
            retrieved_at=acquired or NOW, native_record_id=native,
            acquisition_method='retained_local_evidence; no new acquisition',
            source_use_notes=notes, review_status='pending_review',
            source_applicability=SourceApplicability(market='US',
                applicability_basis='Existing MY2022 US guide scope; joins bound to exact model, table, QOP and research row',
                publisher_jurisdiction='US' if source_type=='manufacturer_document' else None,
                applicability_scope='model_year'),
            extraction_provenance=ExtractionProvenance(sha(path),rel(path),
                'MY2022_retained_discovery_transcription','1.0.0','manually_verified_transcription',
                unknown_fields={'notes':'Reuses discovery extraction; not a new production extractor or original Edmunds page acquisition'}),
            unknown_fields={'publication_revision':revision}), assertions)
    validate_source_assertion_set(sas)
    artifact(HERE/'assertion_sets'/(native+'.source_assertion_set.1.1.0.json'),sas)
    SETS[native]=sas
    return sas

# Only already retained technical p1 is needed for explicit model-wide 4WD.
sp = source_index['2022_JP_Wrangler_SP']
assert 'four-wheel drive' in pages[sp['source_id']][0].lower()
tech = source_set(sp['source_id'],'MY2022-technical-layout-p1',ROOT/sp['retained_path'],sp['url'],
    [SourceAssertion('MY2022-layout-p1','manufacturer_technical_page',pages[sp['source_id']][0],
                     'PDF page 1; GENERAL INFORMATION and BODY/CHASSIS; 2022 Jeep Wrangler')],
    acquired=sp['acquired_at'],notes='Explicit model-wide four-wheel-drive layout. No engine classification inferred from overview availability.')


def trim_label(row):
    label = row['marketed_column_label']
    if label=='Altitude': label='Sport Altitude' if row['model_code']=='JLJL74' else 'Sahara Altitude'
    if row['model_code']=='JLXP74' and label=='High Altitude': label += ' 4xe'
    return ('Unlimited ' if row['body_style']=='4-door' else '')+label


def build_one(row):
    rid = row['research_row_id']; engine = row['engine_code']; label = trim_label(row)
    obs = [c for c in cells if all(c[k]==row[k] for k in ['model_code','marketed_column_label','engine_code'])]
    assert len(obs)==len(row['evidence'])
    sas_list=[]
    for sid in sorted({c['source_id'] for c in obs},key=lambda sid:source_index[sid]['revision_date']):
        s=source_index[sid]
        e=next(e for e in excerpts.values() if e['source_id']==sid and e['model_code']==row['model_code'])
        native=sid+'-'+row['model_code']
        all_obs=[c for c in cells if c['excerpt_id']==e['excerpt_id']]
        assertions=[SourceAssertion(native+'-table','factory_powertrain_table',e['text'],f'PDF page {e["pdf_page_1_based"]}; model {row["model_code"]}; named marketed columns and positive QOP cells'),
            SourceAssertion(native+'-heading','source_document_heading',pages[sid][0],'PDF page 1; United States / MY2022 / Wrangler / body heading'),
            SourceAssertion(native+'-model','source_model_code',row['model_code'],f'PDF page {e["pdf_page_1_based"]}; exact manufacturer model code')]
        for code in sorted({c['engine_code'] for c in all_obs}):
            segments=sorted({c['manufacturer_engine_segment'] for c in all_obs if c['engine_code']==code})
            for n,seg in enumerate(segments):
                assertions.append(SourceAssertion(native+f'-{code}-segment-{n}','engine_transmission_QOP_segment',seg,
                    f'PDF page {e["pdf_page_1_based"]}; full engine/transmission/QOP segment {n}; {code}'))
            descriptor=' '.join(line[:21].strip() for line in segments[0].splitlines())
            assertions.append(SourceAssertion(native+'-'+code+'-engine-column','engine_descriptor',descriptor,
                f'PDF page {e["pdf_page_1_based"]}; first 21 characters of each retained layout-segment line; full segments retained; no codes or QOP values interpreted as powertrain classes'))
        sas_list.append(source_set(sid,native,ROOT/s['retained_path'],s['url'],assertions,
            revision=s['revision_date'],acquired=s['acquired_at'],notes='Manufacturer-issued third-party archived guide. Raw heading, model and positive engine/QOP group retained; no cross-year availability inference.'))
    primary=sas_list[-1]
    ast={a.attribute_key:a for a in primary.source_assertions if a.attribute_key in ['factory_powertrain_table','source_document_heading']}
    engine_ast=next(a for a in primary.source_assertions if a.assertion_id.endswith(engine+'-engine-column'))
    values=copy.deepcopy(assessments[engine]['research_values'])
    interpretations=[]
    def interp(key,value,a,notes):
        interpretations.append(NormalizedInterpretation(rid+'-'+key,a.assertion_id,key,value,
            raw_source_value=a.raw_value,normalization_notes=notes))
    for key,value in values.items():
        if value is not None:
            assert _supports(engine_ast.raw_value,key,value,jeep=True),(rid,key,engine_ast.raw_value)
            interp(key,TechnicalValue(value,'L',engine_ast.raw_value) if key==FIELDS[0] else value,engine_ast,
                   'Existing discovery direct projection only; qualified engine column and exact positive trim/QOP membership. No inferred values or approvals.')
    for key,value in [('make','Jeep'),('model','Wrangler'),('model_year',2022),('market','US')]:
        interp(key,value,ast['source_document_heading'],'Independent retained US MY2022 document heading; caller target is not evidence.')
    interp('trim',label,ast['factory_powertrain_table'],
           'Provisional body-aware marketed-label normalization using exact manufacturer section, QOP column and existing Edmunds mapping; established Wrangler naming convention, no new-grade adjudication approval.')
    engine_labels={'ERC':'3.6L V6 ESS','ERG':'3.6L V6 eTorque','EC1':'2.0L I4 Turbo','EXJ':'3.0L V6 Turbo Diesel','ECX':'2.0L I4 Turbo PHEV','ESG':'6.4L V8 HEMI'}
    interp('engine_name',engine_labels[engine],engine_ast,'Display descriptor only; manufacturer engine codes and names do not substitute for five-field identity.')
    sas_list.append(tech)
    interp('generic_drive_classification','4WD',tech.source_assertions[0],
           'Explicit 2022 model-wide BODY/CHASSIS four-wheel-drive layout in retained manufacturer technical p1; no equipment/mode inference.')
    edrow=cm[rid]
    edset=source_set('rigarchive_MY2022_edmunds_reconciliation',rid+'-edmunds-transcription',
        ED/'row_comparison.csv',edrow['edmunds_url'],
        [SourceAssertion(rid+'-edmunds-correspondence','research_offering_correspondence',edrow,
            f'Existing reconciliation CSV row {rid}; Edmunds live selector style {edrow["edmunds_style_id"]}; methodology/date in companion README')],
        notes='RigArchive-authored research transcription, not retained original Edmunds HTML or direct manufacturer classification. Offering-level corroboration only; no powertrain values mapped from this secondary interpretation.',source_type='research_transcription')
    sas_list.append(edset)
    c=construct_candidate_configuration(CandidateIdentity('Jeep','Wrangler',model_year=2022,market='US',trim_name=label),
        sas_list,interpretations,candidate_reference=rid,created_at=NOW,schema_version='2.1.0')
    unresolved=[k for k,v in values.items() if v is None]
    c.reconciliation_and_review.requires_human_review=True
    c.reconciliation_and_review.review_workflow_disposition='pending_review'
    c.reconciliation_and_review.reconciliation_notes='Provisional lightweight construction. Missing five-field classifications and unpublished MY2022 source correspondence block canonical eligibility; no approval is implied.'
    for key in unresolved:
        c.reconciliation_and_review.attribute_states[key]=AttributeReconciliationState('incomplete','pending_review','Unresolved evidence-backed classification; remains null')
    c.unknown_fields['research_revision_lineage']={
        'research_row':row,'research_matrix':rel(BASE/'provisional_configuration_inventory.json'),
        'research_matrix_sha256':sha(BASE/'provisional_configuration_inventory.json'),
        'edmunds_mapping':edrow,'edmunds_matrix':rel(ED/'row_comparison.csv'),'edmunds_matrix_sha256':sha(ED/'row_comparison.csv'),
        'edmunds_notice':'Secondary research transcription; exact offering/name match is not complete canonical identity proof',
        'manufacturer_model_code':row['model_code'],'positive_QOP_observations':obs,
        'package_inventory':rel(BASE/'factory_package_availability_excerpts.json'),
        'package_inventory_sha256':sha(BASE/'factory_package_availability_excerpts.json'),
        'package_page_scope_notice':'Raw retention only; not normalized, authorized optional-equipment ingestion or evaluated compatibility',
        'package_source_locators':[{'source_id':sid,'source_sha256':source_index[sid]['sha256'],'extraction_path':source_index[sid]['extraction_path']} for sid in sorted({c['source_id'] for c in obs})],
        'target_generation_context':{'pk':32,'uuid':'38d3c3ac-f825-4406-abb5-c2d12b9129a4','authorization_status':'intended existing target only; not a published correspondence'},
        'trim_review':'High Tide grade / Jeep Beach equipment relationship remains pending owner acceptance' if row['marketed_column_label']=='High Tide' else 'Provisional established marketed naming; no new human finding asserted',
        'classification_approval':'None; all unsupported values retained as null',
    }
    validate_candidate_configuration(c)
    assert candidate_powertrain(c,verify_bytes=True)==values
    return c,sas_list

construction_start=time.perf_counter()
candidates=[];inventory=[];unresolved=[];proof_checks=[]
for row in consumer:
    c,sets=build_one(row)
    encoded=serialize_artifact(c)
    # Rebuild independently with the same scope/clock. No random IDs or timestamp drift.
    duplicate,_=build_one(row)
    assert serialize_artifact(duplicate)==encoded
    path=HERE/'candidates'/(c.candidate_reference+'.provisional-r1.candidate.2.1.0.json')
    artifact(path,c)
    values=candidate_powertrain(c,verify_bytes=True)
    validate_generation_evidence(c.generation_evidence,c.evidence_documents)
    try:
        proof=identity_proof(c,[])
    except ValidationError as exc:
        proof_checks.append({'candidate_reference':c.candidate_reference,'requested_contract':'Engine Proof 2.0','status':'not_supported','reason':exc.messages,'proof_created':False})
    else:
        # A proof for an empty caller list cannot establish live canonical peer absence.
        raise AssertionError('Complete candidate requires an explicitly read-only canonical peer assessment before retaining proof')
    entry={'candidate_reference':c.candidate_reference,'candidate_artifact':rel(path),
        'candidate_hash':digest(candidate_config_doc_to_dict(c)),'artifact_sha256':sha(path),
        'body_style':row['body_style'],'trim_name':c.candidate_identity.trim_name,
        'manufacturer_model_code':row['model_code'],'engine_code':row['engine_code'],
        'canonical_powertrain':values,'unresolved_fields':[k for k,v in values.items() if v is None],
        'edmunds_outcome':cm[row['research_row_id']]['outcome'],'edmunds_style_id':cm[row['research_row_id']]['edmunds_style_id'],
        'assertion_sets':[rel(HERE/'assertion_sets'/(s.provenance.native_record_id+'.source_assertion_set.1.1.0.json')) for s in sets],
        'generation_identity_count':len(c.generation_evidence),'complete_five_field_identity':all(v is not None for v in values.values())}
    inventory.append(entry);candidates.append(c)
    for field in entry['unresolved_fields']:
        unresolved.append({'candidate_reference':c.candidate_reference,'candidate_hash':entry['candidate_hash'],
            'engine_code':row['engine_code'],'field':field,'current_value':None,
            'possible_value_for_review':assessments[row['engine_code']]['possible_values_requiring_review'][field],
            'status':'unapproved; null preserved','assessment_reference':rel(BASE/'powertrain_evidence_matrix.json'),
            'source_evidence_refs':[d['source_id']+'|'+d['raw_artifact_hash']+'|'+d['assertion_set_id'] for d in c.evidence_documents],
            'reason':'Existing direct support is insufficient; Edmunds research wording does not automatically satisfy unchanged contract predicate. Human conclusion must be separately approved.'})
construction_seconds=time.perf_counter()-construction_start
assert len(candidates)==55 and len(unresolved)==112
emit(HERE/'candidate_inventory.json',{'candidate_contract':'2.1.0','revision':'provisional-r1','rows':inventory})
with (HERE/'candidate_inventory.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['candidate_reference','body_style','trim_name','manufacturer_model_code','engine_code','edmunds_outcome','complete_five_field_identity','unresolved_fields','candidate_artifact'],lineterminator='\n');w.writeheader()
    w.writerows({k:'|'.join(r[k]) if isinstance(r[k],list) else r[k] for k in w.fieldnames} for r in inventory)
emit(HERE/'unresolved_classification_register.json',unresolved)
emit(HERE/'engine_proof_assessment.json',proof_checks)
emit(HERE/'engine_proofs_index.json',[])
emit(HERE/'offering_correspondence_inventory.json',{'input_rows':56,'same_name':45,'equivalent_name':11,
    'consumer_same_name':44,'consumer_equivalent_name':11,'rows':[{**r,'scope':'deferred_RHD' if r['manufacturer_row']==rhd[0]['research_row_id'] else 'consumer_candidate'} for r in comparisons]})
emit(HERE/'deferred_RHD.json',{'research_row':rhd[0],'edmunds_mapping':cm[rhd[0]['research_row_id']],
    'candidate_created':False,'reason':'Explicitly deferred by owner scope; existence corroborated, no scope or steering identity decision'})
reviews=[]
for r in consumer:
    for q in filter(None,cm[r['research_row_id']]['manufacturer_QOPs_not_observed_on_Edmunds'].split('|')):
        reviews.append({'candidate_reference':r['research_row_id'],'quick_order_package':q,'engine_code':r['engine_code'],
            'transmission_code':'DFT','status':'manufacturer_supported; Edmunds_not_observed; preserved_review_item',
            'evidence':[c for c in cells if c['model_code']==r['model_code'] and c['marketed_column_label']==r['marketed_column_label'] and c['quick_order_package']==q]})
assert len(reviews)==8
emit(HERE/'transmission_QOP_review_items.json',reviews)

# Duplicate check respects unknowns. Code/label inequality cannot prove distinction.
possible_pairs=[];complete_duplicates=[]
for a,b in combinations(inventory,2):
    if a['trim_name']!=b['trim_name']:continue
    av,bv=a['canonical_powertrain'],b['canonical_powertrain']
    if any(av[k] is not None and bv[k] is not None and av[k]!=bv[k] for k in FIELDS):continue
    if a['complete_five_field_identity'] and b['complete_five_field_identity']:
        complete_duplicates.append([a['candidate_reference'],b['candidate_reference']])
    else:
        possible_pairs.append({'candidates':[a['candidate_reference'],b['candidate_reference']],
            'status':'unknown_overlap_not_proven_duplicate_or_distinct',
            'reason':'Same trim/body/market/drive and no established unequal five-field dimension; null is not an equality or difference proof'})
emit(HERE/'duplicate_identity_review.json',{'confirmed_complete_duplicates':complete_duplicates,
    'possible_overlap_pairs':possible_pairs,'source_row_duplicates':0,'candidate_reference_duplicates':0})

# Actual supported planner; operational DB is opened using SQLite mode=ro only.
DB_PHASE=True
settings.DATABASES['default']['NAME']=READ_URI
settings.DATABASES['default']['OPTIONS']={'uri':True}
from django.db import connection
from reference.models import Generation, VehicleDefinition, ImportExecutionReceipt, GenerationCorrespondenceRevision
from reference.ingestion.importing.planner import plan_candidate_import
plan_start=time.perf_counter()
target=Generation.objects.get(pk=32)
assert str(target.uuid)=='38d3c3ac-f825-4406-abb5-c2d12b9129a4'
canonical_count=VehicleDefinition.objects.count();receipt_count=ImportExecutionReceipt.objects.count();correspondence_count=GenerationCorrespondenceRevision.objects.count()
namespace_count=VehicleDefinition.objects.filter(generation_id=32,model_year=2022).count()
plans=[]
for c in candidates:
    plan=plan_candidate_import(c)
    plans.append({'candidate_reference':c.candidate_reference,'eligibility_status':plan.eligibility_status.value,
        'planned_action':plan.planned_action.value,'review_category':plan.review_category.value if plan.review_category else None,
        'reasons':plan.reasons,'resolved_generation_id':plan.resolved_generation_id,
        'intended_generation_id':32,'executable_manifest_created':False})
keys={(i['source_id'],i['source_namespace'],i['identity_type'],i['native_identifier']) for c in candidates for i in c.generation_evidence}
revisions=list(GenerationCorrespondenceRevision.objects.filter(vehicle_model=target.vehicle_model,market='US',start_year__lte=2022,end_year__gte=2022,successor__isnull=True))
covered={(r.source_id,r.source_namespace,r.identity_type,r.native_identifier) for r in revisions}
missing=sorted(keys-covered)
connection.close();DB_PHASE=False
planning_seconds=time.perf_counter()-plan_start
emit(HERE/'eligibility_assessment.json',plans)
emit(HERE/'generation_readiness.json',{'intended_target':{'pk':32,'uuid':str(target.uuid)},'target_exists':True,
    'source_model_keys':len(keys),'missing_applicable_reviewed_keys':len(missing),'missing_keys':[list(k) for k in missing],
    'existing_MY2022_target_namespace_rows':namespace_count,'canonical_counts':{'VehicleDefinitions':canonical_count,'audit_receipts':receipt_count,'correspondence_revisions':correspondence_count},
    'notice':'Read-only readiness assessment, not a correspondence proposal or publication; supplied target PK does not authorize source-to-generation resolution'})
assert all(p['eligibility_status']!='eligible' for p in plans)
preservation()
summary={'candidate_contract':'2.1.0','engine_proof_contract':'2.0','schema_valid_candidates':55,
    'complete_candidates':sum(r['complete_five_field_identity'] for r in inventory),'incomplete_candidates':sum(not r['complete_five_field_identity'] for r in inventory),
    'blocked_candidates':sum(p['eligibility_status']!='eligible' for p in plans),'eligible_candidates':sum(p['eligibility_status']=='eligible' for p in plans),
    'count_semantics':'Complete/incomplete partition 55; blocked overlaps completeness and is not an additional candidate set',
    'by_body':dict(Counter(r['body_style'] for r in inventory)),'by_engine':dict(Counter(r['engine_code'] for r in inventory)),
    'unresolved_field_instances':len(unresolved),'unresolved_by_field':dict(Counter(r['field'] for r in unresolved)),
    'consumer_Edmunds_outcomes':dict(Counter(r['edmunds_outcome'] for r in inventory)),
    'RHD_deferred':1,'transmission_review_items':8,'assertion_sets':len(SETS),
    'engine_proofs_created':0,'possible_identity_overlap_pairs':len(possible_pairs),
    'planner_status_counts':dict(Counter(p['eligibility_status'] for p in plans)),
    'planner_review_categories':dict(Counter(p['review_category'] for p in plans)),
    'missing_generation_source_keys':len(missing),'database_preserved':True,
    'canonical_writes':0,'correspondences_published':0,'matrices_certified':0,
    'source_acquisitions':0,'candidate_revisions_per_row':1,
    'checks':{'schema':'passed','serialization_roundtrip':'passed','deterministic_rebuild':'passed','qualified_source_and_raw_byte_lineage':'passed','Edmunds_correspondence':'passed','RHD_exclusion':'passed','null_preservation':'passed','generation_evidence_projection':'passed','Engine_Proof_2_0_incomplete_rejection':'passed','actual_read_only_planner':'passed','preservation':'passed'}}
emit(HERE/'eligibility_summary.json',summary)
# Timing is observational, separate from deterministic candidate payloads.
if not (HERE/'processing_measurements.json').exists():
    emit(HERE/'processing_measurements.json',{'measured_at':datetime.now(timezone.utc).isoformat(),
        'construction_and_duplicate_rebuild_and_contract_validation_seconds':round(construction_seconds,6),
        'read_only_planning_and_generation_readiness_seconds':round(planning_seconds,6),
        'script_elapsed_seconds':round(time.perf_counter()-SCRIPT_START,6),
        'sqlite_read_only_connections':SQLITE_OPENS,'new_source_acquisitions':0,
        'candidate_artifacts':55,'source_assertion_sets':len(SETS),
        'candidate_bytes':sum((ROOT/r['candidate_artifact']).stat().st_size for r in inventory),
        'assertion_set_bytes':sum(p.stat().st_size for p in (HERE/'assertion_sets').glob('*.json')),
        'python':sys.version.split()[0],'django':django.get_version(),
        'limitations':'Script measurements only, not complete chat wall time or model processing. No reliable token counters or comparable MY2019–MY2021 timing baseline available; no savings asserted.'})
print(json.dumps(summary,indent=2))
print(json.dumps(load(HERE/'processing_measurements.json'),indent=2))
