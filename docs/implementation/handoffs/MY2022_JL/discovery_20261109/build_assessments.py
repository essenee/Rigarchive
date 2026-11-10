"""Research-only field assessments using the unchanged existing support predicate."""
import hashlib,json,os,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
O=Path(__file__).resolve().parent;ROOT=O.parents[4];sys.path.insert(0,str(ROOT))
os.environ['DJANGO_SETTINGS_MODULE']='config.settings';os.environ['RIGARCHIVE_TEST_DB_PATH']=':memory:'
import django
django.setup()
from reference.ingestion.importing.powertrain_identity import _supports
from reference.powertrain import FIELDS

def read(n):return json.loads((O/n).read_text())
def save(n,d):(O/n).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
rows=read('provisional_configuration_inventory.json');cells=read('positive_package_observations.json');inv=read('manufacturer_source_inventory.json')
expected={'ERC':['3.6',6,'naturally_aspirated','gasoline','none'],'ERG':['3.6',6,'naturally_aspirated','gasoline','mild_hybrid'],'EC1':['2',4,'turbocharged','gasoline','none'],'EXJ':['3',6,'turbocharged','diesel','none'],'ECX':['2',4,'turbocharged','gasoline','plug_in_hybrid'],'ESG':['6.4',8,'naturally_aspirated','gasoline','none']}
tech_pages={'ERC':[1,2,5],'ERG':[1,2,4,5],'EC1':[2,4],'EXJ':[3,5],'ECX':[2,4],'ESG':[3,4,5]}
assess=[]
for eng,values in expected.items():
 obs=[c for c in cells if c['engine_code']==eng]
 # Only the engine column supplies direct lexical claims. QOP cells such as 22L
 # are not marketed displacement measurements; transmission/QOP lineage is separate.
 descriptors=sorted({' '.join(line[:21].strip() for line in c['manufacturer_engine_segment'].splitlines()) for c in obs})
 fields={k:(v if any(_supports(d,k,v,jeep=True) for d in descriptors) else None) for k,v in zip(FIELDS,values)}
 assess.append(dict(engine_code=eng,engine_family={'ERC':'3.6 V6 ESS','ERG':'3.6 V6 eTorque','EC1':'2.0 I4 turbo ESS','EXJ':'3.0 V6 turbo diesel ESS','ECX':'2.0 I4 turbo PHEV','ESG':'6.4 V8 HEMI'}[eng],research_values=fields,unresolved_fields=[k for k,v in fields.items() if v is None],possible_values_requiring_review={k:v for k,v in zip(FIELDS,values) if fields[k] is None},approval_status='not_requested_or_applied',manufacturer_descriptors=descriptors,body_styles=sorted({c['body_style'] for c in obs}),transmission_codes=sorted({c['transmission_code'] for c in obs}),affected_rows=[r['research_row_id'] for r in rows if r['engine_code']==eng],guide_refs=[{k:c[k] for k in ['source_id','source_sha256','pdf_page_1_based','revision_date','quick_order_package']} for c in obs],technical_context_refs=[dict(source_id='2022_JP_Wrangler_SP',pdf_pages_1_based=tech_pages[eng],source_sha256=next(s['sha256'] for s in inv if s['source_id']=='2022_JP_Wrangler_SP')),dict(source_id='2022_JP_Wrangler_FA',pdf_pages_1_based=[1],source_sha256=next(s['sha256'] for s in inv if s['source_id']=='2022_JP_Wrangler_FA'))],technical_context_notice='Technical sections are contextual evidence; do not transfer a broad-family statement to every trim without reviewed applicability. Technical page 5 manual/eTorque wording contradicts page 1 and guides.',fuel_grade_note={'ERC':'SP p1: unleaded regular 87 AKI','ERG':'SP p1: unleaded regular 87 AKI','EC1':'SP p2: minimum unleaded regular 87 AKI; 91+ recommended for optimum economy/performance','ECX':'SP p2 includes 4xe in shared 2.0 family; applicability of fuel wording needs review','EXJ':'SP p3: ultra-low sulfur diesel','ESG':'SP p4: premium 91 AKI required; gasoline classification requires reviewed evidence beyond octane terminology'}[eng]))
save('powertrain_evidence_matrix.json',assess)
release=O/'evidence/stellantis_high_tide_release.html'
supp=[dict(source_id='Stellantis_High_Tide_20220207',url='https://www.prnewswire.com/news-releases/jeep-brand-makes-big-splashes-with-2022-wrangler-high-tide-model-and-new-high-velocity-yellow-301476721.html',retained_path=str(release.relative_to(ROOT)),sha256=sha(release),publication_date='2022-02-07',publication_time='13:15 ET',retained_at=datetime.now(timezone.utc).isoformat(),timestamp_basis='Retention verification; download earlier this session',authenticity='Manufacturer-authored release distributed by PR Newswire; News provided by Stellantis and SOURCE Stellantis on retained HTML; not a publisher-hosted domain',source_use='Jeep Beach first-500 High Tide edition relationship and US MY2022 announcement; no separate model/QOP code established',extraction_path=str((O/'evidence/stellantis_high_tide_release.txt').relative_to(ROOT)),extraction_sha256=sha(O/'evidence/stellantis_high_tide_release.txt'))]
if (O/'supplemental_source_inventory.json').exists():
    supp=read('supplemental_source_inventory.json')
save('supplemental_source_inventory.json',supp)
save('raw_source_retention_manifest.json',[{k:r[k] for k in ['source_id','url','retained_path','sha256','acquired_at','acquisition_timestamp_basis','retained_at'] if k in r} for r in inv+supp])
save('edition_and_scope_review.json',[
 dict(label='Jeep Beach',status='manufacturer_confirmed_marketed_edition; identity_unresolved',source_id=supp[0]['source_id'],source_sha256=supp[0]['sha256'],locator='article body: first 500 High Tide vehicles',model_code=None,engine_code=None,transmission_code=None,related_research_row=next(r['research_row_id'] for r in rows if r['marketed_column_label']=='High Tide'),notice='Do not assign High Tide codes by inference or create a separate canonical row without owner review; not counted in 56 guide-union rows'),
 dict(label='Sport RHD',status='separate_owner_scope_review',model_code='JLUL74',guide_row=next(r['research_row_id'] for r in rows if r['model_code']=='JLUL74'),notice='US guide evidence exists; no claim that RHD is automatically fleet-only or excluded from consumer scope'),
 dict(label='Willys 4xe / Freedom / 80th Anniversary / Islander',status='not_established_in_retained_MY2022_guides',notice='No automatic carryforward from MY2021. Calendar-year 2022 announcements may concern MY2023. Not proven nonexistent worldwide or at every production date.')])
print({a['engine_code']:a['research_values'] for a in assess})
