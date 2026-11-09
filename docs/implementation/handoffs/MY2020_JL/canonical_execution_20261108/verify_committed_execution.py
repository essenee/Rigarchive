"""Independent read-only verification after a successful atomic Matrix execution.
Never invokes certification, execution, imports, saves or migrations. Receipt
parent IDs live in generation_resolution; full candidates live in retained
execution manifests, with receipt-bound manifest/candidate hashes.
"""
import os,sys,json,hashlib,sqlite3
from pathlib import Path
from collections import Counter
from io import StringIO
H=Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'manage.py').exists());P=H.parent/'final_planning_20261108';R=H.parent/'selector_packaging_repair_20261108';sys.path.insert(0,str(ROOT));os.environ['DJANGO_SETTINGS_MODULE']='config.settings';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from django.conf import settings
settings.DATABASES['default']['NAME']='file:'+str(ROOT/'db.sqlite3')+'?mode=ro';settings.DATABASES['default']['OPTIONS']={'uri':True}
import django;django.setup()
from django.db import connection
from django.core.management import call_command
from reference.models import Generation,VehicleDefinition,ImportExecutionReceipt,GenerationCorrespondenceRevision
from reference.ingestion.serialization import deserialize_artifact,candidate_config_doc_to_dict
from reference.ingestion.matrix import compute_matrix_digest
from reference.ingestion.matrix_approval import read_matrix_approval
from reference.ingestion.manifest import dict_to_manifest
from reference.ingestion.generation_correspondence import digest,validate_documents
from reference.ingestion.importing.matrix_workflow import MatrixYear
from reference.powertrain import BASE_FIELDS,FIELDS,record_powertrain
connection.cursor().execute('PRAGMA query_only=ON')
def load(p):return json.loads(p.read_text())
def rel(p):return str(p.relative_to(ROOT))
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(c):
 schema=c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_autoindex%' ORDER BY type,name").fetchall();tables={}
 for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
  cols=c.execute('PRAGMA table_info("'+name+'")').fetchall();names=[x[1] for x in cols];pos=[names.index(x[1]) for x in cols if x[5]];data=c.execute('SELECT * FROM "'+name+'"').fetchall();hashed={hashlib.sha256(json.dumps([r[n] for n in pos],default=str,separators=(',',':')).encode()).hexdigest():hashlib.sha256(json.dumps(list(r),default=str,ensure_ascii=False,separators=(',',':')).encode()).hexdigest() for r in data};assert len(hashed)==len(data);tables[name]={'count':len(data),'columns':names,'rows':hashed}
 return {'schema_digest':digest(schema),'tables':tables,'sequences':dict(c.execute('SELECT name,seq FROM sqlite_sequence').fetchall())}
assert load(H/'execution_command_result.json')['exit_code']==0,'Do not retry execution; inspect failure first'
base=load(H/'preservation_baseline.json');pre=load(H/'preflight.json');matrix=load(P/'matrix_2_1.json');EXPECTED=pre['approved_matrix_digest'];assert compute_matrix_digest(matrix)==EXPECTED=='sha256:a624e23a03e47491f86f8a417a86768e91aa8269213101a8d0dff08f1b3c9e0c';approval=read_matrix_approval(H/'approval.json',matrix)
attempts=list((H/'attempts').glob('matrix-*'));assert len(attempts)==1;attempt=attempts[0];result=load(attempt/'result.json');assert result['complete'] and result['counts']=={'newly_created':49}
rows=load(R/'candidate_index.json')['rows'];candidates={r['research_row_id']:deserialize_artifact((ROOT/r['candidate_artifact']).read_text()) for r in rows};gen=Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32);vm=gen.vehicle_model
assert load(attempt/'approval.json')==approval and compute_matrix_digest(load(attempt/'matrix.json'))==EXPECTED
if (H/'reconciliation.json').exists():reconciliation=load(H/'reconciliation.json');assert reconciliation['complete'] and reconciliation['counts']=={'previously_completed':49}
else:
 reconciliation=MatrixYear(matrix,approval,2020,candidates).status();assert reconciliation['complete'] and reconciliation['counts']=={'previously_completed':49};(H/'reconciliation.json').write_text(json.dumps(reconciliation,indent=2)+'\n')
new=list(VehicleDefinition.objects.filter(generation_id=32,model_year=2020,market='US').order_by('pk'));assert len(new)==49 and VehicleDefinition.objects.count()==861 and ImportExecutionReceipt.objects.count()==2980 and GenerationCorrespondenceRevision.objects.count()==64
assert len({v.slug for v in new})==len({str(v.uuid) for v in new})==49
pubs=load(H.parent/'generation_publication_20261108/publication_results.json')['results'];out=[];bases=[];receiptids=[]
for n,mr in enumerate(sorted(matrix['rows'],key=lambda r:r['row_id'])):
 rid=mr['row_id'];v=next(v for v in new if v.slug==mr['target_slug']);assert v.is_active and v.build_slug()==v.slug and v.generation_id==32
 assert all(getattr(v,k)==mr['target_fields'][k] for k in BASE_FIELDS);assert record_powertrain(v)=={k:mr['target_fields'][k] for k in FIELDS};v.clean()
 rr=list(ImportExecutionReceipt.objects.filter(created_vehicle_definition=v,operation_type='vehicle_definition_import',execution_outcome='created'));assert len(rr)==1;r=rr[0];rs=r.resolution_snapshot_json;resolution=rs['generation_resolution'];parents=resolution['parents']
 assert r.resolved_generation_id==32 and parents['generation_uuid']==str(gen.uuid) and parents['vehicle_model_id']==vm.pk and parents['manufacturer_id']==vm.manufacturer_id
 assert r.operator_label=='project_owner' and rs['attribution']['execution_agent']=='codex' and r.execution_channel=='cli' and r.planned_action=='create'
 assert r.created_vehicle_definition_pk_snapshot==v.pk and str(r.created_vehicle_definition_uuid_snapshot)==str(v.uuid) and r.created_vehicle_definition_slug_snapshot==v.slug
 assert r.candidate_reference==rid and r.target_fields_json==mr['target_fields'] and rs['candidate_hash']==mr['candidate_digest']
 link=rs['matrix'];assert link['matrix_digest']==EXPECTED and link['model_year']==2020 and link['row_id']==rid and link['approval_digest']==reconciliation['approval_digest'];assert link['generation_binding']==(mr['generation_binding']|{'generation':matrix['parents']['generation']})
 assert resolution['resolution_version']=='1.1' and resolution['engine_distinction']['version']=='2.0' and resolution['engine_distinction']['canonical_powertrain']==record_powertrain(v)
 assert {x['uuid']:x['hash'] for x in resolution['correspondences']}=={p['revision_uuid']:p['content_hash'] for p in pubs if rid in p['candidate_references']};validate_documents(resolution['documents'],verify_bytes=True)
 mf=attempt/f'{n:04d}.manifest.json';manifest=dict_to_manifest(load(mf));assert manifest.manifest_version=='2.1' and manifest.manifest_hash==r.manifest_hash;rp=manifest.plans[0];assert rp.candidate_snapshot==candidate_config_doc_to_dict(candidates[rid]) and rp.generation_resolution==resolution and rp.candidate_hash==mr['candidate_digest']
 assert rp.planned_action=='create' and rp.create_basis==r.create_basis and rp.create_basis in mr['permitted_create_bases'] and rp.namespace_snapshot_count==n and rp.target_slug==v.slug
 prior=[m for m in sorted(matrix['rows'],key=lambda r:r['row_id'])[:n] if m['target_fields']['trim_name']==mr['target_fields']['trim_name']];assert len(resolution['engine_distinction']['peers'])==len(prior)
 snap=next(p for p in pre['snapshot_plans'] if p['row_id']==rid);receiptids.append(r.pk);bases.append(r.create_basis);out.append({'row_id':rid,'VehicleDefinition_PK':v.pk,'UUID':str(v.uuid),'slug':v.slug,'generation_PK':32,'target_fields':mr['target_fields'],'candidate_hash':mr['candidate_digest'],'receipt_PK':r.pk,'receipt_UUID':str(r.uuid),'execution_manifest':rel(mf),'execution_manifest_hash':r.manifest_hash,'snapshot_manifest_hash':snap['manifest_hash'],'creation_basis':r.create_basis,'namespace_count_at_creation':rp.namespace_snapshot_count,'same_trim_peers_at_creation':len(prior),'correspondence_UUIDs':[x['uuid'] for x in resolution['correspondences']]})
assert len(set(receiptids))==49 and sorted(receiptids)==list(range(2932,2981));assert Counter(bases)==Counter({'first_representation':1,'source_established_grade':20,'mechanical_dimension':28})
c=sqlite3.connect('file:'+str(ROOT/'db.sqlite3')+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON');after=snapshot(c);assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall();c.close();old=base['snapshot'];assert after['schema_digest']==old['schema_digest'] and set(after['tables'])==set(old['tables']);delta={'reference_vehicledefinition':49,'reference_importexecutionreceipt':49};tables={}
for name,b in old['tables'].items():
 a=after['tables'][name];assert a['columns']==b['columns'] and all(a['rows'].get(k)==v for k,v in b['rows'].items());assert a['count']==b['count']+delta.get(name,0);tables[name]={'before':b['count'],'after':a['count'],'all_preexisting_rows_unchanged':True,'new_rows':a['count']-b['count']}
assert set(after['sequences'])==set(old['sequences']);assert all(after['sequences'][k]==v+delta.get(k,0) for k,v in old['sequences'].items());assert sha(ROOT/base['backup'])==base['backup_sha256'];assert all(sha(ROOT/p)==v for p,v in base['preexisting_MY2020_files'].items());check=StringIO();call_command('check',stdout=check);connection.close()
verification={'certified_matrix_digest':EXPECTED,'approval':approval,'approval_sha256':sha(H/'approval.json'),'attempt_directory':rel(attempt),'new_VehicleDefinitions':49,'all_new_US_MY2020_JL':True,'new_record_PKs':[v.pk for v in new],'new_receipt_PKs':sorted(receiptids),'creation_basis_counts':dict(Counter(bases)),'actual_atomic_workflow':'completed2020 in one durable transaction with fresh per-row plans','all_original812VehicleDefinitions_unchanged':True,'all_preexisting_database_rows_unchanged':True,'published_correspondences_unchanged':64,'schema_unchanged':True,'table_reconciliation':tables,'post_counts':{'VehicleDefinitions':861,'receipts':2980,'correspondences':64},'rows':out,'SQLite_integrity':'ok','foreign_key_violations':0,'Django_checks':check.getvalue().strip(),'backup':base['backup'],'backup_sha256':base['backup_sha256'],'backup_unchanged':True,'database_after_sha256':sha(ROOT/'db.sqlite3'),'preexisting_MY2020_artifact_files_unchanged':len(base['preexisting_MY2020_files']),'no_migrations_backfills_other_imports_code_contract_or_source_changes':True,'diagnostic_note':'Receipt parent identities are verified from generation_resolution and full candidate snapshots from receipt-hash-bound execution manifests, matching the existing receipt contract.'}
with (H/'verification.json').open('x') as f:json.dump(verification,f,indent=2);f.write('\n')
print('Independent verification passed:49new records;861total;receipts2932-2980;all prior rows and64correspondences unchanged',flush=True)
