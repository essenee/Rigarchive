"""Verify the milestone; sanitize a copy only, using the MY2020 Git policy."""
from pathlib import Path
import collections, csv, hashlib, importlib.metadata, json, os, sqlite3, subprocess, sys, tempfile
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(ROOT))
HERE=Path(__file__).resolve().parent
BASE=HERE.parent
from docs.implementation.handoffs.MY2021_JL.canonical_execution_20261109.resumed_20261109 import execute_reconciled as execution
from docs.implementation.handoffs.MY2021_JL.generation_publication_20261109 import publish_atomic as helpers
from reference.ingestion.importing.matrix_workflow import MatrixYear
from reference.ingestion.generation_correspondence import digest, validate_documents
from reference.models import GenerationCorrespondenceRevision, ImportExecutionReceipt, VehicleDefinition
from reference.powertrain import FIELDS, record_powertrain

def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(name,value):
 p=HERE/name
 with p.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def quote(s):return '"'+s.replace('"','""')+'"'

assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()=='main'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip().startswith('8d4a6e8')
assert sys.version_info[:3]==(3,13,1)
assert all(importlib.metadata.version(n)==v for n,v in [x.split('==') for x in (ROOT/'requirements.txt').read_text().splitlines() if x])
live_hash=sha(ROOT/'db.sqlite3')
session_assessment=load(HERE/'checkpoint_session_assessment_baseline_check.json')
assert live_hash==session_assessment['current_file_sha256'],'Database changed after session assessment; stop'
original_baseline=load(BASE/'canonical_execution_20261109/resumed_20261109/preservation_baseline.json')
reader=helpers.ro(ROOT/'db.sqlite3');current_snapshot=helpers.snapshot(reader);reader.close()
for table,old in original_baseline['snapshot']['tables'].items():
 if table=='django_session':continue
 current=current_snapshot['tables'][table]
 assert all(current['rows'].get(k)==h for k,h in old['rows'].items()),table
 assert current['count']==old['count']+{'reference_vehicledefinition':73,'reference_importexecutionreceipt':73}.get(table,0),table

original=[p for p in BASE.rglob('*') if p.is_file() and HERE not in p.parents and '__pycache__' not in p.parts]
assert not any(p.is_symlink() for p in BASE.rglob('*'))
verified=0
for manifest in BASE.rglob('artifact_hashes.json'):
 if HERE in manifest.parents:continue
 entries=load(manifest);entries=entries.get('files',entries)
 for name,value in entries.items():
  assert isinstance(value,str) and value.startswith('sha256:'),(manifest,name)
  options=[manifest.parent/name,ROOT/name]
  path=next((p for p in options if p.is_file()),None)
  assert path is not None and sha(path)==value,(manifest,name)
  verified+=1
print('Verified',verified,'retained artifact hash entries',flush=True)
for p in original:
 if p.suffix=='.json':load(p)
save('artifact_inventory.json',{'files':{str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(original)},'count':len(original),'bytes':sum(p.stat().st_size for p in original),'suffix_counts':dict(collections.Counter(p.suffix for p in original)),'verified_prior_hash_entries':verified})
matrix,approval,rows,candidates=execution.inputs()
assert helpers.counts()=={'VehicleDefinitions':934,'audit_receipts':3148,'correspondences':159}
status=MatrixYear(matrix,approval,2021,candidates).status()
assert status['complete'] and status['counts']=={'previously_completed':73}
save('matrix_receipt_revalidation.json',status)
mapping=load(BASE/'canonical_execution_20261109/resumed_20261109/candidate_to_canonical_mapping.json')['rows']
assert len(mapping)==73
for item in mapping:
 r=VehicleDefinition.objects.get(pk=item['VehicleDefinition_PK']);r.clean()
 assert r.generation_id==32 and r.model_year==2021 and r.market=='US'
 assert str(r.uuid)==item['UUID'] and r.slug==item['slug']==r.build_slug()
 assert record_powertrain(r)==item['canonical_powertrain']==candidates[item['row_id']].canonical_powertrain
 assert all(record_powertrain(r)[f] is not None for f in FIELDS)
 receipt=ImportExecutionReceipt.objects.get(pk=item['receipt_PK'],created_vehicle_definition=r)
 assert receipt.manifest_hash==item['execution_manifest_hash'] and receipt.target_fields_json==item['target_fields']
 assert receipt.resolution_snapshot_json['candidate_hash']==item['candidate_digest']
 assert receipt.resolution_snapshot_json['matrix']['matrix_digest']==execution.EXPECTED
 validate_documents(receipt.resolution_snapshot_json['generation_resolution']['documents'],verify_bytes=True)
assert {r['VehicleDefinition_PK'] for r in mapping}==set(range(877,950))
assert {r['receipt_PK'] for r in mapping}==set(range(3076,3149))
assert collections.Counter(r['body_style'] for r in mapping)=={'2-door':23,'4-door':50}
assert len({r['target_fields']['trim_name'] for r in mapping})==24
assert not any(r['model_code']=='JLUL74' or r['row_id']=='JL21-71' for r in mapping)
publications=load(BASE/'generation_publication_20261109/publication_results.json')['results']
assert len(publications)==95 and {x['revision_PK'] for x in publications}==set(range(65,160))
for pub in publications:
 r=GenerationCorrespondenceRevision.objects.get(pk=pub['revision_PK'],uuid=pub['revision_uuid']);r.clean()
 assert r.generation_id==32 and r.content_hash==pub['content_hash']==digest(r.review_payload())
 receipt=ImportExecutionReceipt.objects.get(pk=pub['receipt_PK'],correspondence_revision=r)
 assert receipt.resolution_snapshot_json['review']==r.review_payload()
 assert receipt.manifest_hash==r.content_hash
execution.unchanged_files()
print('73 identities,receipts,Matrix lineage and95 publications verified',flush=True)
# A consistent copy is the only writable database opened by this script.
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
checkpoint=ROOT/'backups/review'/('MY2021_commit_checkpoint_'+stamp+'.sqlite3')
assert not checkpoint.exists()
source=helpers.ro(ROOT/'db.sqlite3');before=helpers.snapshot(source)
copy=sqlite3.connect(checkpoint);source.backup(copy)
# Read the prior sanitized account policy without exposing operational account values.
with tempfile.TemporaryDirectory(prefix='my2021-prior-checkpoint-') as temp:
 old=Path(temp)/'prior.sqlite3';old.write_bytes(subprocess.check_output(['git','show','5a451d2:db.sqlite3'],cwd=ROOT))
 previous=helpers.ro(old)
 oldcols=[r[1] for r in previous.execute('pragma table_info(accounts_user)')]
 oldrows=previous.execute('select * from accounts_user order by id').fetchall()
 newrows=copy.execute('select * from accounts_user order by id').fetchall()
 assert len(oldrows)==len(newrows)==1 and oldrows[0][oldcols.index('id')]==17
 sanitized_columns={'username','password','last_login','email','display_name'}
 for oldrow,newrow in zip(oldrows,newrows):
  for i,col in enumerate(oldcols):
   if col not in sanitized_columns:assert oldrow[i]==newrow[i], 'Unexpected account state outside established sanitization policy'
  copy.execute('update accounts_user set username=?,password=?,last_login=?,email=?,display_name=? where id=?',tuple(oldrow[oldcols.index(k)] for k in ['username','password','last_login','email','display_name','id']))
 previous.close()
copy.execute('pragma secure_delete=ON')
session_count=copy.execute('select count(*) from django_session').fetchone()[0]
# Secret values are inspected only in memory and never logged or serialized.
private_values=[v for row in source.execute('select session_key,session_data from django_session') for v in row if isinstance(v,str) and len(v)>8]
private_values += [r[0] for r in source.execute('select password from accounts_user') if isinstance(r[0],str) and len(r[0])>8]
copy.execute('delete from django_session');copy.commit();copy.execute('vacuum')
assert copy.execute('pragma integrity_check').fetchone()[0]=='ok'
assert copy.execute('pragma foreign_key_check').fetchall()==[]
assert copy.execute('select count(*) from django_session').fetchone()[0]==0
assert copy.execute("select count(*) from accounts_user where password != '!' or email != '' or last_login is not null").fetchone()[0]==0
assert not copy.execute("select name from sqlite_master where type='table' and (lower(name) like '%token%' or lower(name) like '%secret%' or lower(name) like '%credential%')").fetchall()
after=helpers.snapshot(copy)
for table,original_table in before['tables'].items():
 if table not in {'accounts_user','django_session'}:assert after['tables'][table]==original_table,table
assert before['schema_digest']==after['schema_digest'] and before['sequences']==after['sequences']
copy.close();source.close()
raw=checkpoint.read_bytes();assert all(value.encode() not in raw for value in private_values)
# Scan publication-bound text for exact operational session/password secrets, without printing them.
for p in original:
 if p.suffix!='.pdf':
  data=p.read_bytes();assert all(value.encode() not in data for value in private_values),'Private authentication value found in retained artifact: '+str(p.relative_to(ROOT))
# Simulate restoration into a distinct throwaway development DB, never live.
with tempfile.TemporaryDirectory(prefix='my2021-restore-') as temp:
 restored=sqlite3.connect(Path(temp)/'development.sqlite3');src=helpers.ro(checkpoint);src.backup(restored);src.close()
 assert restored.execute('pragma integrity_check').fetchone()[0]=='ok' and not restored.execute('pragma foreign_key_check').fetchall()
 assert helpers.snapshot(restored)==after
 assert tuple(restored.execute('select count(*) from '+t).fetchone()[0] for t in ['reference_vehicledefinition','reference_importexecutionreceipt','reference_generationcorrespondencerevision'])==(934,3148,159)
 restored.close()
assert sha(ROOT/'db.sqlite3')==live_hash
save('checkpoint_report.json',{'status':'passed','checkpoint_path':str(checkpoint),'checkpoint_sha256':sha(checkpoint),'live_database_before_sha256':live_hash,'live_database_after_sha256':sha(ROOT/'db.sqlite3'),'live_database_unchanged':True,'totals':helpers.counts(),'MY2021_definitions':73,'MY2021_execution_receipts':73,'MY2021_published_correspondences':95,'body_distribution':{'2-door':23,'4-door':50},'labels':24,'complete_five_field_identities':73,'Matrix_digest':execution.EXPECTED,'SQLite_integrity':'ok','foreign_key_violations':0,'canonical_and_all_other_non_authentication_tables_identical':True,'session_rows_removed_from_copy_only':session_count,'sanitized_account_PKs':[17],'sanitized_columns':sorted(sanitized_columns),'password':'unusable marker; no credentials retained','private_session_and_password_bytes_absent':True,'publication_artifact_authentication_secret_scan':'passed','restoration_to_separate_development_copy':'passed;all tables matched;934/3148/159','python':sys.version,'interpreter':sys.executable,'dependencies':{n:importlib.metadata.version(n) for n in ['Django','pypdf']},'prior_sanitization_policy_commit':'5a451d2','no_application_contract_or_migration_changes':True})
print('SANITIZED CHECKPOINT PASSED:',checkpoint,sha(checkpoint),flush=True)
