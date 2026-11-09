"""Exact owner-authorized Matrix certification and one atomic MY2020 execution.
Parent verification uses SQLite mode=ro/query_only. Only the accepted execution
CLI is allowed to write canonical data. Original snapshots are never executed.
"""
import os,sys,json,hashlib,sqlite3,subprocess,copy
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict
from collections import Counter
from io import StringIO
H=Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'manage.py').exists());B=H.parent;P=B/'final_planning_20261108';R=B/'selector_packaging_repair_20261108';PUB=B/'generation_publication_20261108';sys.path.insert(0,str(ROOT));os.environ['DJANGO_SETTINGS_MODULE']='config.settings';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from django.conf import settings
settings.DATABASES['default']['NAME']='file:'+str(ROOT/'db.sqlite3')+'?mode=ro';settings.DATABASES['default']['OPTIONS']={'uri':True}
import django;django.setup()
from django.db import connection
from django.core.management import call_command
from reference.models import Generation,GenerationCorrespondenceRevision as Revision,ImportExecutionReceipt,VehicleDefinition
from reference.ingestion.serialization import deserialize_artifact,candidate_config_doc_to_dict,adjudication_from_dict
from reference.ingestion.validation import validate_candidate_configuration
from reference.ingestion.classification_adjudication import validate_classification_adjudication
from reference.ingestion.matrix import validate_matrix,compute_matrix_digest
from reference.ingestion.matrix_approval import read_matrix_approval
from reference.ingestion.manifest import dict_to_manifest,manifest_to_dict,reconstruct_plan_from_manifest
from reference.ingestion.generation_correspondence import digest,validate_documents,revalidate_resolution
from reference.ingestion.importing.planner import plan_candidate_import
from reference.ingestion.importing.matrix_workflow import MatrixYear,_references
from reference.ingestion.importing.powertrain_identity import candidate_powertrain
from reference.powertrain import FIELDS,BASE_FIELDS,record_powertrain
connection.cursor().execute('PRAGMA query_only=ON');NOW=datetime.now(timezone.utc).isoformat();EXPECTED='sha256:a624e23a03e47491f86f8a417a86768e91aa8269213101a8d0dff08f1b3c9e0c'
def rel(p):return str(p.relative_to(ROOT))
def load(p):return json.loads(p.read_text())
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2,ensure_ascii=False);f.write('\n')
def ro(p):
 c=sqlite3.connect('file:'+str(p)+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON');return c
def snapshot(c):
 schema=c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_autoindex%' ORDER BY type,name").fetchall();tables={}
 for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
  columns=c.execute('PRAGMA table_info("'+name+'")').fetchall();names=[x[1] for x in columns];positions=[names.index(x[1]) for x in columns if x[5]];assert positions
  data=c.execute('SELECT * FROM "'+name+'"').fetchall();rows={hashlib.sha256(json.dumps([r[n] for n in positions],default=str,separators=(',',':')).encode()).hexdigest():hashlib.sha256(json.dumps(list(r),default=str,ensure_ascii=False,separators=(',',':')).encode()).hexdigest() for r in data};assert len(rows)==len(data);tables[name]={'count':len(data),'columns':names,'rows':rows}
 return {'schema_digest':digest(schema),'tables':tables,'sequences':dict(c.execute('SELECT name,seq FROM sqlite_sequence').fetchall())}
assert not (H/'preflight.json').exists(),'Existing execution checkpoint must not be rerun blindly'
files={rel(p):sha(p) for p in B.rglob('*') if p.is_file() and not p.is_relative_to(H)};db_before=sha(ROOT/'db.sqlite3')
for folder in [P,R,PUB]:assert all(sha(ROOT/p)==v for p,v in load(folder/'artifact_hashes.json').items()),'Reviewed artifact hash changed: '+str(folder)
matrix=load(P/'matrix_2_1.json');validate_matrix(matrix);assert compute_matrix_digest(matrix)==EXPECTED
rows=load(R/'candidate_index.json')['rows'];plans=load(P/'plan_index.json')['plans'];assert len(rows)==len(plans)==len(matrix['rows'])==49 and matrix['model_years']==[2020] and matrix['market']=='US'
assert set(r['research_row_id'] for r in rows)=={f'JL20-{n:02d}' for n in range(1,50)}
assert Counter(r['engine_code'] for r in rows)==Counter({'ERC':17,'ERG':3,'EC1':15,'EC3':6,'EXJ':8});assert Counter(r['body_style'] for r in rows)==Counter({'2-door':15,'4-door':34})
counts={'VehicleDefinitions':VehicleDefinition.objects.count(),'receipts':ImportExecutionReceipt.objects.count(),'correspondences':Revision.objects.count()};assert counts=={'VehicleDefinitions':812,'receipts':2931,'correspondences':64}
assert not VehicleDefinition.objects.filter(generation_id=32,model_year=2020,market='US').exists()
gen=Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32,uuid='38d3c3ac-f825-4406-abb5-c2d12b9129a4');vm=gen.vehicle_model;assert gen.is_active and vm.is_active and vm.manufacturer.is_active and vm.name=='Wrangler' and vm.manufacturer.name=='Jeep'
for name,obj in [('manufacturer',vm.manufacturer),('vehicle_model',vm),('generation',gen)]:assert matrix['parents'][name]=={'pk':obj.pk,'uuid':str(obj.uuid),'slug':obj.slug}
pubs=load(PUB/'publication_results.json')['results'];assert len(pubs)==51 and {p['revision_PK'] for p in pubs}==set(range(14,65))
for p in pubs:
 r=Revision.objects.get(pk=p['revision_PK'],uuid=p['revision_uuid']);r.clean();assert r.content_hash==p['content_hash']==digest(r.review_payload()) and r.generation_id==32 and r.start_year==r.end_year==2020 and r.market=='US'
 receipt=ImportExecutionReceipt.objects.get(pk=p['receipt_PK'],correspondence_revision=r);assert receipt.execution_outcome=='created' and receipt.manifest_hash==r.content_hash and receipt.resolution_snapshot_json['review']==r.review_payload()
candidates={};classification_count=0;preplans=[];seen_trim={};basis_analysis=[]
for r in sorted(rows,key=lambda r:r['research_row_id']):
 rid=r['research_row_id'];c=deserialize_artifact((ROOT/r['candidate_artifact']).read_text());validate_candidate_configuration(c);candidate_powertrain(c,complete=True,verify_bytes=True);validate_documents(c.evidence_documents,verify_bytes=True);assert sha(ROOT/r['candidate_artifact'])==r['artifact_sha256'] and digest(candidate_config_doc_to_dict(c))==r['candidate_hash'];assert (c.candidate_identity.manufacturer_name,c.candidate_identity.vehicle_model_name,c.candidate_identity.model_year,c.candidate_identity.market)==('Jeep','Wrangler',2020,'US');assert c.candidate_identity.trim_name==r['trim_name_proposal'];candidates[c.candidate_reference]=c
 if 'approved_adjudication' in r:
  a=adjudication_from_dict(load(ROOT/r['approved_adjudication']));validate_classification_adjudication(a,require_approved=True);assert a.adjudication_hash==r['approved_adjudication_hash'] and sha(ROOT/r['approved_adjudication'])==r['approved_adjudication_file_sha256'];classification_count+=len(a.evidence_anchors['classifications']);assert all(x['confidence']=='moderate' for x in a.evidence_anchors['classifications'].values())
 else:assert r['engine_code']=='EC3'
 if rid in ['JL20-33','JL20-34','JL20-35']:assert r['model_code']=='JLJP74' and c.candidate_identity.trim_name=='Unlimited High Altitude'
 pi=next(p for p in plans if p['row_id']==rid);mraw=load(ROOT/pi['manifest']);assert sha(ROOT/pi['manifest'])==pi['manifest_file_hash'];manifest=dict_to_manifest(mraw);assert manifest.manifest_hash==pi['manifest_hash'] and manifest.manifest_version=='2.1' and manifest_to_dict(manifest)==mraw
 planned=reconstruct_plan_from_manifest(manifest.plans[0]);revalidate_resolution(planned);fresh=plan_candidate_import(c);assert asdict(planned)==asdict(fresh)
 assert fresh.eligibility_status.value=='eligible' and fresh.planned_action.value=='create' and fresh.existing_vehicle_definition_id is None and fresh.resolved_generation_id==32 and fresh.create_basis.value=='first_representation' and fresh.namespace_snapshot_count==0
 assert fresh.candidate_hash==r['candidate_hash']==pi['candidate_digest'];assert fresh.generation_resolution['resolution_version']=='1.1' and fresh.generation_resolution['engine_distinction']['version']=='2.0'
 mr=next(x for x in matrix['rows'] if x['row_id']==rid);assert mr['candidate_reference']==c.candidate_reference and mr['candidate_digest']==fresh.candidate_hash and mr['target_fields']==fresh.target_vehicle_definition_fields and mr['target_slug']==fresh.target_slug and mr['action']=='create' and mr['existing_record'] is None
 ev,cor=_references(fresh);assert (mr['evidence'],mr['correspondence'])==(ev,cor);assert {x['uuid']:x['hash'] for x in fresh.generation_resolution['correspondences']}=={p['revision_uuid']:p['content_hash'] for p in pubs if rid in p['candidate_references']}
 prior=seen_trim.get(c.candidate_identity.trim_name,[]);anticipated='first_representation' if not preplans else 'mechanical_dimension' if prior else 'source_established_grade';assert mr['permitted_create_bases']==sorted({'first_representation',anticipated});assert all(x['powertrain']!=c.canonical_powertrain for x in prior)
 basis_analysis.append({'row_id':rid,'anticipated_basis':anticipated,'permitted_create_bases':mr['permitted_create_bases']});seen_trim.setdefault(c.candidate_identity.trim_name,[]).append({'row_id':rid,'powertrain':c.canonical_powertrain});preplans.append({'row_id':rid,'candidate_artifact':r['candidate_artifact'],'candidate_hash':r['candidate_hash'],'manifest_hash':pi['manifest_hash'],'target_fields':mr['target_fields'],'target_slug':mr['target_slug'],'correspondences':cor})
assert classification_count==60 and len(candidates)==49 and len({p['target_slug'] for p in preplans})==49
review=MatrixYear(matrix,None,2020,candidates,review_only=True).status();assert review['counts']=={'pending_create':49} and review['approval_digest'] is None
check=StringIO();call_command('check',stdout=check)
assert all(sha(ROOT/p)==v for p,v in files.items()) and sha(ROOT/'db.sqlite3')==db_before
# New, ignored, consistent backup; all audit row identifiers and values are hashed.
bdir=ROOT/'backups/review';bdir.mkdir(parents=True,exist_ok=True);bp=bdir/('MY2020_JL_canonical_preimport_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite3');assert not bp.exists();assert subprocess.run(['git','check-ignore','-q',rel(bp)],cwd=ROOT).returncode==0
src=ro(ROOT/'db.sqlite3');dst=sqlite3.connect(bp);src.backup(dst);dst.close();src.close();bc=ro(bp);assert bc.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not bc.execute('PRAGMA foreign_key_check').fetchall();baseline=snapshot(bc);bc.close();lc=ro(ROOT/'db.sqlite3');assert snapshot(lc)==baseline;lc.close();assert sha(ROOT/'db.sqlite3')==db_before
save(H/'preservation_baseline.json',{'preexisting_MY2020_files':files,'database_before_sha256':db_before,'backup':rel(bp),'backup_sha256':sha(bp),'snapshot':baseline,'privacy':'Primary-key tuples and values are hashed; no private row contents in audit metadata'})
save(H/'preflight.json',{'recorded_at':NOW,'result':'all verification gates passed before certification/import','approved_matrix_digest':EXPECTED,'review_manifest_sha256':sha(P/'artifact_hashes.json'),'plan_index_sha256':sha(P/'plan_index.json'),'counts_before':counts,'scope':{'candidates':49,'year':2020,'market':'US','generation_PK':32,'generation_UUID':str(gen.uuid),'body_counts':dict(Counter(r['body_style'] for r in rows)),'engine_counts':dict(Counter(r['engine_code'] for r in rows)),'model_code_counts':dict(Counter(r['model_code'] for r in rows)),'approved_field_decisions':60,'High_Altitude_identities':3},'snapshot_plans':preplans,'creation_bases_verified':basis_analysis,'live_review':review,'published_revision_PKs':list(range(14,65)),'Django_checks':check.getvalue().strip(),'backup':{'path':rel(bp),'sha256':sha(bp),'integrity':'ok','foreign_keys':'passed','all_table_schema_row_and_sequence_match':True},'owner_authorization':'Current explicit instruction authorizes exact Matrix certification and create-only atomic execution after these gates. Director project_owner; agent codex; affirmative CLI confirmations are supplied for this authorization only.'})
print('PRECHECK PASSED: exact Matrix49/49;60claims;51mappings;consistent backup',rel(bp),flush=True)
# Certification is local artifact-only; execution below is the only live write.
args=[]
for r in sorted(rows,key=lambda r:r['research_row_id']):args.extend(['--candidate',r['candidate_artifact']])
base=[str(ROOT/'.venv/bin/python'),'-B',str(ROOT/'manage.py')];env=os.environ.copy();env.pop('RIGARCHIVE_TEST_DB_PATH',None);approval_path=H/'approval.json'
cert=base+['approve_generation_trim_matrix','--matrix',rel(P/'matrix_2_1.json')]+args+['--operator','project_owner','--agent','codex','--output',rel(approval_path),'--skip-checks']
with (H/'certification_cli.txt').open('x') as log:cert_result=subprocess.run(cert,input='yes\n',text=True,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,env=env,timeout=1800)
save(H/'certification_result.json',{'command':cert,'exit_code':cert_result.returncode,'confirmation':'Explicit owner authorization for exact verified digest supplied as affirmative yes to unchanged CLI prompt'})
assert cert_result.returncode==0,'Certification failed; stop before execution'
approval=read_matrix_approval(approval_path,matrix);assert approval['matrix_digest']==EXPECTED and approval['operator']=='project_owner' and approval['decision']=='approved';assert sha(ROOT/'db.sqlite3')==db_before and all(sha(ROOT/p)==v for p,v in files.items())
assert MatrixYear(matrix,approval,2020,candidates).status()['counts']=={'pending_create':49}
print('CERTIFIED exact Matrix; starting accepted single atomic2020 execution with fresh per-row plans',flush=True)
attempt_root=H/'attempts';attempt_root.mkdir(exist_ok=True);command=base+['execute_generation_trim_matrix_year','--matrix',rel(P/'matrix_2_1.json'),'--approval',rel(approval_path),'--year','2020']+args+['--operator','project_owner','--agent','codex','--output-dir',rel(attempt_root),'--skip-checks']
with (H/'execution_cli.txt').open('x') as log:execution=subprocess.run(command,input='yes\n',text=True,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,env=env,timeout=3600)
save(H/'execution_command_result.json',{'command':command,'exit_code':execution.returncode,'matrix_digest':EXPECTED,'approval_sha256':sha(approval_path),'standalone_snapshot_execution':False,'workflow':'One accepted atomic Matrix2020 execution; fresh plan and manifest per row','confirmation':'Explicit owner authorization supplied as affirmative yes to unchanged CLI prompt'})
assert execution.returncode==0,'Execution command failed or reporting incomplete; inspect attempts/logs before any retry'
attempts=[p for p in attempt_root.iterdir() if p.is_dir()];assert len(attempts)==1;attempt=attempts[0];report=load(attempt/'result.json');assert report['complete'] and report['counts']=={'newly_created':49} and report['authorized_count']==49 and report['matrix_digest']==EXPECTED
assert compute_matrix_digest(load(attempt/'matrix.json'))==EXPECTED and load(attempt/'approval.json')==approval
print('EXECUTION COMMITTED49 newly_created; beginning independent post-execution verification',flush=True)
# Parent connection remains read-only; reconcile through the accepted workflow.
reconciliation=MatrixYear(matrix,approval,2020,candidates).status();assert reconciliation['complete'] and reconciliation['counts']=={'previously_completed':49};save(H/'reconciliation.json',reconciliation)
newrecords=list(VehicleDefinition.objects.filter(generation_id=32,model_year=2020,market='US').order_by('pk'));assert len(newrecords)==49 and VehicleDefinition.objects.count()==861 and ImportExecutionReceipt.objects.count()==2980 and Revision.objects.count()==64
assert len({r.slug for r in newrecords})==len({str(r.uuid) for r in newrecords})==49
verification_rows=[];used_receipts=[];actual_bases=[]
for index,mr in enumerate(sorted(matrix['rows'],key=lambda r:r['row_id'])):
 rid=mr['row_id'];record=next(r for r in newrecords if r.slug==mr['target_slug']);assert record.generation_id==32 and record.model_year==2020 and record.market=='US' and record.is_active;assert record.build_slug()==record.slug
 for k in BASE_FIELDS:assert getattr(record,k)==mr['target_fields'][k]
 assert record_powertrain(record)=={k:mr['target_fields'][k] for k in FIELDS}
 record.clean();assert gen.vehicle_model_id==vm.pk and vm.manufacturer_id==matrix['parents']['manufacturer']['pk']
 receipts=list(ImportExecutionReceipt.objects.filter(created_vehicle_definition=record,execution_outcome='created',operation_type='vehicle_definition_import'));assert len(receipts)==1;receipt=receipts[0];assert receipt.operator_label=='project_owner' and receipt.target_fields_json==mr['target_fields'] and receipt.candidate_reference==mr['candidate_reference'];assert receipt.created_vehicle_definition_pk_snapshot==record.pk and str(receipt.created_vehicle_definition_uuid_snapshot)==str(record.uuid) and receipt.created_vehicle_definition_slug_snapshot==record.slug
 assert receipt.resolved_generation_id==32 and receipt.resolution_snapshot_json['generation_resolution']['parents']['vehicle_model_id']==vm.pk and receipt.resolution_snapshot_json['generation_resolution']['parents']['manufacturer_id']==vm.manufacturer_id
 resolution=receipt.resolution_snapshot_json['generation_resolution'];link=receipt.resolution_snapshot_json['matrix'];assert link['matrix_digest']==EXPECTED and link['row_id']==rid and link['model_year']==2020 and link['approval_digest']==reconciliation['approval_digest'] and link['generation_binding']==reconciliation['rows'][index]['generation_binding'];assert resolution['resolution_version']=='1.1' and resolution['parents']['generation_id']==32 and resolution['engine_distinction']['version']=='2.0'
 assert resolution['engine_distinction']['canonical_powertrain']==record_powertrain(record)
 assert {x['uuid']:x['hash'] for x in resolution['correspondences']}=={p['revision_uuid']:p['content_hash'] for p in pubs if rid in p['candidate_references']}
 validate_documents(resolution['documents'],verify_bytes=True);assert receipt.resolution_snapshot_json['candidate_hash']==mr['candidate_digest']
 mf=attempt/f'{index:04d}.manifest.json';mdoc=dict_to_manifest(load(mf));assert mdoc.manifest_hash==receipt.manifest_hash;rp=mdoc.plans[0];assert rp.candidate_snapshot==candidate_config_doc_to_dict(candidates[mr['candidate_reference']]) and rp.generation_resolution==resolution;assert rp.create_basis in mr['permitted_create_bases'] and rp.planned_action=='create' and rp.candidate_hash==mr['candidate_digest'] and rp.target_slug==record.slug;assert rp.namespace_snapshot_count==index;assert len(rp.generation_resolution['engine_distinction']['peers'])==len([p for p in preplans[:index] if p['target_fields']['trim_name']==mr['target_fields']['trim_name']])
 snap=next(p for p in preplans if p['row_id']==rid);actual_bases.append(rp.create_basis);used_receipts.append(receipt.pk)
 verification_rows.append({'row_id':rid,'VehicleDefinition_PK':record.pk,'UUID':str(record.uuid),'slug':record.slug,'generation_PK':32,'target_fields':mr['target_fields'],'candidate_hash':mr['candidate_digest'],'receipt_PK':receipt.pk,'receipt_UUID':str(receipt.uuid),'execution_manifest':rel(mf),'execution_manifest_hash':receipt.manifest_hash,'snapshot_manifest_hash':snap['manifest_hash'],'creation_basis':rp.create_basis,'namespace_count_at_creation':rp.namespace_snapshot_count,'same_trim_peers_at_creation':len(rp.generation_resolution['engine_distinction']['peers']),'correspondence_UUIDs':[x['uuid'] for x in resolution['correspondences']]})
assert len(set(used_receipts))==49 and Counter(actual_bases)==Counter({'first_representation':1,'source_established_grade':20,'mechanical_dimension':28})
# Compare all existing rows to consistent backup; only49 definitions/receipts added.
live=ro(ROOT/'db.sqlite3');after=snapshot(live);assert live.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not live.execute('PRAGMA foreign_key_check').fetchall();live.close();assert after['schema_digest']==baseline['schema_digest'] and set(after['tables'])==set(baseline['tables']);allow={'reference_vehicledefinition':49,'reference_importexecutionreceipt':49};tables={}
for name,before in baseline['tables'].items():
 now=after['tables'][name];assert now['columns']==before['columns'] and all(now['rows'].get(k)==v for k,v in before['rows'].items()),'Preexisting row changed: '+name;assert now['count']==before['count']+allow.get(name,0);tables[name]={'before':before['count'],'after':now['count'],'all_preexisting_rows_unchanged':True,'new_rows':now['count']-before['count']}
for name,value in baseline['sequences'].items():assert after['sequences'][name]==value+allow.get(name,0)
assert set(after['sequences'])==set(baseline['sequences']);assert sha(bp)==load(H/'preservation_baseline.json')['backup_sha256'] and all(sha(ROOT/p)==v for p,v in files.items());check=StringIO();call_command('check',stdout=check);connection.close()
save(H/'verification.json',{'certified_matrix_digest':EXPECTED,'approval':approval,'approval_sha256':sha(approval_path),'attempt_directory':rel(attempt),'new_VehicleDefinitions':49,'all_new_US_MY2020_JL':True,'new_record_PKs':[r.pk for r in newrecords],'new_receipt_PKs':sorted(used_receipts),'creation_basis_counts':dict(Counter(actual_bases)),'actual_atomic_workflow':'completed2020 in one durable transaction with fresh per-row plans','all_original812VehicleDefinitions_unchanged':True,'all_preexisting_database_rows_unchanged':True,'published_correspondences_unchanged':64,'schema_unchanged':True,'table_reconciliation':tables,'post_counts':{'VehicleDefinitions':861,'receipts':2980,'correspondences':64},'rows':verification_rows,'SQLite_integrity':'ok','foreign_key_violations':0,'Django_checks':check.getvalue().strip(),'backup':rel(bp),'backup_sha256':sha(bp),'backup_unchanged':True,'database_after_sha256':sha(ROOT/'db.sqlite3'),'preexisting_MY2020_artifact_files_unchanged':len(files),'no_migrations_backfills_other_imports_code_contract_or_source_changes':True})
print('VERIFIED861 total VehicleDefinitions;2980receipts;64unchanged correspondences;all existing rows unchanged',flush=True)
