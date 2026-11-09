"""Owner-authorized exact51 publication through accepted CLI, with gated backup.
Parent ORM/verification connections are SQLite read-only; only51 accepted CLI
invocations write the live database. No import or migration workflow is invoked.
"""
import os,sys,json,hashlib,copy,sqlite3,subprocess
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
from unittest.mock import patch
from io import StringIO
H=Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'manage.py').exists());B=H.parent;R=B/'selector_packaging_repair_20261108';sys.path.insert(0,str(ROOT));os.environ['DJANGO_SETTINGS_MODULE']='config.settings';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from django.conf import settings
settings.DATABASES['default']['NAME']='file:'+str(ROOT/'db.sqlite3')+'?mode=ro';settings.DATABASES['default']['OPTIONS']={'uri':True}
import django;django.setup()
from django.db import connection
from django.core.management import call_command
from reference.models import Generation,GenerationCorrespondenceRevision as Revision,ImportExecutionReceipt,VehicleDefinition
from reference.ingestion.serialization import deserialize_artifact,candidate_config_doc_to_dict
from reference.ingestion.validation import validate_candidate_configuration
from reference.ingestion.importing.powertrain_identity import candidate_powertrain
from reference.ingestion.generation_correspondence import digest,validate_documents,validate_generation_evidence,validate_review_payload,resolve_generation
from pypdf import PdfReader
NOW=datetime.now(timezone.utc).isoformat();connection.cursor().execute('PRAGMA query_only=ON')
def rel(p):return str(p.relative_to(ROOT))
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2,ensure_ascii=False);f.write('\n')
def identity(i):return tuple(i[k] for k in ['source_id','source_namespace','identity_type','native_identifier'])
def ro(path):
 c=sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON');return c
# No row contents are written to reports: only per-row hashes/schema/count metadata.
def db_snapshot(c):
 schema=c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_autoindex%' ORDER BY type,name").fetchall();tables={}
 for (name,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall():
  columns=[r[1] for r in c.execute('PRAGMA table_info("'+name+'")')];data=c.execute('SELECT * FROM "'+name+'"').fetchall();pk=[r[1] for r in c.execute('PRAGMA table_info("'+name+'")') if r[5]];assert pk,'No key for preservation comparison: '+name
  positions=[columns.index(p) for p in pk];hashed={hashlib.sha256(json.dumps([r[n] for n in positions],default=str,separators=(',',':')).encode()).hexdigest():hashlib.sha256(json.dumps(list(r),default=str,ensure_ascii=False,separators=(',',':')).encode()).hexdigest() for r in data};assert len(hashed)==len(data);tables[name]={'count':len(data),'columns':columns,'rows':hashed}
 seq=dict(c.execute('SELECT name,seq FROM sqlite_sequence').fetchall());return {'schema_digest':digest(schema),'tables':tables,'sequences':seq}
assert not (H/'preflight.json').exists(),'Checkpoint already exists; preserve and inspect before resuming publication'
source_hashes=load(R/'artifact_hashes.json');assert all(sha(ROOT/p)==v for p,v in source_hashes.items()),'Reviewed packaging checkpoint changed'
files={rel(p):sha(p) for p in B.rglob('*') if p.is_file() and not p.is_relative_to(H)};start_hash=sha(ROOT/'db.sqlite3');rows=load(R/'candidate_index.json')['rows'];proposal_index=load(R/'correspondence_proposal_index.json')['proposals'];selectors=load(R/'selector_index.json')['selectors'];assert len(rows)==49 and len(proposal_index)==51 and len(selectors)==51
assert Counter(r['model_code'] for r in rows)==Counter({'JLJL72':12,'JLJS72':3,'JLJL74':18,'JLJP74':12,'JLJS74':4})
assert VehicleDefinition.objects.count()==812 and ImportExecutionReceipt.objects.count()==2880 and Revision.objects.count()==13
assert ImportExecutionReceipt.objects.order_by('-pk').first().pk==2880
active=Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32,uuid='38d3c3ac-f825-4406-abb5-c2d12b9129a4');vm=active.vehicle_model;assert active.is_active and vm.is_active and vm.manufacturer.is_active and vm.name=='Wrangler' and vm.manufacturer.name=='Jeep'
candidates={};required=defaultdict(set)
for r in rows:
 c=deserialize_artifact((ROOT/r['candidate_artifact']).read_text());validate_candidate_configuration(c);candidate_powertrain(c,complete=True,verify_bytes=True);validate_documents(c.evidence_documents,verify_bytes=True);validate_generation_evidence(c.generation_evidence,c.evidence_documents)
 assert digest(candidate_config_doc_to_dict(c))==r['candidate_hash'] and sha(ROOT/r['candidate_artifact'])==r['artifact_sha256'];assert (c.candidate_identity.manufacturer_name,c.candidate_identity.vehicle_model_name,c.candidate_identity.model_year,c.candidate_identity.market)==('Jeep','Wrangler',2020,'US')
 candidates[r['research_row_id']]=c
 for i in c.generation_evidence:assert i['native_identifier']==r['model_code'];required[identity(i)].add(r['research_row_id'])
assert len(required)==51
proposals=[];objects=[];pdfcache={}
for entry in proposal_index:
 artifact=load(ROOT/entry['proposal']);assert set(artifact)=={'review','content_hash'};p=artifact['review'];ch=artifact['content_hash'];validate_review_payload(p);validate_documents(p['evidence'],verify_bytes=True);assert digest(p)==ch==entry['content_hash'] and p['revision_uuid']==entry['revision_uuid']
 k=tuple(p[n] for n in ['source_id','source_namespace','identity_type','native_identifier']);assert list(k)==entry['key'] and k in required and set(entry['candidate_references'])==required[k]
 assert p['start_year']==p['end_year']==2020 and p['market']=='US' and p['finding']=='established' and p['restrictions']=={} and p['supersedes_uuid'] is None and p['revision_number']==1
 assert p['generation_uuid']==str(active.uuid) and p['vehicle_model_uuid']==str(vm.uuid) and entry['target_generation_PK']==32
 assert len(p['evidence'])==1
 shared=next(x for x in selectors if x['key']==list(k));assert p['evidence']==[shared['document']];assert sha(ROOT/shared['assertion_set'])==shared['artifact_sha256']
 doc=p['evidence'][0];path=ROOT/doc['raw_artifact_reference']
 if str(path) not in pdfcache:pdfcache[str(path)]=[page.extract_text() for page in PdfReader(path).pages]
 raw=pdfcache[str(path)];assert '2020' in raw[0] and 'United States' in raw[0] and k[3] in raw[shared['source_page']-1]
 for rid in required[k]:assert doc in candidates[rid].evidence_documents
 # Any overlapping active source/key record would conflict or duplicate; UUID/chain
 # reuse is forbidden even outside scope. None may exist before this exact set.
 assert not Revision.objects.filter(uuid=p['revision_uuid']).exists()
 assert not Revision.objects.filter(correspondence_uuid=p['correspondence_uuid']).exists()
 assert not Revision.objects.filter(vehicle_model=vm,market='US',source_id=k[0],source_namespace=k[1],identity_type=k[2],native_identifier=k[3],start_year__lte=2020,end_year__gte=2020,successor__isnull=True).exists()
 obj=Revision(uuid=p['revision_uuid'],correspondence_uuid=p['correspondence_uuid'],revision_number=1,supersedes=None,vehicle_model=vm,generation=active,**{n:p[n] for n in ['source_id','source_namespace','identity_type','native_identifier','market','start_year','end_year','restrictions','evidence','finding','reviewer','review_notes']},reviewed_at=datetime.fromisoformat(p['reviewed_at']),content_hash=ch);obj.full_clean(exclude=['content_hash']);assert obj.pk is None and digest(obj.review_payload())==ch;objects.append(obj);proposals.append((entry,p,ch))
assert len({tuple(x[0]['key']) for x in proposals})==51 and {tuple(x[0]['key']) for x in proposals}==set(required)
assert len({p['revision_uuid'] for _,p,_ in proposals})==51 and len({p['correspondence_uuid'] for _,p,_ in proposals})==51
# Reuse accepted resolver unchanged; only its DB lookup gets unsaved proposed rows.
def lookup(model,year,market,identities):
 assert model.pk==vm.pk and year==2020 and market=='US';keys={identity(i) for i in identities};return [o for o in objects if (o.source_id,o.source_namespace,o.identity_type,o.native_identifier) in keys]
sim=[]
with patch('reference.ingestion.generation_correspondence._applicable_revisions',side_effect=lookup):
 for rid,c in candidates.items():
  result=resolve_generation(vm,2020,'US',c.generation_evidence,c.evidence_documents,{'trim_name':c.candidate_identity.trim_name,'drivetrain':'4WD'});assert result['basis']=='reviewed_source_correspondence' and result['parents']['generation_id']==32 and result['parents']['generation_uuid']==str(active.uuid);assert len(result['correspondences'])==len({identity(i) for i in c.generation_evidence});sim.append({'candidate_reference':rid,'target_generation_PK':32,'correspondences':result['correspondences']})
 # Prove each of51 is required by removing it for a candidate that uses the key.
 for o in list(objects):
  k=(o.source_id,o.source_namespace,o.identity_type,o.native_identifier);rid=next(iter(required[k]));c=candidates[rid];objects.remove(o)
  try:resolve_generation(vm,2020,'US',c.generation_evidence,c.evidence_documents)
  except Exception as exc:assert 'Missing reviewed generation correspondence' in str(exc)
  else:raise AssertionError('Unnecessary proposal or weakened coverage guard')
  objects.append(o)
check=StringIO();call_command('check',stdout=check)
assert sha(ROOT/'db.sqlite3')==start_hash and all(sha(ROOT/p)==v for p,v in files.items())
# Consistent SQLite backup to a new ignored project-local file; never replace liveDB.
backup_dir=ROOT/'backups/review';backup_dir.mkdir(parents=True,exist_ok=True);bp=backup_dir/('MY2020_JL_correspondence_prepublication_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite3');assert not bp.exists()
assert subprocess.run(['git','check-ignore','-q',rel(bp)],cwd=ROOT).returncode==0,'Backup must be ignored'
source=ro(ROOT/'db.sqlite3');dest=sqlite3.connect(bp);source.backup(dest);dest.close();source.close();bc=ro(bp);assert bc.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not bc.execute('PRAGMA foreign_key_check').fetchall();baseline=db_snapshot(bc);bc.close();lc=ro(ROOT/'db.sqlite3');assert db_snapshot(lc)==baseline;lc.close();assert sha(ROOT/'db.sqlite3')==start_hash
save(H/'preservation_baseline.json',{'preexisting_files':files,'database_before_sha256':start_hash,'backup':rel(bp),'backup_sha256':sha(bp),'database_snapshot':baseline})
save(H/'preflight.json',{'recorded_at':NOW,'result':'all gates passed before publication','reviewed_manifest_sha256':sha(R/'artifact_hashes.json'),'proposal_index_sha256':sha(R/'correspondence_proposal_index.json'),'candidate_index_sha256':sha(R/'candidate_index.json'),'exact_proposals':proposal_index,'shared_selectors':51,'manufacturer_PDFs_verified':len(pdfcache),'all51_required_by_removal_checks':True,'no_existing_conflicts_duplicates_UUIDs_or_chains':True,'candidate_scope':49,'simulation':sim,'Django_checks':check.getvalue().strip(),'counts':{'VehicleDefinitions':812,'receipts':2880,'correspondences':13},'backup':{'path':rel(bp),'sha256':sha(bp),'integrity':'ok','foreign_keys':'passed','logical_all_table_match_to_live':True},'authorization':'Current explicit owner instruction authorizes exact51 publication after these gates; operator project_owner, agent codex; separate publication confirmation supplied to each accepted CLI'})
print('PREFLIGHT PASSED:51 required;49 resolve in simulation;consistent backup',rel(bp),flush=True)
# Only the existing CLI child processes may write. The parent remains read-only.
results=[];env=os.environ.copy();env.pop('RIGARCHIVE_TEST_DB_PATH',None)
for number,(entry,p,ch) in enumerate(proposals,1):
 assert all(sha(ROOT/q)==v for q,v in source_hashes.items()),'Source checkpoint became stale; stop'
 assert VehicleDefinition.objects.count()==812 and Revision.objects.count()==13+number-1 and ImportExecutionReceipt.objects.count()==2880+number-1,'Unexpected concurrent DB state; stop'
 assert not Revision.objects.filter(uuid=p['revision_uuid']).exists()
 k=entry['key'];assert not Revision.objects.filter(vehicle_model=vm,market='US',source_id=k[0],source_namespace=k[1],identity_type=k[2],native_identifier=k[3],start_year__lte=2020,end_year__gte=2020,successor__isnull=True).exists()
 log=H/'workflow_logs'/f'{number:02d}-{k[0]}-{k[3]}.txt';command=[str(ROOT/'.venv/bin/python'),'-B',str(ROOT/'manage.py'),'publish_generation_correspondence','--review',entry['proposal'],'--operator','project_owner','--agent','codex','--skip-checks'];out=subprocess.run(command,input='yes\n',capture_output=True,text=True,cwd=ROOT,env=env,timeout=60);log.parent.mkdir(exist_ok=True);log.write_text(out.stdout+out.stderr);assert out.returncode==0,'Publication CLI failed; stop and inspect '+rel(log)
 revision=Revision.objects.get(uuid=p['revision_uuid']);assert revision.content_hash==ch and revision.review_payload()==p and revision.generation_id==32;revision.clean();receipt=ImportExecutionReceipt.objects.get(correspondence_revision=revision);assert receipt.execution_outcome=='created' and receipt.operation_type=='correspondence_publication' and receipt.operator_label=='project_owner' and receipt.manifest_hash==ch and receipt.resolution_snapshot_json['review']==p and receipt.resolution_snapshot_json['content_hash']==ch and receipt.resolution_snapshot_json['attribution']['execution_agent']=='codex'
 assert receipt.source_id==p['source_id'] and receipt.native_identifier==p['native_identifier'] and receipt.source_identity_type==p['identity_type'];assert receipt.candidate_reference==p['revision_uuid']
 item={'proposal':entry['proposal'],'content_hash':ch,'source_model_key':entry['key'],'revision_PK':revision.pk,'revision_uuid':str(revision.uuid),'correspondence_uuid':str(revision.correspondence_uuid),'receipt_PK':receipt.pk,'receipt_uuid':str(receipt.uuid),'execution_outcome':receipt.execution_outcome,'target_generation_PK':32,'candidate_references':entry['candidate_references'],'workflow_log':rel(log)};results.append(item);save(H/'publication_records'/f'{number:02d}.json',item)
 print('Published',number,'/51;revision',revision.pk,'receipt',receipt.pk,flush=True)
save(H/'publication_results.json',{'published':51,'results':results,'receipt_PKs':[r['receipt_PK'] for r in results]})
# No patch here: every candidate resolves against the actual published DB state.
actual=[]
for rid,c in candidates.items():
 validate_candidate_configuration(c);candidate_powertrain(c,complete=True,verify_bytes=True);validate_documents(c.evidence_documents,verify_bytes=True);result=resolve_generation(vm,2020,'US',c.generation_evidence,c.evidence_documents,{'trim_name':c.candidate_identity.trim_name,'drivetrain':'4WD'});assert result['basis']=='reviewed_source_correspondence' and result['parents']['generation_id']==32 and result['parents']['generation_uuid']==str(active.uuid)
 wanted={x['revision_uuid']:x['content_hash'] for x in results if rid in x['candidate_references']};assert {x['uuid']:x['hash'] for x in result['correspondences']}==wanted
 actual.append({'candidate_reference':rid,'model_code':next(r['model_code'] for r in rows if r['research_row_id']==rid),'candidate_hash':next(r['candidate_hash'] for r in rows if r['research_row_id']==rid),'basis':result['basis'],'target_generation_PK':32,'target_generation_uuid':str(active.uuid),'correspondences':result['correspondences'],'actual_published_state':True})
assert VehicleDefinition.objects.count()==812 and Revision.objects.count()==64 and ImportExecutionReceipt.objects.count()==2931
lc=ro(ROOT/'db.sqlite3');after=db_snapshot(lc);assert lc.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not lc.execute('PRAGMA foreign_key_check').fetchall();lc.close();assert after['schema_digest']==baseline['schema_digest'];comparison={}
allowed={'reference_generationcorrespondencerevision':51,'reference_importexecutionreceipt':51}
for table,before in baseline['tables'].items():
 now=after['tables'][table];assert now['columns']==before['columns'];assert all(now['rows'].get(k)==v for k,v in before['rows'].items()),'Preexisting data changed in'+table;assert now['count']==before['count']+allowed.get(table,0);comparison[table]={'before':before['count'],'after':now['count'],'all_preexisting_rows_unchanged':True,'new_rows':now['count']-before['count']}
assert set(after['tables'])==set(baseline['tables']);assert set(after['sequences'])==set(baseline['sequences'])
for table,seq in baseline['sequences'].items():assert after['sequences'][table]==seq+allowed.get(table,0),'Unexpected sequence change: '+table
assert sha(bp)==load(H/'preservation_baseline.json')['backup_sha256'];assert all(sha(ROOT/p)==v for p,v in files.items());check=StringIO();call_command('check',stdout=check);connection.close()
save(H/'postpublication_verification.json',{'actual_resolver_coverage':actual,'model_code_coverage':dict(Counter(r['model_code'] for r in rows)),'counts':{'VehicleDefinitions':812,'receipts':2931,'correspondences':64},'new_correspondence_records':51,'new_receipts':51,'receipt_PKs':[r['receipt_PK'] for r in results],'all812VehicleDefinitions_unchanged':True,'all_preexisting_database_rows_unchanged':True,'table_reconciliation':comparison,'schema_unchanged':True,'SQLite_integrity':'ok','foreign_key_violations':0,'Django_checks':check.getvalue().strip(),'backup_path':rel(bp),'backup_sha256':sha(bp),'backup_unchanged':True,'postpublication_database_sha256':sha(ROOT/'db.sqlite3'),'candidate_proposal_evidence_files_unchanged':len(files),'only_writes':'51correspondences+51publicationreceipts+normal sequence advances','no_import_or_migration':True})
print('VERIFIED:49 actual published resolutions;812 VehicleDefinitions unchanged;64 correspondences;2931 receipts',flush=True)
