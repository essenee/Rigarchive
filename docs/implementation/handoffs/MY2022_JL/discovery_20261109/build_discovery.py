"""Offline research transcription. No Candidates, approvals, ORM or writes to SQLite.
Run from repository root with the explicitly authorized .venv/bin/python -B.
"""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from pypdf import PdfReader

O = Path(__file__).resolve().parent
ROOT = O.parents[4]
def sha(p): return 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, data): (O/name).write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
def read(name): return json.loads((O/name).read_text())
def csvsave(name, rows):
    with (O/name).open('w', newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n');w.writeheader()
        w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()} for r in rows)
# Labels transcribed from MY2022 model headings and QOP column headers only.
LABELS={'JLJL72':{'B':'Sport','K':'Willys Sport','S':'Sport S','W':'Willys'},
'JLJL74':{'B':'Sport','K':'Willys Sport','S':'Sport S','W':'Willys','L':'Altitude','D':'High Tide'},
'JLJP74':{'G':'Sahara','L':'Altitude','N':'High Altitude'},'JLJS72':{'R':'Rubicon'},
'JLJS74':{'R':'Rubicon'},'JLJX74':{'X':'Rubicon 392'},'JLUL74':{'A':'Sport RHD'},
'JLXP74':{'P':'Sahara 4xe','N':'High Altitude'},'JLXS74':{'V':'Rubicon 4xe'}}
PAIRS={'23':('ERC','DEM'),'24':('ERC','DFT'),'22':('EC1','DFT'),'25':('ERG','DFT'),'26':('EXJ','DFV'),'27':('ESG','DFV'),'29':('ECX','DFY')}
inv=read('manufacturer_source_inventory.json');cells=[];excerpts=[];packages=[]
for s in inv:
    path=ROOT/s['retained_path'];assert sha(path)==s['sha256']
    pages=[p.extract_text(extraction_mode='layout') or '' for p in PdfReader(path).pages]
    assert '2022' in pages[0]
    ep=O/'evidence'/(s['source_id']+'.text.json');ep.write_text(json.dumps(pages,indent=2)+'\n')
    s.update(extraction_path=str(ep.relative_to(ROOT)),extraction_sha256=sha(ep),pages=len(pages))
    ds=re.findall(r'(?:REISSUED|ISSUED):\s*(\d\d/\d\d/\d{4})',pages[0]);s['printed_dates']=ds
    s['revision_date']=datetime.strptime(ds[0],'%m/%d/%Y').date().isoformat() if ds else None
    if s['kind']!='ordering_guide':continue
    assert 'United States' in pages[0] and 'FCA' in pages[0]
    s['authenticity']='Manufacturer-issued third-party archived copy: US/MY2022 heading, printed FCA dealer footer, model/QOP table consistency verified; no digital-signature claim.'
    for num,t in enumerate(pages,1):
        if 'POWERTRAIN AVAILABILITY' in t:
            models=set(re.findall(r'\bJL[A-Z]{2}7[24]\b',t));assert len(models)==1
            model=models.pop();raw=re.split(r'PACKAGE CONTENT|PRICE INCLUDES|STEP #3|E - EXTRA COST',t.split('POWERTRAIN AVAILABILITY',1)[1])[0]
            eid=f"{s['source_id']}-p{num}"
            excerpts.append(dict(excerpt_id=eid,source_id=s['source_id'],source_sha256=s['sha256'],pdf_page_1_based=num,model_code=model,text=raw))
            starts=[m.start() for m in re.finditer(r'(?m)^\s*\d\.\dL\s+[VI][468]\b',raw)];assert starts
            for k,start in enumerate(starts):
                seg=raw[start:starts[k+1] if k+1<len(starts) else len(raw)]
                engines=set(re.findall(r'\((E[A-Z0-9]{2})\)',seg));assert len(engines)==1
                eng=engines.pop()
                for q in re.findall(r'\b2[23456789][A-Z]\b',seg):
                    if q=='24V':continue
                    expected,tx=PAIRS[q[:2]];assert eng==expected and '('+tx+')' in seg
                    label=LABELS[model][q[-1]]
                    cells.append(dict(source_id=s['source_id'],source_sha256=s['sha256'],revision_date=s['revision_date'],pdf_page_1_based=num,excerpt_id=eid,model_code=model,body_style=s['body_style'],market='US',marketed_column_label=label,engine_code=eng,transmission_code=tx,quick_order_package=q,manufacturer_engine_segment=seg.strip()))
        if re.search(r'PACKAGE CONTENT|GROUP DETAIL|SELECT - \$ OPTIONS',t):
            packages.append(dict(source_id=s['source_id'],source_sha256=s['sha256'],pdf_page_1_based=num,text=t))
groups=defaultdict(list)
for c in cells:groups[(c['body_style'],c['model_code'],c['marketed_column_label'],c['engine_code'])].append(c)
rows=[]
for i,((body,model,label,eng),obs) in enumerate(sorted(groups.items()),1):
    rows.append(dict(research_row_id=f'JL22-{i:02}',model_year=2022,market='US',body_style=body,model_code=model,marketed_column_label=label,engine_code=eng,electrification_type={'ERG':'mild_hybrid','ECX':'plug_in_hybrid'}.get(eng),classification_status='research projection only; unassessed fields remain null; no owner approval applied',confidence='high for positive guide cell; canonical classification pending',scope_status='owner_RHD_scope_decision' if model=='JLUL74' else 'provisional_consumer',transmission_codes=sorted({c['transmission_code'] for c in obs}),quick_order_packages=sorted({c['quick_order_package'] for c in obs}),first_observed_revision=min(c['revision_date'] for c in obs),last_observed_revision=max(c['revision_date'] for c in obs),evidence=[{k:c[k] for k in ['source_id','source_sha256','pdf_page_1_based','revision_date','quick_order_package','transmission_code']} for c in obs],unresolved_questions=['Approve MY2022 trim normalization and five-field classification; no MY2021 approval carried forward']+(['RHD market/fleet/consumer scope and identity require owner decision'] if model=='JLUL74' else [])+(['High Tide / Jeep Beach grade-versus-package relationship requires review'] if label=='High Tide' else [])))
save('manufacturer_source_inventory.json',inv);csvsave('manufacturer_source_inventory.csv',inv)
save('positive_package_observations.json',cells);save('evidence_index.json',excerpts);save('factory_package_availability_excerpts.json',packages)
save('provisional_configuration_inventory.json',rows);csvsave('provisional_configuration_inventory.csv',rows)
summary=dict(provisional_rows=len(rows),consumer_proposals=sum(r['scope_status']=='provisional_consumer' for r in rows),RHD_review_rows=sum(r['scope_status']!='provisional_consumer' for r in rows),by_body=dict(Counter(r['body_style'] for r in rows)),by_engine=dict(Counter(r['engine_code'] for r in rows)),body_model_label_groups=len({(r['body_style'],r['model_code'],r['marketed_column_label']) for r in rows}),positive_cells=len(cells),powertrain_pages=len(excerpts),package_pages=len(packages),notice='Observed guide union, not certified complete MY2022 factory space or canonical count. Jeep Beach retained separately pending classification.')
save('offering_summary.json',summary)
revisions=[]
for body in ['2-door','4-door']:
    prev=set()
    for s in sorted([s for s in inv if s['body_style']==body],key=lambda s:s['revision_date']):
        now={(c['model_code'],c['marketed_column_label'],c['engine_code'],c['transmission_code']) for c in cells if c['source_id']==s['source_id']}
        revisions.append(dict(source_id=s['source_id'],revision_date=s['revision_date'],positive_pairings=len(now),added=[list(x) for x in sorted(now-prev)],absent_since_previous=[list(x) for x in sorted(prev-now)],notice='Omission is not proven discontinuation; guide observation date is not production boundary.'));prev=now
save('revision_comparison.json',revisions)
# Comparison uses existing discovery, not reconstructed canonical records.
old=json.loads((O.parent.parent/'MY2021_JL/preliminary_factory_offerings.json').read_text())
def label22(r):
    label=r['marketed_column_label'];m=r['model_code']
    if label=='Altitude':label='Sport Altitude' if m=='JLJL74' else 'Sahara Altitude'
    if label=='High Altitude' and m=='JLXP74':label+=' 4xe'
    return ('Unlimited ' if r['body_style']=='4-door' else '')+label
oldmap={(r['body_style'],r['model_code'],r['marketed_trim_proposal'],r['engine_code']):r for r in old}
newmap={(r['body_style'],r['model_code'],label22(r),r['engine_code']):r for r in rows}
comparison=[]
for key in sorted(oldmap.keys()|newmap.keys()):
    a=oldmap.get(key);b=newmap.get(key)
    comparison.append(dict(comparison_key=list(key),status='continuing_observed' if a and b else 'newly_observed_MY2022' if b else 'MY2021_only_not_observed_MY2022',MY2021_row=a['research_row_id'] if a else None,MY2022_row=b['research_row_id'] if b else None,MY2021_pairings=a['engine_transmission_pairings'] if a else [],MY2022_pairings=[b['engine_code']+'/'+x for x in b['transmission_codes']] if b else [],MY2021_evidence=a['excerpt_ids'] if a else [],MY2022_evidence=b['evidence'] if b else [],notice='Comparison-only label alignment, not approved MY2022 normalization. Absence is not confirmed discontinuation.'))
save('MY2021_to_MY2022_comparison.json',comparison);csvsave('MY2021_to_MY2022_comparison.csv',comparison)
print(json.dumps(summary,indent=2));print(Counter(x['status'] for x in comparison))
