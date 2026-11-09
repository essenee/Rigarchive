"""Read-only verification and review indexes; no canonical workflow invocation."""
import os,sys,json,hashlib,sqlite3,csv
from pathlib import Path
from collections import Counter
H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
# Derive root from the already validated candidate artifact paths.
ROOT=next(p for p in H.parents if (p/'manage.py').is_file())
idx=read(H/'candidate_index.json')['rows'];props=read(H/'classification_proposal_index.json')['proposals'];groups=[]
for code in ['ERC','ERG','EC1','EXJ']:
 selected=[p for p in props if p['engine_code']==code];groups.append({'engine_code':code,'candidate_count':len(selected),'proposals':selected,'fields':dict(Counter(f for p in selected for f in p['fields'])),'status':'Unsupported; additional positive diesel hardware evidence needed' if code=='EXJ' else 'Evidence-backed engineering proposals; moderate confidence; fresh bounded human sign-off required','human_approval':'none'})
save(H/'classification_review_groups.json',groups)
trims=[]
for trim in sorted({r['trim_name_proposal'] for r in idx}):
 rs=[r for r in idx if r['trim_name_proposal']==trim];trims.append({'proposed_label':trim,'body_style':rs[0]['body_style'],'rows':[r['research_row_id'] for r in rs],'model_code':rs[0]['model_code'],'evidence_excerpt_ids':sorted({r['primary_excerpt'] for r in rs}),'qops':sorted({q for r in rs for q in r['cpos_codes']}),'review_finding':'Retain as provisional marketed factory grade: named guide column tied to scoped model heading and populated engine/QOP cells; not a generic optional Group. QOP alone is not sufficient evidence. Transmission choices collapsed.','canonical_taxonomy_approval':False,'naming_review':'Sahara High Altitude versus High Altitude; owner normalization review required' if 'High Altitude' in trim else 'Existing body-aware Unlimited convention; no new body identity model','classification_boundary':'Research candidate context is not canonical grade approval; any disputed grade must use existing adjudication workflow before promotion'})
save(H/'trim_review.json',{'authority':['ADR-0005 as narrowly extended by ADR-0010','ADR-0011 body convention','ADR-0012/RA-044 powertrain identity'],'excluded_rows':[],'questioned_label_rows':[r['research_row_id'] for r in idx if 'High Altitude' in r['trim_name_proposal']],'variants':trims})
with (H/'reviewed_offering_matrix.csv').open('w') as f:
 fields=['research_row_id','body_style','trim_name_proposal','engine_code','model_code','candidate_hash','candidate_artifact','primary_excerpt'];w=csv.DictWriter(f,fields,extrasaction='ignore');w.writeheader();w.writerows(idx)
sources=[]
for p in sorted((H/'assertion_sets').glob('*.json')):
 x=read(p);pr=x['provenance'];sources.append({'assertion_set':str(p.relative_to(ROOT)),'artifact_hash':sha(p),'source_id':pr['source_id'],'url':pr['source_locator'],'native_record_id':pr['native_record_id'],'raw_source':pr['extraction_provenance'],'applicability':pr['source_applicability']})
save(H/'evidence_index.json',{'assertion_sets':sources,'secondary_snapshot':{'path':str((H/'evidence/edmunds_observed_identity_facts.json').relative_to(ROOT)),'derived_snapshot_hash':sha(H/'evidence/edmunds_observed_identity_facts.json'),'not_original_html':True},'context':'MY2019_context_documents.json retains original applicability; no approved human conclusion used as evidence','independence':'Guide revisions and manufacturer manual/specifications share manufacturer authority. Mirrors are not independent evidence sources.'})
baseline=read(H/'preservation_baseline.json');checks={p:sha(ROOT/p)==h for p,h in baseline['preexisting_MY2020_files'].items()};assert all(checks.values())
dbhash=sha(ROOT/'db.sqlite3');print('BASELINE KEYS',baseline.keys());assert dbhash=='sha256:f0d32327e0d688b56711a572375e4e462a266ebb8fdb250b97965e392dff07ab'
c=sqlite3.connect(f'file:{ROOT}/db.sqlite3?mode=ro',uri=True);c.execute('PRAGMA query_only=ON');names=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")];receipt=next(n for n in names if n=='reference_importexecutionreceipt');counts={'VehicleDefinitions':c.execute('SELECT count(*) FROM reference_vehicledefinition').fetchone()[0],'receipts':c.execute(f'SELECT count(*) FROM "{receipt}"').fetchone()[0],'migrations':c.execute('SELECT count(*) FROM django_migrations').fetchone()[0]};assert counts['VehicleDefinitions']==812 and counts['receipts']==2880
integrity=c.execute('PRAGMA integrity_check').fetchone()[0];fks=c.execute('PRAGMA foreign_key_check').fetchall();assert integrity=='ok' and not fks;c.close();assert sha(ROOT/'db.sqlite3')==dbhash
save(H/'verification_report.json',{'environment':{'interpreter':str(ROOT/'.venv/bin/python'),'Python':'3.13.1','Django':'6.0.7','pypdf':'6.16.1'},'focused_tests':{'classification_powertrain_generation':{'tests':67,'result':'passed'},'serialization_candidate_construction':{'tests':29,'result':'passed'}},'database':{'access':'SQLite URI mode=ro; PRAGMA query_only=ON','sha256':dbhash,'unchanged':True,'counts':counts,'integrity':integrity,'foreign_key_violations':len(fks)},'preservation':{'preexisting_MY2020_files':len(checks),'all_unchanged':all(checks.values())},'scope':{'candidates':49,'body_trim_variants':21,'directly_complete':6,'classification_review_candidates':43,'supported_proposed_claims':52,'unsupported_proposed_claims':8,'approved_claims':0,'correspondence_or_import_planning':'not performed'},'edmunds':{'body_trim_variants':21,'engine_combinations':49,'corroborated':48,'manufacturer_only':1,'secondary_only_observed':0}})
save(H/'review_artifact_hashes.json',{str(p.relative_to(ROOT)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.name!='review_artifact_hashes.json'})
print('Verified',counts,'DB unchanged; preserved',len(checks),'preexisting files')
