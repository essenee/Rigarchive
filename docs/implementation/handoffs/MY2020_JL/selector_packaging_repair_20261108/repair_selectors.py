"""Artifact-only additive shared-selector repair; no publication/import APIs.

Classification declarations carry forward exact approved claims/base bindings;
only supporting evidence and explicit revision notes are extended. Read-only
resolver simulation supplies unsaved proposed revisions at the lookup boundary.
"""
import os,sys,json,hashlib,copy,re
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timezone
from uuid import uuid4
from unittest.mock import patch
from io import StringIO
H=Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if (p/'manage.py').exists());B=H.parent;A=B/'approved_classifications_20261108';sys.path.insert(0,str(ROOT));os.environ['DJANGO_SETTINGS_MODULE']='config.settings';os.environ['PYTHONDONTWRITEBYTECODE']='1'
from django.conf import settings
settings.DATABASES['default']['NAME']='file:'+str(ROOT/'db.sqlite3')+'?mode=ro';settings.DATABASES['default']['OPTIONS']={'uri':True}
import django;django.setup()
from django.db import connection
from django.core.management import call_command
from reference.models import Generation,GenerationCorrespondenceRevision as Revision,ImportExecutionReceipt,VehicleDefinition
from reference.ingestion.contracts import SourceAssertionSet,SourceAssertion,SourceMetadata,SourceApplicability,ExtractionProvenance,Envelope
from reference.ingestion.serialization import serialize_artifact,deserialize_artifact,candidate_config_doc_to_dict,adjudication_from_dict,adjudication_to_dict,compute_adjudication_hash
from reference.ingestion.validation import validate_candidate_configuration,validate_source_assertion_set
from reference.ingestion.classification_adjudication import validate_classification_adjudication,apply_classification_adjudication
from reference.ingestion.generation_correspondence import digest,validate_documents,validate_generation_evidence,validate_review_payload,resolve_generation
from reference.ingestion.normalization.generation import generation_evidence_from_sets,generation_evidence_from_documents
from reference.ingestion.importing.powertrain_identity import candidate_powertrain
from reference.powertrain import FIELDS
from pypdf import PdfReader
connection.cursor().execute('PRAGMA query_only=ON');NOW=json.loads((H/'authorization.json').read_text())['recorded_at'] if (H/'authorization.json').exists() else datetime.now(timezone.utc).isoformat()
def rel(p):return str(p.relative_to(ROOT))
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,x):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():
  assert json.loads(p.read_text())==x,'Existing artifact differs; preserve and stop: '+str(p)
  return
 with p.open('x') as f:json.dump(x,f,indent=2,ensure_ascii=False);f.write('\n')
def textsave(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():
  assert p.read_text()==s,'Existing artifact differs; preserve and stop: '+str(p)
  return
 with p.open('x') as f:f.write(s)
def key(i):return tuple(i[k] for k in ['source_id','source_namespace','identity_type','native_identifier'])
assert not (H/'validation_results.json').exists(),'Completed revision must not be rerun; preserve it'
files={rel(p):sha(p) for p in B.rglob('*') if p.is_file() and not p.is_relative_to(H)};dbhash=sha(ROOT/'db.sqlite3')
assert all(sha(ROOT/p)==v for p,v in load(A/'artifact_hashes.json').items())
rows=load(A/'candidate_index.json')['rows'];original={};groups=defaultdict(dict);representatives={}
for r in rows:
 c=deserialize_artifact((ROOT/r['candidate_artifact']).read_text());validate_candidate_configuration(c);candidate_powertrain(c,complete=True,verify_bytes=True);validate_documents(c.evidence_documents,verify_bytes=True);validate_generation_evidence(c.generation_evidence,c.evidence_documents);assert digest(candidate_config_doc_to_dict(c))==r['candidate_hash'] and sha(ROOT/r['candidate_artifact'])==r['artifact_sha256'];original[r['research_row_id']]=c
 assert (c.candidate_identity.manufacturer_name,c.candidate_identity.vehicle_model_name,c.candidate_identity.model_year,c.candidate_identity.market)==('Jeep','Wrangler',2020,'US')
 for i in c.generation_evidence:
  k=key(i);assert k[1:] == ('source_model_code','model_code',r['model_code']);groups[k][r['research_row_id']]=c
  d=next(d for d in c.evidence_documents if d['source_id']==i['source_id'] and d['raw_artifact_hash']==i['document_hash'] and d['assertion_set_id']==i['assertion_set_id']);representatives.setdefault(k,(d,i))
assert len(rows)==49 and len(groups)==51
assert Counter(r['model_code'] for r in rows)==Counter({'JLJL72':12,'JLJS72':3,'JLJL74':18,'JLJP74':12,'JLJS74':4})
gen=Generation.objects.select_related('vehicle_model__manufacturer').get(pk=32,uuid='38d3c3ac-f825-4406-abb5-c2d12b9129a4');vm=gen.vehicle_model;assert gen.is_active and vm.is_active and vm.manufacturer.is_active and vm.name=='Wrangler' and vm.manufacturer.name=='Jeep' and gen.start_year<=2020 and (gen.end_year is None or gen.end_year>=2020)
assert not Revision.objects.filter(vehicle_model=vm,market='US',start_year__lte=2020,end_year__gte=2020,successor__isnull=True).exists()
save(H/'authorization.json',{'recorded_at':NOW,'authority':'Current owner task: MY2020 JL Generation Correspondence Evidence-Packaging Repair','scope':'Additively revise exactly49 US MY2020 Wrangler JL candidates using51 existing source/model selector groups; preserve60 approved claims and3 High Altitude identities','prior_approval':rel(A/'authorization.json'),'prior_approval_sha256':sha(A/'authorization.json'),'classification_handling':'Carry forward existing approved declarations through supporting-document-only revisions. This is not a new classification decision. Original operator, approval timestamp, base candidate binding and classifications are preserved; notes pin predecessor and current evidence-packaging authorization.','restrictions':'No correspondence publication, canonical DB write, Matrix certification, import plan, import, migration, application/contract change, commit or push'})
save(H/'preservation_baseline.json',{'database_sha256':dbhash,'files':files})
save(H/'contract_verification.json',{'allowed':True,'repair':'Add shared selectors under original existing source/namespace/model keys; retain all original documents and generation identities','minimum_new_shared_documents':51,'candidate_evidence_enrichment_revisions':49,'classification_evidence_declaration_revisions':43,'proof':'Adjudication1.1 permits nonhuman supporting_documents; existing projector appends them and reprojects generation evidence. Claims and original candidate digest binding are unchanged. EC3 no-human declarations can use ordinary additive evidence revisions.','immutable_constraints':'Existing approved candidates cannot be directly mutated. No chained human declaration; exactly one current human declaration per revised human-classified candidate. All original declarations and predecessors remain retained.','resolver_guards':'Every generation key must have applicable reviewed correspondence; every mapping evidence document must occur exactly in each candidate; one active valid target; all current validation retained.'})
shared={};selector_index=[];pdfcache={}
for k in sorted(groups):
 d,i=representatives[k];p=ROOT/d['raw_artifact_reference'];assert sha(p)==d['raw_artifact_hash']
 if str(p) not in pdfcache:pdfcache[str(p)]=[page.extract_text() for page in PdfReader(p).pages]
 pages=pdfcache[str(p)];assert 'United States' in pages[0] and '2020' in pages[0]
 ast=next(a for a in d['assertions'] if a['assertion_id']==i['assertion_id']);match=re.search(r'PDF page\s*(\d+)',ast['source_context']);assert match;page=int(match.group(1));assert k[3] in pages[page-1]
 # Claim is the same manufacturer model-code token at the same retained location.
 # No trim, engine or generation target is asserted in this source document.
 sid=k[0]+'-'+k[3]+'-shared-selector-r1';sas=SourceAssertionSet(Envelope('rigarchive.source_assertion_set.v1','1.1.0',NOW,'MY2020_shared_selector_packaging'),SourceMetadata(k[0],'manufacturer_issued_order_guide_archived_copy',d['source_locator'],d.get('retrieved_at'),sid,'reuse retained authentic manufacturer PDF','Shared extraction of same explicit model-code heading; US MY2020 applicability from cover. Per-candidate facts remain in their original documents.','reviewed',{},SourceApplicability('US','Printed US/MY2020 document cover and exact model-code page heading; same document revision','US','model_year'),ExtractionProvenance(d['raw_artifact_hash'],d['raw_artifact_reference'],'my2020_shared_model_code_selector','1.0.0','manually_verified_transcription')),[SourceAssertion('model_code','source_model_code',k[3],f'PDF page {page}; manufacturer model-code heading, same original location as predecessor assertion {d["assertion_set_id"]}/{ast["assertion_id"]}. Shared across applicable candidate configurations; no engine/trim availability inferred.')])
 validate_source_assertion_set(sas);sp=H/'selectors'/f'{sid}.source_assertion_set.json';textsave(sp,serialize_artifact(sas)+'\n');assert serialize_artifact(deserialize_artifact(sp.read_text()))==serialize_artifact(sas)
 identities,docs=generation_evidence_from_sets([sas]);assert len(identities)==1 and key(identities[0])==k;validate_documents(docs,verify_bytes=True);shared[k]=docs[0];selector_index.append({'key':list(k),'assertion_set':rel(sp),'artifact_sha256':sha(sp),'document':docs[0],'candidate_references':sorted(groups[k]),'source_page':page,'predecessor_raw_hash':d['raw_artifact_hash'],'manufacturer_fact_unchanged':True})
save(H/'selector_index.json',{'shared_selector_count':51,'source_PDFs':len(pdfcache),'selectors':selector_index})
print('Created51 shared selectors from authentic existing source hashes; all original keys retained',flush=True)
current=[];carry=[]
for r in rows:
 rid=r['research_row_id'];old=original[rid];selectors=[copy.deepcopy(shared[k]) for k in sorted({key(i) for i in old.generation_evidence})];entry=copy.deepcopy(r);cp=H/'candidates'/f'{rid}.selector-r1.candidate.2.1.0.json'
 if 'approved_adjudication' in r:
  apath=ROOT/r['approved_adjudication'];oldadj=adjudication_from_dict(load(apath));validate_classification_adjudication(oldadj,require_approved=True);adj=copy.deepcopy(oldadj)
  assert not any(d['source_id']=='human_classification_adjudication' for d in selectors)
  for d in selectors:
   if d not in adj.evidence_anchors['supporting_documents']:adj.evidence_anchors['supporting_documents'].append(d)
  adj.adjudication_notes+=' Evidence-packaging revision authorized separately; original classification decision unchanged. Predecessor '+rel(apath)+' hash '+sha(apath)+' adjudication '+oldadj.adjudication_hash+'. Packaging authorization '+rel(H/'authorization.json')+' hash '+sha(H/'authorization.json')+'.'
  adj.adjudication_hash=compute_adjudication_hash(adjudication_to_dict(adj));validate_classification_adjudication(adj,require_approved=True);np=H/'adjudication_evidence_revisions'/f'{rid}.selector-evidence-r1.approved.json';save(np,adjudication_to_dict(adj));new=apply_classification_adjudication(rel(np))
  before=adjudication_to_dict(oldadj);after=adjudication_to_dict(adj);assert {k for k in before if before[k]!=after[k]}=={'evidence_anchors','adjudication_notes','adjudication_hash'}
  assert adj.evidence_anchors['classifications']==oldadj.evidence_anchors['classifications'] and adj.created_at==oldadj.created_at and adj.operator_label==oldadj.operator_label
  assert all(adj.evidence_anchors[k]==oldadj.evidence_anchors[k] for k in ['candidate_artifact_reference','candidate_hash'])
  assert all(d in adj.evidence_anchors['supporting_documents'] for d in oldadj.evidence_anchors['supporting_documents'])
  # All original manufacturer and other nonhuman evidence remains exactly intact.
  assert all(d in new.evidence_documents for d in old.evidence_documents if d['source_id']!='human_classification_adjudication')
  carry.append({'candidate_reference':rid,'previous_adjudication':rel(apath),'previous_hash':oldadj.adjudication_hash,'evidence_revision':rel(np),'new_hash':adj.adjudication_hash,'classification_claims_unchanged':True,'original_approval_timestamp_and_operator_preserved':True,'new_classification_decisions':0})
  entry['superseded_approved_adjudication']={'artifact':rel(apath),'adjudication_hash':oldadj.adjudication_hash,'artifact_sha256':sha(apath)};entry.update(approved_adjudication=rel(np),approved_adjudication_hash=adj.adjudication_hash,approved_adjudication_file_sha256=sha(np))
 else:
  assert r['engine_code']=='EC3';new=copy.deepcopy(old);new.envelope.created_at=NOW;new.evidence_documents.extend(selectors);new.generation_evidence=generation_evidence_from_documents(new.evidence_documents);new.evidence_raw_hashes=sorted({d['raw_artifact_hash'] for d in new.evidence_documents});new.unknown_fields['selector_packaging_revision']={'previous_candidate_artifact':r['candidate_artifact'],'previous_candidate_hash':r['candidate_hash'],'authorization':rel(H/'authorization.json'),'fact_changes':False};assert all(d in new.evidence_documents for d in old.evidence_documents)
 validate_candidate_configuration(new);candidate_powertrain(new,complete=True,verify_bytes=True);validate_documents(new.evidence_documents,verify_bytes=True);validate_generation_evidence(new.generation_evidence,new.evidence_documents)
 assert new.canonical_powertrain==old.canonical_powertrain and new.candidate_identity==old.candidate_identity and new.normalized_technical_details==old.normalized_technical_details
 assert all(i in new.generation_evidence for i in old.generation_evidence)
 assert {key(i) for i in new.generation_evidence}=={key(i) for i in old.generation_evidence}
 # Only human-qualified classification refs change; all original direct-source mappings survive.
 assert all(i in new.normalized_assertions for i in old.normalized_assertions if not i.source_assertion_ref.startswith('human_classification_adjudication|'))
 textsave(cp,serialize_artifact(new)+'\n');assert serialize_artifact(deserialize_artifact(cp.read_text()))==serialize_artifact(new)
 entry.setdefault('superseded_artifacts',[]).append({'artifact':r['candidate_artifact'],'candidate_hash':r['candidate_hash'],'artifact_sha256':r['artifact_sha256'],'reason':'Additive shared-selector evidence packaging; all facts and identities unchanged'})
 entry.update(candidate_artifact=rel(cp),candidate_hash=digest(candidate_config_doc_to_dict(new)),artifact_sha256=sha(cp),status='complete; shared-selector packaging repaired',selector_documents=[{'source_id':d['source_id'],'assertion_set_id':d['assertion_set_id'],'raw_artifact_hash':d['raw_artifact_hash']} for d in selectors],packaging_authorization=rel(H/'authorization.json'));current.append(entry)
 assert sha(ROOT/'db.sqlite3')==dbhash
save(H/'candidate_index.json',{'candidate_contract':'2.1.0','scope':'49 approved US MY2020 Wrangler JL; evidence-only revisions','rows':current});save(H/'classification_provenance_carryforward.json',{'records':carry,'approved_field_decisions_preserved':60,'new_classification_decisions':0})
print('Created49 revised candidates;60 approved claims unchanged in43 evidence-only declaration revisions',flush=True)
# Produce only unpublished correspondence review artifacts, never import plans.
proposed=[];objects=[]
for k in sorted(shared):
 payload={'review_version':'1.0','revision_uuid':str(uuid4()),'correspondence_uuid':str(uuid4()),'revision_number':1,'supersedes_uuid':None,'vehicle_model_uuid':str(vm.uuid),'generation_uuid':str(gen.uuid),'source_id':k[0],'source_namespace':k[1],'identity_type':k[2],'native_identifier':k[3],'market':'US','start_year':2020,'end_year':2020,'restrictions':{},'evidence':[shared[k]],'finding':'established','reviewer':'Codex evidence-packaging verification; unpublished proposal; publication authorization pending','reviewed_at':NOW,'review_notes':'Exact US MY2020 manufacturer model-code heading retained from authentic guide, unchanged source/hash/page. Same manufacturer/model/code lineage as established prior JL mappings, active existing JL target and in-range model year; no name-only target selection. Shared selector is present byte-for-byte in every matching candidate. Proposed only; no publication authorization asserted.'}
 validate_review_payload(payload);validate_documents(payload['evidence'],verify_bytes=True);ch=digest(payload);pp=H/'correspondence_proposals'/f'{k[0]}-{k[3]}.review.json';save(pp,{'review':payload,'content_hash':ch})
 obj=Revision(uuid=payload['revision_uuid'],correspondence_uuid=payload['correspondence_uuid'],revision_number=1,supersedes=None,vehicle_model=vm,generation=gen,source_id=k[0],source_namespace=k[1],identity_type=k[2],native_identifier=k[3],market='US',start_year=2020,end_year=2020,restrictions={},evidence=[shared[k]],finding='established',reviewer=payload['reviewer'],reviewed_at=datetime.fromisoformat(NOW),review_notes=payload['review_notes'],content_hash=ch);obj.clean();assert obj.pk is None and obj.content_hash==digest(obj.review_payload());objects.append(obj);proposed.append({'key':list(k),'proposal':rel(pp),'content_hash':ch,'revision_uuid':payload['revision_uuid'],'target_generation_PK':32,'candidate_references':sorted(groups[k])})
save(H/'correspondence_proposal_index.json',{'status':'unpublished; read-only verification inputs only','minimum_records_for_unchanged_existing_identity_keys':51,'proposals':proposed})
def lookup(model,year,market,identities):
 assert model.pk==vm.pk and year==2020 and market=='US'
 keys={key(i) for i in identities}
 return [o for o in objects if (o.source_id,o.source_namespace,o.identity_type,o.native_identifier) in keys]
coverage=[]
with patch('reference.ingestion.generation_correspondence._applicable_revisions',side_effect=lookup):
 for r in current:
  c=deserialize_artifact((ROOT/r['candidate_artifact']).read_text());result=resolve_generation(vm,2020,'US',c.generation_evidence,c.evidence_documents,{'trim_name':c.candidate_identity.trim_name,'drivetrain':'4WD'});assert result['basis']=='reviewed_source_correspondence' and result['parents']['generation_id']==32 and result['parents']['generation_uuid']==str(gen.uuid)
  expected={key(i) for i in c.generation_evidence};assert len(result['correspondences'])==len(expected)
  coverage.append({'candidate_reference':r['research_row_id'],'model_code':r['model_code'],'candidate_artifact':r['candidate_artifact'],'candidate_hash':r['candidate_hash'],'source_model_groups':len(expected),'target_generation_PK':32,'target_generation_uuid':str(gen.uuid),'basis':result['basis'],'correspondences':result['correspondences'],'simulation_only':True})
 # Regression proof: the original packaging still fails the exact document guard.
 old=original[rows[0]['research_row_id']]
 try:resolve_generation(vm,2020,'US',old.generation_evidence,old.evidence_documents)
 except Exception as e:assert 'Correspondence source revision does not match candidate evidence' in str(e)
 else:raise AssertionError('Original packaging unexpectedly passed')
 # Missing one required mapping must still fail; no year-only fallback.
 removed=objects.pop(0);affected=next(c for c in original.values() if any(key(i)==(removed.source_id,removed.source_namespace,removed.identity_type,removed.native_identifier) for i in c.generation_evidence));finalrow=next(r for r in current if r['research_row_id']==affected.candidate_reference);c=deserialize_artifact((ROOT/finalrow['candidate_artifact']).read_text())
 try:resolve_generation(vm,2020,'US',c.generation_evidence,c.evidence_documents)
 except Exception as e:assert 'Missing reviewed generation correspondence' in str(e)
 else:raise AssertionError('Missing mapping accepted')
 objects.append(removed)
# Every key has exactly one shared document/proposal; overlapping facts have one target.
assert len(proposed)==len({tuple(p['key']) for p in proposed})==51
assert len({(r['trim_name_proposal'],r['market'],tuple(r['canonical_powertrain'][f] for f in FIELDS)) for r in current})==49
assert all(original[r['research_row_id']].candidate_identity.trim_name=='Unlimited High Altitude' for r in current if r['research_row_id'] in ['JL20-33','JL20-34','JL20-35'])
counts={'VehicleDefinitions':VehicleDefinition.objects.count(),'receipts':ImportExecutionReceipt.objects.count(),'correspondences':Revision.objects.count()};assert counts=={'VehicleDefinitions':812,'receipts':2880,'correspondences':13}
check=StringIO();call_command('check',stdout=check)
with connection.cursor() as cur:
 cur.execute('PRAGMA integrity_check');assert cur.fetchone()[0]=='ok';cur.execute('PRAGMA foreign_key_check');assert not cur.fetchall()
connection.close();assert sha(ROOT/'db.sqlite3')==dbhash and all(sha(ROOT/p)==v for p,v in files.items())
save(H/'coverage_verification.json',{'status':'49/49 resolve against proposed unsaved correspondences; not published coverage','simulation_boundary':'Only _applicable_revisions lookup is supplied with filtered unsaved proposed revisions. Accepted resolver, completeness, exact-document inclusion, content hashes, restrictions and active-target checks execute unchanged against live read-only parents. No DB insert/save/bulk_create or publication function is invoked.','model_code_coverage':dict(Counter(r['model_code'] for r in current)),'required_correspondence_records':51,'duplicates':0,'conflicts':0,'rows':coverage,'negative_checks':{'original_packaging_exact_document_guard':'rejected','missing_required_mapping':'rejected without fallback'}})
save(H/'validation_results.json',{'candidate_revisions':49,'source_selectors':51,'classification_evidence_revisions':43,'approved_field_decisions_preserved':60,'new_classification_decisions':0,'complete_powertrain_identities':49,'High_Altitude_identities_preserved':3,'contract_validation':'passed','raw_source_hashes_and_lineage':'passed','serialization_roundtrips':'passed','uniqueness':'49 distinct identities','correspondence_simulation':'49/49 target JL32;51 unique unpublished reviews','Django_checks':check.getvalue().strip(),'database_counts':counts,'database_sha256_before_and_after':dbhash,'database_unchanged':True,'SQLite_integrity_and_foreign_keys':'passed','preexisting_files_unchanged':len(files),'publications_or_import_plans':0})
print('SUCCESS:49/49 resolver simulations target JL32;51 unique unpublished proposals;DB byte-identical',flush=True)
