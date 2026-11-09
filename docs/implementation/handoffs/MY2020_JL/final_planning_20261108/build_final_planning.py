"""Read-only MY2020 Matrix/manifest planning; no approval or execution API calls."""
import os,sys,json,hashlib,copy
from dataclasses import asdict
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
from io import StringIO
H=Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'manage.py').exists());B=H.parent;R=B/'selector_packaging_repair_20261108';P=B/'generation_publication_20261108';sys.path.insert(0,str(ROOT));os.environ['DJANGO_SETTINGS_MODULE']='config.settings';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from django.conf import settings
settings.DATABASES['default']['NAME']='file:'+str(ROOT/'db.sqlite3')+'?mode=ro';settings.DATABASES['default']['OPTIONS']={'uri':True}
import django;django.setup()
from django.db import connection
from django.core.management import call_command
from reference.models import Generation,GenerationCorrespondenceRevision as Revision,ImportExecutionReceipt,VehicleDefinition
from reference.ingestion.serialization import deserialize_artifact,serialize_artifact,candidate_config_doc_to_dict,adjudication_from_dict
from reference.ingestion.validation import validate_candidate_configuration
from reference.ingestion.classification_adjudication import validate_classification_adjudication
from reference.ingestion.generation_correspondence import digest,validate_documents,validate_generation_evidence,revalidate_resolution
from reference.ingestion.importing.powertrain_identity import candidate_powertrain,identity_proof
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.manifest import dict_to_manifest,manifest_to_dict,reconstruct_plan_from_manifest
from reference.ingestion.matrix import validate_matrix,canonical_matrix_payload,compute_matrix_digest
from reference.ingestion.importing.matrix_workflow import _references,_identity
from reference.powertrain import FIELDS
connection.cursor().execute('PRAGMA query_only=ON');NOW=datetime.now(timezone.utc).isoformat()
def rel(p):return str(p.relative_to(ROOT))
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2,ensure_ascii=False);f.write('\n')
def textsave(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
assert not (H/'preservation.json').exists(),'Preserve existing planning checkpoint; no overwrite'
files={rel(p):sha(p) for p in B.rglob('*') if p.is_file() and not p.is_relative_to(H)};before=sha(ROOT/'db.sqlite3')
assert all(sha(ROOT/p)==v for p,v in load(R/'artifact_hashes.json').items());assert all(sha(ROOT/p)==v for p,v in load(P/'artifact_hashes.json').items())
assert before==load(P/'postpublication_verification.json')['postpublication_database_sha256']
counts={'VehicleDefinitions':VehicleDefinition.objects.count(),'receipts':ImportExecutionReceipt.objects.count(),'correspondences':Revision.objects.count()};assert counts=={'VehicleDefinitions':812,'receipts':2931,'correspondences':64}
gen=Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32,uuid='38d3c3ac-f825-4406-abb5-c2d12b9129a4');vm=gen.vehicle_model;assert gen.is_active and vm.is_active and vm.manufacturer.is_active
rows=load(R/'candidate_index.json')['rows'];assert len(rows)==49 and len({r['research_row_id'] for r in rows})==49;assert Counter(r['model_code'] for r in rows)==Counter({'JLJL72':12,'JLJS72':3,'JLJL74':18,'JLJP74':12,'JLJS74':4})
namespace=list(VehicleDefinition.objects.filter(generation=gen,model_year=2020,market='US').order_by('pk'));assert not namespace,'Namespace changed; reassess rather than assume empty first representation'
pubs=load(P/'publication_results.json')['results'];assert len(pubs)==51;published={x['revision_uuid']:x['content_hash'] for x in pubs}
for x in pubs:
 r=Revision.objects.get(pk=x['revision_PK'],uuid=x['revision_uuid']);r.clean();assert r.generation_id==32 and r.content_hash==x['content_hash']==digest(r.review_payload());assert r.start_year==r.end_year==2020 and r.market=='US'
 a=ImportExecutionReceipt.objects.get(pk=x['receipt_PK'],correspondence_revision=r);assert a.execution_outcome=='created' and a.manifest_hash==r.content_hash and a.resolution_snapshot_json['review']==r.review_payload()
save(H/'preservation.json',{'database_sha256_before':before,'database_counts':counts,'preexisting_MY2020_files':files,'read_only_access':'SQLite URI mode=ro and query_only=ON; no publication/import/approval/migration workflow invoked','input_candidate_index_sha256':sha(R/'candidate_index.json'),'publication_results_sha256':sha(P/'publication_results.json')})
print('Preflight passed:49 current candidates;51 real publications;empty MY2020 JL canonical namespace',flush=True)
plans=[];proofs=[];peers=[];matrixrows=[];bases=[];seen_trim={};seen_identity=set();seen_slugs=set();used_correspondences=set();classification_count=0;candidate_map={}
for n,r in enumerate(sorted(rows,key=lambda r:r['research_row_id']),1):
 rid=r['research_row_id'];c=deserialize_artifact((ROOT/r['candidate_artifact']).read_text());candidate_map[c.candidate_reference]=c
 validate_candidate_configuration(c);candidate_powertrain(c,complete=True,verify_bytes=True);validate_documents(c.evidence_documents,verify_bytes=True);validate_generation_evidence(c.generation_evidence,c.evidence_documents)
 assert digest(candidate_config_doc_to_dict(c))==r['candidate_hash'] and sha(ROOT/r['candidate_artifact'])==r['artifact_sha256'];assert serialize_artifact(deserialize_artifact(serialize_artifact(c)))==serialize_artifact(c)
 ci=c.candidate_identity;assert (ci.manufacturer_name,ci.vehicle_model_name,ci.model_year,ci.market)==('Jeep','Wrangler',2020,'US');assert ci.trim_name==r['trim_name_proposal']
 human=[d for d in c.evidence_documents if d['source_id']=='human_classification_adjudication'];claims={}
 if r['engine_code']!='EC3':
  assert len(human)==1 and human[0]['raw_artifact_reference']==r['approved_adjudication'];adj=adjudication_from_dict(load(ROOT/r['approved_adjudication']));validate_classification_adjudication(adj,require_approved=True);assert adj.adjudication_hash==r['approved_adjudication_hash'] and sha(ROOT/r['approved_adjudication'])==r['approved_adjudication_file_sha256'];claims=adj.evidence_anchors['classifications'];classification_count+=len(claims)
  assert all(claim['confidence']=='moderate' for claim in claims.values())
 else:assert not human
 if rid in ['JL20-33','JL20-34','JL20-35']:assert ci.trim_name=='Unlimited High Altitude' and r['model_code']=='JLJP74'
 out=H/'manifests'/f'{rid}.manifest.2.1.json';out.parent.mkdir(exist_ok=True);log=StringIO();call_command('plan_canonical_import',candidate=r['candidate_artifact'],output=rel(out),stdout=log,skip_checks=True);textsave(H/'planning_logs'/f'{rid}.txt',log.getvalue())
 raw=load(out);manifest=dict_to_manifest(raw);assert raw['manifest_version']=='2.1' and len(manifest.plans)==1 and manifest_to_dict(manifest)==raw
 plan=reconstruct_plan_from_manifest(manifest.plans[0]);revalidate_resolution(plan);fresh=plan_candidate_import(c);assert asdict(fresh)==asdict(plan),'Fresh planning changed: '+rid
 if plan.eligibility_status.value!='eligible' or plan.planned_action.value!='create':
  save(H/'blocked_planning_result.json',{'row_id':rid,'manifest':rel(out),'plan':raw['plans'][0]});raise RuntimeError('Planning blocked; no scope/validation relaxation permitted: '+rid)
 assert plan.resolved_generation_id==32 and plan.resolved_vehicle_model_id==vm.pk and plan.resolved_manufacturer_id==vm.manufacturer_id and plan.existing_vehicle_definition_id is None
 resolution=plan.generation_resolution;assert resolution['resolution_version']=='1.1' and resolution['basis']=='reviewed_source_correspondence' and resolution['parents']['generation_uuid']==str(gen.uuid)
 actual={x['uuid']:x['hash'] for x in resolution['correspondences']};wanted={x['revision_uuid']:x['content_hash'] for x in pubs if rid in x['candidate_references']};assert actual==wanted and all(published[k]==v for k,v in actual.items());used_correspondences.update(actual)
 proof=resolution['engine_distinction'];assert proof['version']=='2.0' and proof['canonical_powertrain']==c.canonical_powertrain;assert proof==identity_proof(c,[]);assert proof['peers']==[]
 fields=plan.target_vehicle_definition_fields;slug=plan.target_slug;identity=(fields['trim_name'],fields['drivetrain'],fields['market'],tuple(fields[k] for k in FIELDS));assert identity not in seen_identity and slug not in seen_slugs;seen_identity.add(identity);seen_slugs.add(slug)
 assert not VehicleDefinition.objects.filter(generation=gen,slug=slug).exists(),'Active or inactive slug occupancy'
 assert plan.create_basis.value=='first_representation' and plan.namespace_snapshot_count==0
 prior=seen_trim.get(fields['trim_name'],[])
 anticipated='first_representation' if n==1 else 'mechanical_dimension' if prior else 'source_established_grade';permitted=sorted({'first_representation',anticipated})
 assert all(x['canonical_powertrain']!=c.canonical_powertrain for x in prior)
 evidence,correspondence=_references(plan)
 matrixrows.append({'row_id':rid,'model_year':2020,'target_fields':fields,'target_slug':slug,'action':'create','permitted_create_bases':permitted,'candidate_reference':c.candidate_reference,'candidate_digest':plan.candidate_hash,'evidence':evidence,'correspondence':correspondence,'existing_record':None,'generation_binding':{'mode':'explicit_correspondence','strategy':'reviewed_source_correspondence','resolution_version':'1.1'}})
 bases.append({'row_id':rid,'current_basis':plan.create_basis.value,'anticipated_basis_in_fixed_matrix_order':anticipated,'permitted_create_bases':permitted,'earlier_same_trim_candidates':[x['row_id'] for x in prior],'tuple_distinct_from_all_earlier_same_trim_candidates':True,'analysis_basis':'Existing structured planner branch plus complete approved pairwise-distinct tuples. Not executed or tested by importing real candidates.'});seen_trim.setdefault(fields['trim_name'],[]).append({'row_id':rid,'canonical_powertrain':c.canonical_powertrain})
 proofs.append({'row_id':rid,'candidate_digest':plan.candidate_hash,'proof':proof,'classification_basis':'approved_human_adjudication_plus_retained_sources' if human else 'retained_direct_source_evidence','human_provenance':human,'approved_classification_claims':claims,'current_canonical_peers':0,'planned_same_trim_combinations':[x['row_id'] for x in prior]})
 peers.append({'row_id':rid,'resolution_version':'1.1','target':resolution['parents'],'model_year':2020,'market':'US','active_and_inactive_canonical_namespace_count':0,'same_trim_drive_peers':proof['peers'],'published_correspondences':resolution['correspondences'],'planned_action':plan.planned_action.value,'eligibility':plan.eligibility_status.value})
 plans.append({'row_id':rid,'candidate_reference':c.candidate_reference,'candidate_artifact':r['candidate_artifact'],'candidate_digest':plan.candidate_hash,'candidate_file_hash':r['artifact_sha256'],'manifest':rel(out),'manifest_hash':manifest.manifest_hash,'manifest_file_hash':sha(out),'planned_action':plan.planned_action.value,'eligibility':plan.eligibility_status.value,'current_create_basis':plan.create_basis.value,'target_slug':slug,'target_fields':fields,'published_correspondences':resolution['correspondences'],'evidence_references':evidence,'approved_adjudication':r.get('approved_adjudication'),'approved_adjudication_hash':r.get('approved_adjudication_hash')})
 print('Planned',n,'/49',rid,'eligible create',flush=True)
assert classification_count==60 and len(used_correspondences)==51
matrix={'matrix_version':'2.1','parents':{'manufacturer':_identity(vm.manufacturer),'vehicle_model':_identity(vm),'generation':_identity(gen)},'market':'US','model_years':[2020],'rows':matrixrows};validate_matrix(matrix);matrix=canonical_matrix_payload(matrix);md=compute_matrix_digest(matrix);save(H/'matrix_2_1.json',matrix);assert compute_matrix_digest(load(H/'matrix_2_1.json'))==md
reviewlog=StringIO();call_command('review_generation_trim_matrix',matrix=rel(H/'matrix_2_1.json'),candidate=[r['candidate_artifact'] for r in rows],stdout=reviewlog,skip_checks=True);review=json.loads(reviewlog.getvalue());assert review['matrix_digest']==md;assert review['validation'][0]['counts']=={'pending_create':49};assert review['validation'][0]['approval_digest'] is None;save(H/'matrix_review.json',review)
save(H/'plan_index.json',{'created_at':NOW,'matrix_digest':md,'matrix_approval':'not_granted','manifest_version':'2.1','plans':plans})
save(H/'engine_proofs_2_0.json',{'assessed':49,'complete':49,'version':'2.0','current_canonical_peers':0,'human_classified_candidates':43,'approved_field_decisions_preserved':60,'limitations':'Human conclusions retain moderate confidence, original applicability and limitations. Empty canonical peer lists describe current DB snapshot only. No transaction-time sibling receipt proof is claimed before execution.','rows':proofs})
save(H/'canonical_peer_assessment.json',{'resolution_version':'1.1','all_namespace_rows_including_inactive':[],'preexisting':0,'conflicting':0,'eligible':49,'blocked':0,'published_correspondences_used':51,'rows':peers})
save(H/'transaction_basis_review.json',{'notice':'Standalone snapshot manifests all bind an empty namespace and first_representation. Do not execute49 standalone snapshots sequentially unchanged. Accepted Matrix execution must freshly plan/revalidate each row in row-ID order inside one model-year transaction. Anticipated bases below are code/tuple analysis, not executed results. No real-candidate rehearsal or import occurred.','anticipated_basis_counts':dict(Counter(x['anticipated_basis_in_fixed_matrix_order'] for x in bases)),'rows':bases})
save(H/'matrix_validation_status.json',{'matrix_version':'2.1','matrix_digest':md,'technical_contract_validation':'passed','accepted_Matrix_review':'49pending_create;zero blocked/conflict','engine_proofs_2_0':'49complete','resolution_1_1':'49actual published bindings','fresh_replanning_determinism':'49passed','manifest_serialization_reconstruction_and_revalidation':'49passed','human_matrix_certification':'not_granted','approval_artifact_created':False,'canonical_execution':'not_performed','required_owner_decision':'Approve/certify exact Matrix digest,49-row scope and per-row permitted creation bases, then separately authorize accepted Matrix execution. Freshly revalidate all state immediately before any future execution.'})
textsave(H/'plan_hashes.md','# MY2020 JL snapshot manifest hashes\n\nMatrix digest: `'+md+'`\n\nUncertified planning artifacts; not standalone sequential execution instructions.\n\n| Row | Manifest hash |\n|---|---|\n'+'\n'.join('| '+p['row_id']+' | `'+p['manifest_hash']+'` |' for p in plans)+'\n')
check=StringIO();call_command('check',stdout=check)
with connection.cursor() as cur:
 cur.execute('PRAGMA integrity_check');assert cur.fetchone()[0]=='ok';cur.execute('PRAGMA foreign_key_check');assert not cur.fetchall()
assert {'VehicleDefinitions':VehicleDefinition.objects.count(),'receipts':ImportExecutionReceipt.objects.count(),'correspondences':Revision.objects.count()}==counts;connection.close();assert sha(ROOT/'db.sqlite3')==before and all(sha(ROOT/p)==v for p,v in files.items())
save(H/'verification.json',{'matrix_digest':md,'eligible':49,'blocked':0,'conflicting':0,'preexisting':0,'expected_creations':49,'expected_no_ops':0,'unique_planned_identities_and_slugs':49,'current_and_approved_candidates_verified':49,'approved_field_decisions_preserved':60,'engine_proofs_verified':49,'manifest_roundtrips_and_fresh_plan_matches':49,'actual_published_correspondence_bindings':51,'Matrix_contract_review':'passed;uncertified','Django_checks':check.getvalue().strip(),'SQLite_integrity':'ok','foreign_key_violations':0,'database_counts':counts,'database_sha256_before_and_after':before,'database_byte_unchanged':True,'preexisting_MY2020_files_unchanged':len(files),'no_approval_import_migration_or_publication':True})
print('MATRIX VALID:',md,'49eligible;0blocked/conflicts/preexisting;49expectedcreates;0noops;UNCERTIFIED;DB byte-identical',flush=True)
