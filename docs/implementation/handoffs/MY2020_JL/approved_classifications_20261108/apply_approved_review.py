"""Apply the owner's exact MY2020 approval through the established CLI only.

All scope/hash/evidence gates run before approving any record. All outputs are
exclusive new artifacts; all Django processes use an isolated in-memory DB.
"""
import os,sys,json,hashlib,subprocess,copy,sqlite3
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
H=Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'manage.py').exists());B=H.parent;R=B/'evidence_resolution_20261108';sys.path.insert(0,str(ROOT));os.environ['DJANGO_SETTINGS_MODULE']='config.settings';os.environ['RIGARCHIVE_TEST_DB_PATH']=':memory:';os.environ['PYTHONDONTWRITEBYTECODE']='1'
import django;django.setup()
from reference.ingestion.serialization import deserialize_artifact,serialize_artifact,candidate_config_doc_to_dict,adjudication_from_dict,adjudication_to_dict
from reference.ingestion.classification_adjudication import validate_classification_adjudication,validate_classification_candidate
from reference.ingestion.generation_correspondence import digest,validate_documents
from reference.ingestion.importing.powertrain_identity import candidate_powertrain
from reference.ingestion.validation import validate_candidate_configuration
from reference.powertrain import FIELDS,TAXONOMIES,validate_powertrain
NOW=datetime.now(timezone.utc).isoformat()
def load(p):return json.loads(p.read_text())
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p):return str(p.relative_to(ROOT))
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2,ensure_ascii=False);f.write('\n')
assert not (H/'authorization.json').exists(),'Approval checkpoint already exists; preserve it and inspect before any rerun'
# Verify the complete reviewed checkpoint, including its scope/index and evidence.
manifest=load(R/'artifact_hashes.json');assert all(sha(ROOT/p)==h for p,h in manifest.items()),'Reviewed artifact hash mismatch'
review_preservation=load(R/'preservation_baseline.json');assert all(sha(ROOT/p)==h for p,h in review_preservation['files'].items()),'Historical input changed'
baseline={rel(p):sha(p) for p in B.rglob('*') if p.is_file() and not p.is_relative_to(H)};dbhash=sha(ROOT/'db.sqlite3');assert dbhash==review_preservation['database_sha256'],'Live DB differs from verified review baseline'
rows=load(R/'candidate_index.json')['rows'];props=load(R/'classification_proposal_index.json')['proposals'];table=load(R/'owner_approval_table.json');naming=load(R/'naming_revisions.json')['revisions'];rowmap={r['research_row_id']:r for r in rows}
assert len(rows)==len(rowmap)==49 and set(rowmap)=={f'JL20-{n:02d}' for n in range(1,50)}
assert Counter(r['engine_code'] for r in rows)==Counter({'ERC':17,'ERG':3,'EC1':15,'EC3':6,'EXJ':8})
assert Counter(r['body_style'] for r in rows)==Counter({'2-door':15,'4-door':34})
expected={('ERC','engine_aspiration'):('naturally_aspirated',17),('ERC','electrification_type'):('none',17),('ERG','engine_aspiration'):('naturally_aspirated',3),('EC1','electrification_type'):('none',15),('EXJ','electrification_type'):('none',8)}
assert table['vehicle_count']==49 and table['classification_candidate_count']==43 and table['field_decisions']==60
assert len(table['classifications'])==5
expected_decisions={}
for group in table['classifications']:
 key=(group['engine_code'],group['field']);assert key in expected;value,count=expected[key]
 assert group['proposed_value']==value and group['affected_candidate_count']==count and group['confidence']=='moderate'
 assert len(group['candidate_references'])==len(set(group['candidate_references']))==count
 assert set(group['candidate_references'])=={rid for rid,r in rowmap.items() if r['engine_code']==key[0]}
 for rid in group['candidate_references']:expected_decisions[(rid,key[1])]=value
assert len(expected_decisions)==60
bases={}
for rid,r in rowmap.items():
 c=deserialize_artifact((ROOT/r['candidate_artifact']).read_text());validate_candidate_configuration(c);validate_documents(c.evidence_documents,verify_bytes=True);candidate_powertrain(c,verify_bytes=True)
 ci=c.candidate_identity;assert (ci.manufacturer_name,ci.vehicle_model_name,ci.model_year,ci.market)==('Jeep','Wrangler',2020,'US');assert ci.trim_name==r['trim_name_proposal'] and c.candidate_reference==rid
 assert digest(candidate_config_doc_to_dict(c))==r['candidate_hash'] and sha(ROOT/r['candidate_artifact'])==r['artifact_sha256']
 assert any(a['attribute_key']=='source_model_code' and a['raw_value']==r['model_code'] for d in c.evidence_documents for a in d['assertions'])
 assert any('('+r['engine_code']+')' in str(a['raw_value']) for d in c.evidence_documents for a in d['assertions'] if a['attribute_key']=='engine_descriptor')
 for it in c.normalized_assertions:
  if it.target_attribute_key=='trim' and it.mapping_status=='mapped':assert it.normalized_concept==ci.trim_name
 bases[rid]=c
assert {n['candidate_reference'] for n in naming}=={'JL20-33','JL20-34','JL20-35'}
for n in naming:
 r=rowmap[n['candidate_reference']];c=bases[n['candidate_reference']]
 assert r['candidate_artifact']==n['current_artifact'] and r['candidate_hash']==n['current_hash'];assert c.candidate_identity.trim_name=='Unlimited High Altitude' and r['model_code']=='JLJP74'
 assert c.unknown_fields['research_revision_lineage']['manufacturer_family']=='Wrangler Unlimited Sahara / JLJP74'
 assert c.unknown_fields['research_revision_lineage']['previous_candidate_hash']==n['previous_hash']
assert len({(r['body_style'],r['trim_name_proposal'],r['engine_code']) for r in rows})==49
assert len(props)==43 and len({p['candidate'] for p in props})==43
observed={};proposalmap={}
for p in props:
 rid=p['candidate'];r=rowmap[rid];a=adjudication_from_dict(load(ROOT/p['proposal']));validate_classification_adjudication(a)
 assert a.adjudication_hash==p['adjudication_hash'] and a.adjudication_decision=='proposed_classifications' and a.operator_label=='pending_human_signoff'
 assert a.candidate_reference==rid and a.evidence_anchors['candidate_hash']==r['candidate_hash'] and a.evidence_anchors['candidate_artifact_reference']==r['candidate_artifact'];assert p['engine_code']==r['engine_code']
 for key,claim in a.evidence_anchors['classifications'].items():
  assert (rid,key) in expected_decisions and claim['value']==expected_decisions[(rid,key)]
  assert key in TAXONOMIES and claim['value'] in TAXONOMIES[key] and claim['confidence']=='moderate' and claim['evidence_status']=='supported'
  assert bases[rid].canonical_powertrain[key] is None and claim['source_assertion_refs'] and claim['reasoning'] and claim['limitations']
  assert r['proposed_structured_powertrain'][key]==claim['value'];observed[(rid,key)]=claim['value']
  if r['engine_code']=='EXJ':assert 'Derived engineering classification' in claim['reasoning'] and 'Secondary alternator' in claim['limitations'] and 'Generic gasoline-family manual' in claim['limitations']
 assert set(a.evidence_anchors['classifications'])==set(r['unapproved_classification_fields'])
 # Complete proposed tuple must agree with the reviewed engine-specific tuple and taxonomy.
 values=copy.deepcopy(bases[rid].canonical_powertrain);values.update({k:v['value'] for k,v in a.evidence_anchors['classifications'].items()});validate_powertrain(values,complete=True);assert values==r['proposed_structured_powertrain']
 proposalmap[rid]=a
assert observed==expected_decisions
save(H/'preflight_verification.json',{'result':'passed before any approval','review_manifest_sha256':sha(R/'artifact_hashes.json'),'approval_table_sha256':sha(R/'owner_approval_table.json'),'review_hashes_checked':len(manifest),'candidate_count':49,'proposal_record_count':43,'field_decision_count':60,'scope':'US MY2020 Wrangler JL only','contradiction_assessment':'Validated mapped manufacturer observations/evidence hashes and scoped reviewed derived findings; no contradictory proposal or unsupported taxonomy value found. No new direct-source claim is manufactured by approval.','High_Altitude_current_revisions':['JL20-33','JL20-34','JL20-35'],'EXJ_confidence':'moderate; original derived-evidence limitations unchanged'})
save(H/'preservation_baseline.json',{'files':baseline,'database_sha256':dbhash})
save(H/'authorization.json',{'created_at':NOW,'authority':'Explicit project-owner approval in current task: MY2020 JL Approved Classifications and High Altitude Naming','human_director':'project_owner','scope':'Exactly60 reviewed field decisions on43 US MY2020 Wrangler JL candidates; three existing High Altitude naming revisions accepted as distinct marketed trims','approval_table':rel(R/'owner_approval_table.json'),'approval_table_sha256':sha(R/'owner_approval_table.json'),'review_manifest':rel(R/'artifact_hashes.json'),'review_manifest_sha256':sha(R/'artifact_hashes.json'),'classification_proposal_bindings':props,'High_Altitude_identity_approval':naming,'constraints':'No cross-year/market/engine propagation; no correspondence publication, Matrix certification, import planning/execution or DB writes','workflow':'adjudicate_canonical_import --classification-review; declared operator project_owner; explicit APPROVE CLASSIFICATIONS response authorized by owner'})
print('PRECHECK PASSED: 43 proposal records /60 field decisions; reviewed hashes and identities match',flush=True)
current=[];execution=[]
for r in rows:
 rid=r['research_row_id'];entry=copy.deepcopy(r);entry['superseded_artifacts']=[]
 if rid in proposalmap:
  p=next(p for p in props if p['candidate']==rid);ap=H/'adjudications'/f'{rid}.approved-r1.adjudication.1.1.json';cp=H/'candidates'/f'{rid}.approved-r1.candidate.2.1.0.json';log=H/'cli_audit'/f'{rid}.txt'
  cmd=[str(ROOT/'.venv/bin/python'),'-B',str(ROOT/'manage.py'),'adjudicate_canonical_import','--classification-review',p['proposal'],'--operator','project_owner','--output',rel(ap),'--candidate-output',rel(cp),'--skip-checks']
  result=subprocess.run(cmd,input='APPROVE CLASSIFICATIONS\n',text=True,capture_output=True,cwd=ROOT,env=os.environ,timeout=60);log.parent.mkdir(exist_ok=True);log.write_text(result.stdout+result.stderr);assert result.returncode==0,f'CLI failed for{rid}: see {rel(log)}'
  approved=adjudication_from_dict(load(ap));validate_classification_adjudication(approved,require_approved=True);assert approved.evidence_anchors==proposalmap[rid].evidence_anchors
  before=adjudication_to_dict(proposalmap[rid]);after=adjudication_to_dict(approved);changed={k for k in before if before[k]!=after[k]};assert changed=={'adjudication_decision','operator_label','created_at','adjudication_hash'}
  c=deserialize_artifact(cp.read_text());validate_candidate_configuration(c);validate_classification_candidate(c);candidate_powertrain(c,complete=True,verify_bytes=True);validate_documents(c.evidence_documents,verify_bytes=True)
  for key in FIELDS:
   if key not in approved.evidence_anchors['classifications']:assert c.canonical_powertrain[key]==bases[rid].canonical_powertrain[key]
  assert c.candidate_identity==bases[rid].candidate_identity;assert c.canonical_powertrain==r['proposed_structured_powertrain'];assert serialize_artifact(deserialize_artifact(serialize_artifact(c)))==serialize_artifact(c)
  entry['superseded_artifacts'].append({'artifact':r['candidate_artifact'],'candidate_hash':r['candidate_hash'],'artifact_sha256':r['artifact_sha256'],'reason':'Approved human-classification projection supersedes incomplete candidate'})
  entry.update(candidate_artifact=rel(cp),candidate_hash=digest(candidate_config_doc_to_dict(c)),artifact_sha256=sha(cp),canonical_powertrain=c.canonical_powertrain,unapproved_classification_fields=[],status='complete; approved human classifications',approved_adjudication=rel(ap),approved_adjudication_hash=approved.adjudication_hash,approved_adjudication_file_sha256=sha(ap))
  execution.append({'candidate_reference':rid,'proposal':p['proposal'],'proposal_hash':p['adjudication_hash'],'approved_adjudication':rel(ap),'approved_adjudication_hash':approved.adjudication_hash,'candidate_revision':rel(cp),'candidate_hash':entry['candidate_hash'],'field_decisions':len(approved.evidence_anchors['classifications']),'cli_audit':rel(log),'CLI_exit_code':result.returncode})
 else:
  c=bases[rid];candidate_powertrain(c,complete=True,verify_bytes=True);entry['status']='complete; original validated EC3 evidence retained';assert r['engine_code']=='EC3'
 if rid in {n['candidate_reference'] for n in naming}:
  n=next(n for n in naming if n['candidate_reference']==rid);entry['superseded_artifacts'].append({'artifact':n['previous_artifact'],'candidate_hash':n['previous_hash'],'reason':'Approved High Altitude marketed display normalization; Sahara family preserved'});entry['High_Altitude_distinct_marketed_trim_approval']=rel(H/'authorization.json')
 current.append(entry)
 assert sha(ROOT/'db.sqlite3')==dbhash
print('APPLIED:',sum(e['field_decisions'] for e in execution),'decisions in',len(execution),'new candidate revisions',flush=True)
assert len({(r['trim_name_proposal'],tuple(r['canonical_powertrain'][k] for k in FIELDS),r['market']) for r in current})==49
assert all(sha(ROOT/p)==v for p,v in baseline.items())
save(H/'candidate_index.json',{'created_at':NOW,'candidate_contract':'2.1.0','scope':'49 US MY2020 Wrangler JL;15two-door/34Unlimited;21body/trim variants','naming_approval':rel(H/'authorization.json'),'rows':current})
save(H/'approval_execution_index.json',{'approved_field_decisions':60,'approved_records':43,'candidate_revisions_created':43,'unchanged_EC3_candidates':6,'executions':execution})
con=sqlite3.connect('file:db.sqlite3?mode=ro',uri=True);con.execute('PRAGMA query_only=ON');counts={'VehicleDefinitions':con.execute('SELECT count(*) FROM reference_vehicledefinition').fetchone()[0],'receipts':con.execute('SELECT count(*) FROM reference_importexecutionreceipt').fetchone()[0],'MY2020_JL':con.execute('SELECT count(*) FROM reference_vehicledefinition WHERE generation_id=32 AND model_year=2020').fetchone()[0]};assert counts=={'VehicleDefinitions':812,'receipts':2880,'MY2020_JL':0};assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert not con.execute('PRAGMA foreign_key_check').fetchall();con.close();assert sha(ROOT/'db.sqlite3')==dbhash
save(H/'validation_results.json',{'approved_field_decisions':60,'approved_records':43,'candidate_revisions_created':43,'final_valid_complete_candidates':49,'unchanged_EC3_candidates':6,'High_Altitude_names_verified':3,'candidate_and_adjudication_contracts':'passed','raw_source_bytes_and_approved_lineage':'passed','serialization_roundtrips':'passed','all_reasoning_confidence_applicability_and_limitations_unchanged':True,'semantic_uniqueness':'49 distinct trim/market/five-field tuples','preexisting_files_preserved':len(baseline),'database_unchanged':True,'database_sha256':dbhash,'database_counts':counts,'SQLite_integrity_and_FKs':'passed','generation_correspondences_published':0,'import_plans_generated':0})
print('FINAL VALIDATION PASSED: all49complete; database unchanged',flush=True)
