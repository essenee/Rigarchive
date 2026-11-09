"""Offline discovery transcription; no Candidate construction or database writes."""
import json,re,csv,hashlib,sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict,Counter
O=Path(__file__).resolve().parent
ROOT=O.parents[3]
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,d):
 with (O/n).open('w') as f:json.dump(d,f,indent=2,ensure_ascii=False);f.write('\n')
def csvsave(n,rows):
 with (O/n).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def iso(d):return datetime.strptime(d,'%m/%d/%Y').date().isoformat()
P={'23':('ERC','DEM'),'24':('ERC','DFT'),'22':('EC1','DFT'),'25':('ERG','DFT'),'26':('EXJ','DFV'),'27':('ESG','DFV'),'29':('ECX','DFY')}
L={'JLJL72':{'B':'Sport','K':'Willys Sport','S':'Sport S','W':'Willys','Q':'80th Anniversary Edition','F':'Freedom','J':'Islander'},'JLJL74':{'B':'Sport','K':'Willys Sport','S':'Sport S','W':'Willys','Q':'80th Anniversary Edition','F':'Freedom','J':'Islander','L':'Sport Altitude'},'JLJP74':{'G':'Sahara','L':'Sahara Altitude','N':'High Altitude'},'JLJS72':{'R':'Rubicon'},'JLJS74':{'R':'Rubicon'},'JLJX74':{'X':'Rubicon 392'},'JLUL74':{'A':'Sport RHD'},'JLXP74':{'P':'Sahara 4xe','N':'High Altitude 4xe'},'JLXS74':{'V':'Rubicon 4xe'}}
inv=json.loads((O/'source_indexes/order_guide_inventory.json').read_text());sources=[];excerpts=[];cells=[];pkg=[]
for r in inv:
 assert r['status']=='retained'
 path=Path(r['retained_path']);assert sha(path)==r['sha256']
 pages=json.loads(Path(r['extraction_path']).read_text());dates=r['printed_dates'];revision=iso(dates[0]);r.update(revision_date_printed=revision,issue_date_printed=iso(dates[-1]),model_year=2021,market='US',authenticity='Manufacturer-issued archived copy: US/MY2021 heading, dealer-use FCA footer, printed issue/reissue dates and model/QOP table consistency; no digital-signature claim.',acquisition='Browser download control; copied unchanged from returned local download path.')
 sid='MY2021-JL-'+('2D-' if r['body_style']=='2-door' else '4D-')+revision;r['source_id']=sid;source_cells=[]
 for num,t in enumerate(pages,1):
  if 'POWERTRAIN AVAILABILITY' not in t:continue
  models=set(re.findall(r'\bJL[A-Z]{2}7[24]\b',t));assert len(models)==1;model=models.pop();assert model in L
  raw=t.split('POWERTRAIN AVAILABILITY',1)[1]
  raw=re.split(r'PACKAGE CONTENT|PRICE INCLUDES|STEP #3|E - EXTRA COST',raw)[0]
  starts=[m.start() for m in re.finditer(r'(?m)^\s*\d\.\dL\s+[VI][468]\b',raw)];assert starts
  eid=f'{sid}-p{num}';pc=[]
  for k,start in enumerate(starts):
   seg=raw[start:starts[k+1] if k+1<len(starts) else len(raw)];engs=set(re.findall(r'\((E[A-Z0-9]{2})\)',seg));assert len(engs)==1,(sid,num,engs);eng=engs.pop()
   for m in re.finditer(r'\b2[23456789][A-Z]\b',seg):
    q=m.group();
    if q=='24V':continue
    expected,tx=P[q[:2]];assert expected==eng and '('+tx+')' in seg,(sid,num,q,eng,tx)
    trim=('Unlimited ' if r['body_style']=='4-door' else '')+L[model][q[-1]]
    cell={'source_id':sid,'revision_date_printed':revision,'body_style':r['body_style'],'model_code':model,'marketed_trim_proposal':trim,'engine_code':eng,'transmission_code':tx,'quick_order_package':q,'pdf_page_1_based':num,'excerpt_id':eid,'source_sha256':r['sha256'],'manufacturer_engine_segment':seg.strip(),'scope_status':'requires_RHD_identity_decision' if model=='JLUL74' else 'proposed_consumer_scope'}
    pc.append(cell);cells.append(cell);source_cells.append(cell)
  assert pc
  excerpts.append({'excerpt_id':eid,'source_id':sid,'document':r['retained_path'],'document_sha256':r['sha256'],'pdf_page_1_based':num,'model_code':model,'extraction_path':r['extraction_path'],'extraction_sha256':sha(Path(r['extraction_path'])),'powertrain_table_text':raw.strip(),'positive_cells':[{k:c[k] for k in ['engine_code','transmission_code','quick_order_package','marketed_trim_proposal']} for c in pc],'notice':'Research transcription and proposed trim normalization, not a Candidate or executable assertion set.'})
 # All optional-package sections retained separately from identity ledger.
 for num,t in enumerate(pages,1):
  matches=[line.strip() for line in t.splitlines() if re.search(r'XTREME|RECON|ANNIVERSARY|80TH|FREEDOM|ISLANDER|HIGH ALTITUDE|RHD|LEFT HAND|RIGHT HAND|ALTERNATOR|STARTER|48.VOLT',line,re.I)]
  if matches:pkg.append({'source_id':sid,'pdf_page_1_based':num,'lines':matches})
 assert len({(c['model_code'],c['quick_order_package']) for c in source_cells})==len(source_cells)
 r['positive_package_cells']=len(source_cells);r['unique_configurations']=len({(c['model_code'],c['marketed_trim_proposal'],c['engine_code']) for c in source_cells});sources.append(r)
groups=defaultdict(list)
for c in cells:groups[(c['body_style'],c['model_code'],c['marketed_trim_proposal'],c['engine_code'])].append(c)
rows=[]
for i,(key,obs) in enumerate(sorted(groups.items()),1):
 b,m,t,e=key;rows.append({'research_row_id':f'JL21-{i:02}','model_year':2021,'market':'US','body_style':b,'model_code':m,'marketed_trim_proposal':t,'engine_code':e,'scope_status':obs[0]['scope_status'],'quick_order_packages':sorted(set(c['quick_order_package'] for c in obs)),'engine_transmission_pairings':sorted({e+'/'+c['transmission_code'] for c in obs}),'first_observed_revision':min(c['revision_date_printed'] for c in obs),'last_observed_revision':max(c['revision_date_printed'] for c in obs),'guide_source_ids':sorted(set(c['source_id'] for c in obs)),'excerpt_ids':sorted(set(c['excerpt_id'] for c in obs)),'positive_observations':len(obs),'availability_notice':'First/last observed guide dates, not production start/end dates.'})
revisions=[]
for b in ['2-door','4-door']:
 prev=set()
 for r in sorted([r for r in sources if r['body_style']==b],key=lambda x:x['revision_date_printed']):
  now={(c['model_code'],c['marketed_trim_proposal'],c['engine_code']) for c in cells if c['source_id']==r['source_id']}
  revisions.append({'source_id':r['source_id'],'revision_date_printed':r['revision_date_printed'],'unique_configurations':len(now),'added_since_previous_retained_revision':[list(k) for k in sorted(now-prev)],'absent_since_previous_retained_revision':[list(k) for k in sorted(prev-now)],'package_cells':r['positive_package_cells']});prev=now
save('source_revision_inventory.json',sources);save('evidence_index.json',excerpts);save('positive_package_observations.json',cells);save('package_and_hardware_excerpt_index.json',pkg);save('preliminary_factory_offerings.json',rows);save('revision_comparison.json',revisions)
csvsave('source_revision_inventory.csv',[{k:r[k] for k in ['source_id','body_style','issue_date_printed','revision_date_printed','url','sha256','retained_path','pages','unique_configurations']} for r in sources])
csvsave('preliminary_factory_offerings.csv',[{k:'|'.join(v) if isinstance(v,list) else v for k,v in r.items()} for r in rows])
summary={'total':len(rows),'consumer_proposals':sum(r['scope_status']=='proposed_consumer_scope' for r in rows),'RHD_review_rows':sum(r['scope_status']!='proposed_consumer_scope' for r in rows),'by_body':dict(Counter(r['body_style'] for r in rows)),'by_engine':dict(Counter(r['engine_code'] for r in rows)),'by_body_and_engine':{b:dict(Counter(r['engine_code'] for r in rows if r['body_style']==b)) for b in ['2-door','4-door']},'body_trim_variants':len({(r['body_style'],r['marketed_trim_proposal']) for r in rows}),'model_codes':dict(Counter(r['model_code'] for r in rows)),'guides':len(sources),'table_excerpts':len(excerpts),'positive_cells':len(cells)}
save('offering_summary.json',summary);print(json.dumps(summary,indent=2))
