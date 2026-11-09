"""Bounded offline construction; writes only this review directory, never queries DB."""
import os,sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT));os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from pypdf import PdfReader
from reference.ingestion.contracts import *
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.serialization import serialize_artifact,deserialize_artifact,candidate_config_doc_to_dict,adjudication_to_dict,adjudication_from_dict,compute_adjudication_hash
from reference.ingestion.validation import validate_candidate_configuration,validate_source_assertion_set
from reference.ingestion.importing.powertrain_identity import candidate_powertrain
from reference.ingestion.generation_correspondence import digest,validate_documents
from reference.ingestion.classification_adjudication import validate_classification_adjudication
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;NOW=datetime.now(timezone.utc).isoformat()
def rel(p):return str(p.relative_to(ROOT))
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,o):p.write_text(json.dumps(o,indent=2,ensure_ascii=False)+'\n')
if (HERE/'candidate_index.json').exists():
 raise SystemExit('Review artifacts already exist; preserve them and use a separately authorized revision directory.')
rows=json.loads((BASE/'preliminary_factory_offerings.json').read_text())['rows'];tables=json.loads((BASE/'evidence/powertrain_table_excerpts.json').read_text())['tables'];inventory=json.loads((BASE/'source_revision_inventory.json').read_text());guides={g['source_id']:g for g in inventory['retained_guides']}
manual=HERE/'evidence/Mopar_MY2020_Wrangler_US_owners_manual.pdf';reader=PdfReader(manual);fuel=reader.pages[283].extract_text();hardware='\n'.join(reader.pages[i].extract_text() for i in [285,286,287]);save(HERE/'evidence/manual_selected_pages.json',{'url':'https://vehicleinfo.mopar.com/assets/publications/en-us/Jeep/2020/Wrangler/P138305_20_JL_OM_EN_USC_DIGITAL.pdf','title':'2020 Jeep Wrangler Owner’s Manual, US/Canada edition','source_hash':sha(manual),'extraction':'pypdf '+__import__('pypdf').__version__,'pages':[{'pdf_page':i+1,'text':reader.pages[i].extract_text()} for i in [283,285,286,287]]})
def sas(sid,path,url,native,assertions,notes):
 s=SourceAssertionSet(Envelope('rigarchive.source_assertion_set.v1','1.1.0',NOW,'bounded_my2020_review'),SourceMetadata(sid,'manufacturer_document',url,NOW,native,'retained authentic PDF',notes,'reviewed',{'model_year':2020},SourceApplicability('US','US model-year guide/manual applicability; engine-family joins explicitly scoped','US','model_year'),ExtractionProvenance(sha(path),rel(path),'pypdf','6.16.1','source_specific_parser')),assertions)
 validate_source_assertion_set(s);assert serialize_artifact(deserialize_artifact(serialize_artifact(s)))==serialize_artifact(s)
 p=HERE/'assertion_sets'/f'{native}.json';p.write_text(serialize_artifact(s)+'\n');return s
fuelset=sas('Mopar_MY2020_Wrangler_US_manual',manual,'https://vehicleinfo.mopar.com/assets/publications/en-us/Jeep/2020/Wrangler/P138305_20_JL_OM_EN_USC_DIGITAL.pdf','MY2020-manual-fuel-hardware',[SourceAssertion('fuel2','fuel_requirements',fuel.split('2.0L E NGINE')[1].split('3.6L E NGINE')[0],'PDF page284 / printed282, 2.0L ENGINE'),SourceAssertion('fuel36','fuel_requirements',fuel.split('3.6L E NGINE')[1].split('WARNING!')[0],'PDF page284 / printed282, 3.6L ENGINE'),SourceAssertion('hardware','engine_hardware',hardware,'PDF pages286–288; cooling system and underhood drawings; applicability must not be inferred beyond each caption')],'US gasoline-family fuel sections; no inferred classifications encoded as manufacturer statements.')
context_docs=json.loads((ROOT/'docs/implementation/handoffs/MY2019_JL/director_review/erc_classification_proposals_20261108/evidence/supporting_documents.json').read_text())
validate_documents(context_docs,verify_bytes=True)
save(HERE/'evidence/MY2019_context_documents.json',{'use':'Context only; no MY2019 human approval extends to MY2020; source applicability unchanged','documents':context_docs})
specpath=BASE/'source_pdfs/FCA_2020_Wrangler_US_specifications.pdf'
spectext=PdfReader(specpath).pages[0].extract_text()
specset=sas('FCA_MY2020_Wrangler_US_specs',specpath,inventory['supplementary_sources'][0]['url'], 'MY2020-US-specs',[SourceAssertion('layout','generic_drive_classification','Longitudinal front engine, four-wheel drive','PDF page1, BODY/CHASSIS Layout'),SourceAssertion('pentastar','manufacturer_powertrain_description',spectext,'PDF page1, ENGINE 3.6-LITER PENTASTAR V-6; source-specific guide governs edition availability')],'Retained manufacturer US specification; generic early availability does not override later guide offerings.')
index=[];proposals=[];observations=[]
for row in rows:
 rid=row['research_row_id'];matching=[t for t in tables if t['excerpt_id'] in row['evidence_excerpt_ids']];primary=next(t for t in matching if t['source_id'].endswith('2020-03-03'))
 # Every positive revision is retained in a genuine source assertion set. Only the primary revision supplies mapped interpretations.
 sets=[]
 for t in matching:
  g=guides[t['source_id']];path=ROOT/t['document'];assert sha(path)==t['document_sha256']
  s=sas(t['source_id'],path,g['url'],rid+'-'+t['source_id'],[SourceAssertion(rid+'-'+t['source_id']+'-table','factory_powertrain_table',t['powertrain_table_text'],f"PDF page {t['pdf_page_1_based']}; model {row['model_code']}; selected grade {row['trim_name_proposal']}; QOP {','.join(row['cpos_codes'])}; normalization is not a verbatim manufacturer trim assertion"),SourceAssertion(rid+'-'+t['source_id']+'-model','source_model_code',t['model_code'],f"PDF page {t['pdf_page_1_based']}; printed model heading")], 'Manufacturer-issued guide, archived copy. Revision omissions do not rescind earlier positive cells.')
  sets.append(s)
 primaryset=next(s for s in sets if s.provenance.source_id==primary['source_id']);table_ref=primaryset.source_assertions[0].assertion_id
 # Exact engine segment in authentic table, avoiding unrelated engines in the same page.
 text=primary['powertrain_table_text'];lines=text.replace('\\n','\n').splitlines();starts=[i for i,l in enumerate(lines) if __import__('re').match(r'^\d\.\dL ',l.strip())];segments=['\n'.join(lines[a:(starts[n+1] if n+1<len(starts) else len(lines))]) for n,a in enumerate(starts)];segment='\n'.join(line[:52].rstrip() for line in next(x for x in segments if '('+row['engine_code']+')' in x).splitlines())
 eng=sas(primary['source_id'],ROOT/primary['document'],guides[primary['source_id']]['url'],rid+'-engine',[SourceAssertion(rid+'-engine','engine_descriptor',segment,f"PDF page {primary['pdf_page_1_based']}; {row['model_code']}; QOP {','.join(row['cpos_codes'])}; exact engine table segment")],'Explicit descriptor and engine-code binding in the same table; classifications not expressed remain null.')
 header=sas(primary['source_id'],ROOT/primary['document'],guides[primary['source_id']]['url'],rid+'-heading',[SourceAssertion(rid+'-heading','source_document_heading',PdfReader(ROOT/primary['document']).pages[0].extract_text(),'PDF page1; US MY2020 model/body applicability')],'Explicit document applicability, not caller target context.')
 sets.extend([eng,fuelset,specset,header]);vals=row['proposed_structured_powertrain'];unknown=row['unapproved_classification_fields'];interps=[]
 for key,value in vals.items():
  if key in unknown:continue
  ref=rid+'-engine'
  if key=='fuel_type' and value=='gasoline':ref='fuel36' if row['engine_code'] in ['ERC','ERG'] else 'fuel2'
  interps.append(NormalizedInterpretation(rid+'-'+key,ref,key,TechnicalValue(value,'L',segment) if key=='engine_displacement_liters' else value,normalization_notes='Direct source terminology normalized; gasoline family joined to exact guide engine displacement/code; no MY2019 human approval propagated.'))
 for key,value in [('make','Jeep'),('model','Wrangler'),('model_year',2020),('market','US')]:interps.append(NormalizedInterpretation(rid+'-'+key,rid+'-heading',key,value,normalization_notes='Document first-page manufacturer/model/year/United States heading; market is independently sourced.'))
 interps.append(NormalizedInterpretation(rid+'-trim',table_ref,'trim',row['trim_name_proposal'],normalization_notes='Proposed body-aware grade normalization from model heading plus marketed-grade column; High Altitude label remains explicitly review-required. QOP option is not independently treated as grade proof.'))
 interps.append(NormalizedInterpretation(rid+'-drive','layout','generic_drive_classification','4WD',normalization_notes='Manufacturer US model layout, applicable to both bodies; no optional transfer-case permutation changes generic drive identity.'))
 from reference.ingestion.importing.powertrain_identity import _supports
 c=construct_candidate_configuration(CandidateIdentity('Jeep','Wrangler',None,2020,'US',row['trim_name_proposal']),sets,interps,candidate_reference=rid,created_at=NOW,schema_version='2.1.0')
 validate_candidate_configuration(c);candidate_powertrain(c,verify_bytes=True);validate_documents(c.evidence_documents,verify_bytes=True)
 path=HERE/'candidates'/f'{rid}.candidate.2.1.0.json';path.write_text(serialize_artifact(c)+'\n');assert serialize_artifact(deserialize_artifact(path.read_text()))==serialize_artifact(c)
 ch=digest(candidate_config_doc_to_dict(c));entry={**row,'candidate_artifact':rel(path),'candidate_hash':ch,'artifact_sha256':sha(path),'canonical_powertrain':c.canonical_powertrain,'status':'constructed; unapproved fields null','primary_excerpt':primary['excerpt_id'],'source_assertion_sets':[rel(HERE/'assertion_sets'/f'{s.provenance.native_record_id}.json') for s in sets]};index.append(entry)
 if unknown:
  refs=['|'.join((d['source_id'],d['raw_artifact_hash'],d['assertion_set_id'],a['assertion_id'])) for d in c.evidence_documents for a in d['assertions'] if a['attribute_key'] in ['engine_descriptor','engine_hardware']]
  claims={}
  for key in unknown:
   reasoning=('Pentastar-family induction conclusion proposed from the 3.6L V6 specification/guide family and existing MY2019 research, not an explicit MY2020 aspiration assertion.' if key=='engine_aspiration' else 'Proposed conventional powertrain classification from differentiated engine offerings and hardware descriptions. ESS or missing eTorque wording alone is insufficient; exact code-to-hardware applicability remains a review limitation.')
   if key=='electrification_type' and row['engine_code']=='EC1':reasoning='MY2020 US manual printed284–285 positively distinguishes 2.0L intercooler without MGU from with-MGU and battery-coolant architecture. The exact order-guide EC1/ESS offering is paired against distinct EC3/eTorque offerings. Proposed none joins the non-MGU variant to EC1; this code-to-hardware association is a bounded engineering conclusion, not a direct manufacturer assertion and not ESS terminology alone.'
   if key=='electrification_type' and row['engine_code']=='ERC':reasoning='Combined US MY2020 separate ERC ESS versus ERG eTorque order-guide offerings, manufacturer Pentastar description, MY2020 optional 3.6 MGU/battery hardware, and retained MY2019 conventional alternator versus ERG BSG context support proposed none. Continuity of ERC conventional architecture into these exact MY2020 offerings requires fresh human judgment; no cross-year approval or absence-only reasoning is used.'
   claims[key]={'value':vals[key],'reasoning':reasoning,'applicability':f"Only {rid}: US MY2020 {row['body_style']} {row['trim_name_proposal']}, {row['engine_code']}, {row['model_code']}, QOP {','.join(row['cpos_codes'])}; candidate digest {ch}",'limitations':'No extension of MY2019 approvals. No final human approval. Family joins are engineering conclusions; exact engine-code hardware/induction corroboration required before approval if current evidence is judged insufficient. Missing archive revisions may affect scope history.','confidence':'low' if row['engine_code']=='EXJ' else 'moderate','source_assertion_refs':refs+(['|'.join((d['source_id'],d['raw_artifact_hash'],d['assertion_set_id'],a['assertion_id'])) for d in context_docs for a in d['assertions']] if row['engine_code'] in ['ERC','ERG'] else []),'evidence_status':'unsupported' if row['engine_code']=='EXJ' else 'supported'}
  adj=CanonicalImportAdjudication('1.1',NOW,'pending_human_signoff','',rid,{'source_id':'human_classification_adjudication','source_identity_type':'candidate_digest','native_identifier':ch},'missing_classification','evidence_backed_classification','proposed_classifications',row['trim_name_proposal'],'Unapproved bounded engineering proposal; no canonical fact or import authorization.',{'candidate_artifact_reference':rel(path),'candidate_hash':ch,'supporting_documents':[d for d in c.evidence_documents if d['source_id'] in ['Mopar_MY2020_Wrangler_US_manual','FCA_MY2020_Wrangler_US_specs']]+(context_docs if row['engine_code'] in ['ERC','ERG'] else []),'classifications':claims})
  adj.adjudication_hash=compute_adjudication_hash(adjudication_to_dict(adj));validate_classification_adjudication(adj)
  ap=HERE/'classification_proposals'/f'{rid}.adjudication.1.1.proposed.json';save(ap,adjudication_to_dict(adj));validate_classification_adjudication(adjudication_from_dict(json.loads(ap.read_text())))
  try:validate_classification_adjudication(adj,require_approved=True)
  except Exception:pass
  else:raise AssertionError('Proposal incorrectly accepted as approved')
  proposals.append({'candidate':rid,'engine_code':row['engine_code'],'fields':unknown,'proposal':rel(ap),'adjudication_hash':adj.adjudication_hash})
 identities=[(r['body_style'],r['trim_name_proposal'],r['engine_code']) for r in index];assert len(identities)==len(set(identities))
save(HERE/'candidate_index.json',{'created':NOW,'candidate_contract':'2.1.0','rows':index});save(HERE/'classification_proposal_index.json',{'status':'proposed only; not approved or applied','proposals':proposals});save(HERE/'reviewed_offering_matrix.json',{'research_review_only':True,'not_matrix_certification':True,'rows':index});save(HERE/'validation_results.json',{'candidates':len(index),'unique':len(set(identities)),'source_assertion_sets':len(list((HERE/'assertion_sets').glob('*.json'))),'candidate_and_source_roundtrips':'passed','evidence_byte_validation':'passed','proposals':len(proposals),'field_proposals':sum(len(p['fields']) for p in proposals),'approval_guard':'all proposals rejected as unapproved','complete_structured_powertrains':sum(not r['unapproved_classification_fields'] for r in rows),'database_access':'none'})
print('Constructed',len(index),'candidates;',len(proposals),'proposals')
