"""Read-only correspondence assessment. Never publishes or edits candidate evidence."""
import os,sys,json,hashlib,sqlite3
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone
H=Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'manage.py').exists());BASE=H.parent;APPROVED=BASE/'approved_classifications_20261108';sys.path.insert(0,str(ROOT));os.environ['DJANGO_SETTINGS_MODULE']='config.settings'
from django.conf import settings
settings.DATABASES['default']['NAME']='file:'+str(ROOT/'db.sqlite3')+'?mode=ro';settings.DATABASES['default']['OPTIONS']={'uri':True}
import django;django.setup()
from django.db import connection
from django.core.management import call_command
from reference.models import Generation,GenerationCorrespondenceRevision,VehicleDefinition,ImportExecutionReceipt
from reference.ingestion.serialization import deserialize_artifact,candidate_config_doc_to_dict
from reference.ingestion.validation import validate_candidate_configuration
from reference.ingestion.importing.powertrain_identity import candidate_powertrain
from reference.ingestion.generation_correspondence import digest,validate_documents,validate_generation_evidence,resolve_generation
from pypdf import PdfReader
from io import StringIO
connection.cursor().execute('PRAGMA query_only=ON')
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def rel(p):return str(p.relative_to(ROOT))
def save(p,x):
 with p.open('x') as f:json.dump(x,f,indent=2,ensure_ascii=False);f.write('\n')
assert not (H/'coverage_assessment.json').exists(),'Existing assessment must be preserved'
files={rel(p):sha(p) for p in BASE.rglob('*') if p.is_file() and not p.is_relative_to(H)};before=sha(ROOT/'db.sqlite3');manifest=load(APPROVED/'artifact_hashes.json');assert all(sha(ROOT/p)==v for p,v in manifest.items())
gen=Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32,uuid='38d3c3ac-f825-4406-abb5-c2d12b9129a4');vm=gen.vehicle_model;assert gen.is_active and vm.is_active and vm.manufacturer.is_active and vm.name=='Wrangler' and vm.manufacturer.name=='Jeep' and gen.start_year<=2020 and (gen.end_year is None or gen.end_year>=2020)
old=list(GenerationCorrespondenceRevision.objects.filter(pk__in=range(9,14)).select_related('generation'));assert len(old)==5
oldreview=[]
for r in old:
 r.clean();assert r.content_hash==digest(r.review_payload());assert r.generation_id==32 and r.start_year==2019 and r.end_year==2019
 receipt=ImportExecutionReceipt.objects.get(correspondence_revision=r,execution_outcome='created');assert receipt.pk in range(2857,2862)
 oldreview.append({'PK':r.pk,'uuid':str(r.uuid),'model_code':r.native_identifier,'source_id':r.source_id,'start_year':r.start_year,'end_year':r.end_year,'target_generation_PK':r.generation_id,'content_hash':r.content_hash,'receipt_PK':receipt.pk,'reusable_for_MY2020':False,'reason':'Year scope is2019 only; source_id also differs from MY2020 retained candidate identities'})
allcurrent=list(GenerationCorrespondenceRevision.objects.filter(vehicle_model=vm,market='US',start_year__lte=2020,end_year__gte=2020,successor__isnull=True));assert not allcurrent
rows=load(APPROVED/'candidate_index.json')['rows'];groups=defaultdict(dict);candidates={};pdfs={};checks=[];coverage=[]
for row in rows:
 rid=row['research_row_id'];c=deserialize_artifact((ROOT/row['candidate_artifact']).read_text());validate_candidate_configuration(c);candidate_powertrain(c,complete=True,verify_bytes=True);validate_documents(c.evidence_documents,verify_bytes=True);validate_generation_evidence(c.generation_evidence,c.evidence_documents)
 assert digest(candidate_config_doc_to_dict(c))==row['candidate_hash'] and sha(ROOT/row['candidate_artifact'])==row['artifact_sha256'];assert (c.candidate_identity.manufacturer_name,c.candidate_identity.vehicle_model_name,c.candidate_identity.model_year,c.candidate_identity.market)==('Jeep','Wrangler',2020,'US');assert all(i['native_identifier']==row['model_code'] for i in c.generation_evidence)
 candidates[rid]=c;keys=[]
 for i in c.generation_evidence:
  key=tuple(i[k] for k in ['source_id','source_namespace','identity_type','native_identifier']);keys.append(key);groups[key][rid]=c.evidence_documents
  d=next(d for d in c.evidence_documents if d['source_id']==i['source_id'] and d['raw_artifact_hash']==i['document_hash'] and d['assertion_set_id']==i['assertion_set_id']);p=ROOT/d['raw_artifact_reference']
  if str(p) not in pdfs:pdfs[str(p)]=[page.extract_text() for page in PdfReader(p).pages]
  raw=pdfs[str(p)];assert '2020' in raw[0] and 'United States' in raw[0] and row['model_code'] in '\n'.join(raw)
 try:resolve_generation(vm,2020,'US',c.generation_evidence,c.evidence_documents,{'trim_name':c.candidate_identity.trim_name,'drivetrain':'4WD'})
 except Exception as exc:error=str(exc)
 else:raise AssertionError('Unexpected existing coverage; reassess before any publication')
 coverage.append({'candidate_reference':rid,'current_artifact':row['candidate_artifact'],'candidate_hash':row['candidate_hash'],'model_code':row['model_code'],'model_year':2020,'market':'US','complete_powertrain':True,'intended_generation_PK':32,'current_published_coverage':False,'resolver_error':error,'required_identity_keys':[list(k) for k in sorted(set(keys))],'status':'blocked by unshared document-qualified selector evidence'})
for key,byrid in sorted(groups.items()):
 common=set.intersection(*[set(json.dumps(d,sort_keys=True) for d in docs) for docs in byrid.values()]);matching=[]
 for raw in common:
  d=json.loads(raw)
  if d['source_id']==key[0] and any(a['attribute_key']==key[1] and str(a['raw_value']).strip()==key[3] for a in d['assertions']):matching.append(d)
 checks.append({'source_id':key[0],'namespace':key[1],'identity_type':key[2],'model_code':key[3],'applicability':'US MY2020 only','candidate_references':sorted(byrid),'shared_valid_selector_documents':len(matching),'publishable_for_entire_key_group':bool(matching)})
assert len(groups)==51 and len(checks)==51 and all(x['shared_valid_selector_documents']==0 for x in checks)
# Concrete contract counterexample: a selector from one candidate cannot cover its peer.
key=next(iter(sorted(groups)));ids=sorted(groups[key]);a,b=ids[:2];ac,bc=candidates[a],candidates[b];doc=next(d for d in ac.evidence_documents if d['source_id']==key[0] and any(s['attribute_key']==key[1] and str(s['raw_value'])==key[3] for s in d['assertions']));assert doc not in bc.evidence_documents
counter={'source_identity_key':list(key),'candidate_A':a,'candidate_B':b,'same_original_source_hash':any(d['raw_artifact_hash']==doc['raw_artifact_hash'] for d in bc.evidence_documents),'candidate_A_selector':doc,'candidate_B_selector_set_ids':[d['assertion_set_id'] for d in bc.evidence_documents if d['source_id']==key[0]],'exact_evidence_inclusion_for_B':False,'required_resolver_guard':'require(all(doc in documents for doc in row.evidence), Correspondence source revision does not match candidate evidence.)','explanation':'All matching correspondence revisions are applied by source_id/namespace/type/native identifier; there is no per-candidate selector choice. Publishing parallel per-candidate records for the same key would apply them all, fail exact inclusion, and violate minimum/nonduplicate goals. Restriction mismatch is a failure, not a candidate-selection filter.'}
checklog=StringIO();call_command('check',stdout=checklog);counts={'VehicleDefinitions':VehicleDefinition.objects.count(),'receipts':ImportExecutionReceipt.objects.count(),'correspondences':GenerationCorrespondenceRevision.objects.count()};assert counts=={'VehicleDefinitions':812,'receipts':2880,'correspondences':13}
with connection.cursor() as cur:
 cur.execute('PRAGMA integrity_check');integrity=cur.fetchone()[0];cur.execute('PRAGMA foreign_key_check');fks=cur.fetchall()
assert integrity=='ok' and not fks;connection.close();assert sha(ROOT/'db.sqlite3')==before and all(sha(ROOT/p)==v for p,v in files.items())
save(H/'preservation.json',{'database_sha256_before_and_after':before,'preexisting_files':files,'all_unchanged':True})
save(H/'existing_MY2019_correspondences.json',{'correspondences':oldreview,'MY2020_reused':0})
save(H/'identity_key_assessment.json',{'distinct_model_codes':dict(Counter(r['model_code'] for r in rows)),'distinct_document_source_identity_keys':51,'manufacturer_order_guide_PDFs_verified':len(pdfs),'groups':checks})
save(H/'counterexample.json',counter)
save(H/'coverage_assessment.json',{'phase1_result':'blocked; phase2 not authorized because full-coverage condition fails','final_candidates_verified':49,'model_code_coverage':dict(Counter(r['model_code'] for r in rows)),'target':{'generation_PK':gen.pk,'generation_uuid':str(gen.uuid),'name':gen.name,'start_year':gen.start_year,'end_year':gen.end_year,'vehicle_model_UUID':str(vm.uuid),'active_parents':True},'manufacturer_evidence_assessment':'Original US MY2020 order guides positively bind all five native model codes to manufacturer/model/body and year; matching source-code lineage targets existing JL, consistent with previous established mappings. Publication evidence-inclusion gate fails independently of target compatibility; no correspondence finding was published.','existing_MY2020_conflicts_or_duplicates':0,'existing_MY2020_covered':0,'MY2019_reused':0,'new_publications':0,'new_receipts':[],'blocking_keys':51,'rows':coverage,'backup':'Not created: verification gate failed before any database write/publication was permitted','smallest_viable_next_step':'Separately authorize versioned candidate evidence packaging revisions using shared immutable per-source/model selector documents and review the resulting exact generation-evidence coverage. Preserve all classifications and prior evidence/approved lineage; human-adjudicated candidates require supported workflow treatment of their exact base hash, not direct mutation. No application/contract change or new architecture is proposed here.'})
save(H/'verification_results.json',{'database_counts':counts,'database_byte_unchanged':True,'SQLite_integrity':integrity,'FK_violations':len(fks),'Django_check':checklog.getvalue().strip(),'original_candidate_classification_and_evidence_files_preserved':len(files),'publication_performed':False,'no_application_contract_or_candidate_change':True})
print('BLOCKED:51 identity keys lack common selector evidence;49/49 currently uncovered;0 publications.');print('Model coverage',dict(Counter(r['model_code'] for r in rows)));print('Database',counts,'unchanged;Django/SQLite/FK checks passed')
