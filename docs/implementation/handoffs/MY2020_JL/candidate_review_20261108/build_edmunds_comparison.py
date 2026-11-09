"""Retain manually transcribed identity facts observed in Edmunds expanded specification sections.
No source HTML or manufacturer assertion is claimed for this derived secondary snapshot.
"""
import json,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent
# id, normalized grade, observed Quick Order Package codes, observed engine option labels.
data=[
('401804418','Sport','23B 24B 22B','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401845519','Willys Sport','22K 24K 23K','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401804419','Sport S','23S 24S 22S','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401804422','Unlimited Sport','23B 24B 22B 26B','2.0L I4 DOHC DI Turbo Engine w/ESS; 3.0L V6 Turbo Diesel Engine w/ESS G3'),
('401804424','Black and Tan','24D 22D 23D','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401845575','Unlimited Willys Sport','24K 22K 23K','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401832293','Willys','22W 24W 23W','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401832294','Freedom','24F 23F 22F','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401804423','Unlimited Sport S','26S 22S 23S 24S','2.0L I4 DOHC DI Turbo Engine w/ESS; 3.0L V6 Turbo Diesel Engine w/ESS G3'),
('401804667','Unlimited Sport Altitude','26L 23L 22L 24L','2.0L I4 DOHC DI Turbo Engine w/ESS; 3.0L V6 Turbo Diesel Engine w/ESS G3'),
('401804588','Unlimited Black and Tan','24D 22D 23D','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401832542','Unlimited Willys','22W 23W 24W 26W','2.0L I4 DOHC DI Turbo Engine w/ESS; 3.0L V6 Turbo Diesel Engine w/ESS G3'),
('401832543','Unlimited Freedom','22F 23F 24F','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401804435','Unlimited Sahara','26G 25G 28G 23G','2.0L I4 DOHC DI Turbo eTorque Engine; 3.6L V6 VVT eTorque Engine; 3.0L V6 Turbo Diesel Engine w/ESS G3'),
('401804421','Rubicon','23R 22R 24R','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401804668','Unlimited Sahara Altitude','26L 28L 23L 25L','2.0L I4 DOHC DI Turbo eTorque Engine; 3.6L V6 VVT eTorque Engine; 3.0L V6 Turbo Diesel Engine w/ESS G3'),
('401804420','Unlimited Rubicon','23R 22R 24R','2.0L I4 DOHC DI Turbo Engine w/ESS'),
('401845566','Rubicon Recon','28Y',''),
('401832588','Unlimited North Edition','28E',''),
('401845579','Unlimited Rubicon Recon','28Y',''),
('401852728','Unlimited Sahara High Altitude','26N 28N 25N','3.6L V6 VVT eTorque Engine; 3.0L V6 Turbo Diesel Engine w/ESS G3')]
records=[]
for sid,trim,qops,options in data:
 hybrid=trim in ['Rubicon Recon','Unlimited Rubicon Recon','Unlimited North Edition','Unlimited Sahara High Altitude']
 records.append({'style_id':sid,'url':f'https://www.edmunds.com/jeep/wrangler/2020/st-{sid}/features-specs/','manufacturer_grade_join':trim,'edmunds_grade':trim.replace('Sahara High Altitude','High Altitude'),'body':'4-door' if trim.startswith('Unlimited') else '2-door','base_engine_observation':{'size_liters':'2.0' if hybrid else '3.6','cylinders':'Inline 4' if hybrid else 'V6','type':'Mild hybrid' if hybrid else 'Gas'},'mechanical_engine_options_observed':options.split('; ') if options else [],'quick_order_package_codes_observed':qops.split(),'section_references':['Engine','Mechanical Options','Packages'],'extraction':'Manual transcription of expanded public specification DOM; no original HTML retained; retrieved 2026-11-08','limitations':'Engine-code correspondence is derived using manufacturer QOP table, not a claim Edmunds prints ERC/ERG/EC1/EC3/EXJ.'})
lookup={r['manufacturer_grade_join']:r for r in records};rows=json.loads((H.parent/'preliminary_factory_offerings.json').read_text())['rows'];comparison=[]
for row in rows:
 d=lookup[row['trim_name_proposal']];observed=any(q in d['quick_order_package_codes_observed'] for q in row['cpos_codes']);comparison.append({'research_row_id':row['research_row_id'],'trim':row['trim_name_proposal'],'engine_code':row['engine_code'],'edmunds_url':d['url'],'status':'corroborated' if observed else 'manufacturer_supported_absent_from_Edmunds','basis':'Base engine / explicit engine option plus QOP correspondence' if observed else 'No diesel mechanical option or 26R package in inspected Unlimited Rubicon listing','caveat':'Sahara Altitude 26L package mislabeled Unlimited Sport Altitude on page; diesel option independently listed' if row['trim_name_proposal']=='Unlimited Sahara Altitude' and row['engine_code']=='EXJ' else ''})
(H/'evidence/edmunds_observed_identity_facts.json').write_text(json.dumps({'secondary_only':True,'not_original_HTML':True,'retrieval_date':'2026-11-08','trim_index_url':'https://www.edmunds.com/jeep/wrangler/2020/trims/','records':records},indent=2)+'\n')
(H/'edmunds_comparison.json').write_text(json.dumps({'body_trim_variants_compared':21,'candidate_combinations_compared':49,'corroborated':sum(c['status']=='corroborated' for c in comparison),'manufacturer_supported_absent':1,'Edmunds_only_configurations_observed':[],'no_scope_changes':True,'rows':comparison},indent=2)+'\n')
print('Edmunds comparison:',len(comparison),'rows')
