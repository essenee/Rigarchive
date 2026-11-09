"""Read-only checks of retained MY2021 discovery sources and derived ledgers.

Run from repository root: .venv/bin/python -B .../validate_discovery.py
Does not construct Candidates, invoke ingestion or write any SQLite connection.
"""
import csv,hashlib,json,re,sqlite3,unittest
from collections import Counter,defaultdict
from pathlib import Path
from pypdf import PdfReader
O=Path(__file__).resolve().parent
ROOT=O.parents[3]
def read(name):return json.loads((O/name).read_text())
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
class DiscoveryChecks(unittest.TestCase):
 def test_original_sources_and_extractions(self):
  guides=read('source_revision_inventory.json');self.assertEqual(len(guides),27)
  self.assertEqual(Counter(r['body_style'] for r in guides),{'2-door':13,'4-door':14})
  for r in guides:
   with self.subTest(source=r['source_id']):
    p=ROOT/r['retained_path'];self.assertEqual(sha(p),r['sha256']);pdf=PdfReader(p);layout=read_relative(r['extraction_path'])
    self.assertEqual(len(pdf.pages),r['pages']);self.assertEqual(len(layout),len(pdf.pages));self.assertIn('United States',layout[0]);self.assertIn('2021',layout[0])
    self.assertEqual([pg.extract_text(extraction_mode='layout') for pg in pdf.pages],layout)
  for s in read('supplemental_source_inventory.json'):
   self.assertEqual(sha(ROOT/s['retained_path']),s['document_sha256']);self.assertEqual(sha(ROOT/s['extraction_path']),s['extraction_sha256']);self.assertEqual(len(PdfReader(ROOT/s['retained_path']).pages),s['pages'])
 def test_independent_plain_text_positive_cells(self):
  # Plain extraction checks the layout transcription independently of its segment parser.
  bysource=defaultdict(list)
  for c in read('positive_package_observations.json'):bysource[c['source_id']].append(c)
  for r in read('source_revision_inventory.json'):
   observed=[]
   for pg in PdfReader(ROOT/r['retained_path']).pages:
    t=pg.extract_text()
    if 'POWERTRAIN AVAILABILITY' not in t:continue
    t=re.split(r'PACKAGE CONTENT|PRICE INCLUDES|STEP #3|E - EXTRA COST',t.split('POWERTRAIN AVAILABILITY',1)[1])[0]
    observed.extend(q for q in re.findall(r'\b2[23456789][A-Z]\b',t) if q!='24V')
   self.assertEqual(Counter(observed),Counter(c['quick_order_package'] for c in bysource[r['source_id']]),r['source_id'])
 def test_lineage_and_pairings(self):
  guides={r['source_id']:r for r in read('source_revision_inventory.json')};excerpts={r['excerpt_id']:r for r in read('evidence_index.json')}
  self.assertEqual(len(excerpts),106)
  pairs={'23':('ERC','DEM'),'24':('ERC','DFT'),'22':('EC1','DFT'),'25':('ERG','DFT'),'26':('EXJ','DFV'),'27':('ESG','DFV'),'29':('ECX','DFY')}
  seen=set()
  for c in read('positive_package_observations.json'):
   key=(c['source_id'],c['model_code'],c['quick_order_package']);self.assertNotIn(key,seen);seen.add(key)
   self.assertEqual((c['engine_code'],c['transmission_code']),pairs[c['quick_order_package'][:2]])
   s=guides[c['source_id']];e=excerpts[c['excerpt_id']];self.assertEqual(c['source_sha256'],s['sha256']);self.assertEqual(e['document_sha256'],s['sha256']);self.assertEqual(c['model_code'],e['model_code'])
   self.assertIn(c['quick_order_package'],e['powertrain_table_text']);self.assertIn('('+c['engine_code']+')',c['manufacturer_engine_segment']);self.assertIn('('+c['transmission_code']+')',c['manufacturer_engine_segment'])
  self.assertEqual(len(seen),900)
 def test_union_uniqueness_and_serialization(self):
  rows=read('preliminary_factory_offerings.json');keys={(r['body_style'],r['model_code'],r['marketed_trim_proposal'],r['engine_code']) for r in rows}
  self.assertEqual(len(keys),len(rows));self.assertEqual(len(rows),74);self.assertEqual(json.loads(json.dumps(rows)),rows)
  cells=read('positive_package_observations.json');self.assertEqual(keys,{(c['body_style'],c['model_code'],c['marketed_trim_proposal'],c['engine_code']) for c in cells})
  with (O/'preliminary_factory_offerings.csv').open() as stream:csvrows=list(csv.DictReader(stream))
  self.assertEqual(len(csvrows),len(rows))
  for row,csvrow in zip(rows,csvrows):
   self.assertEqual({k:'|'.join(v) if isinstance(v,list) else str(v) for k,v in row.items()},csvrow)
   obs=[c for c in cells if (c['body_style'],c['model_code'],c['marketed_trim_proposal'],c['engine_code'])==(row['body_style'],row['model_code'],row['marketed_trim_proposal'],row['engine_code'])]
   self.assertEqual(set(row['guide_source_ids']),{c['source_id'] for c in obs});self.assertEqual(set(row['excerpt_ids']),{c['excerpt_id'] for c in obs})
   self.assertEqual(row['first_observed_revision'],min(c['revision_date_printed'] for c in obs));self.assertEqual(row['last_observed_revision'],max(c['revision_date_printed'] for c in obs))
 def test_scope_and_classification_boundaries(self):
  rows=read('preliminary_factory_offerings.json');self.assertTrue(all(r['market']=='US' and r['model_year']==2021 for r in rows));self.assertEqual(sum(r['model_code']=='JLUL74' for r in rows),1)
  for r in rows:
   if r['engine_code'] in {'ECX','ESG','EXJ'}:self.assertEqual(r['body_style'],'4-door')
   if r['model_code']=='JLUL74':self.assertEqual(r['scope_status'],'requires_RHD_identity_decision')
  assessments=read('engine_classification_assessment.json');self.assertEqual({a['engine_code'] for a in assessments},{'ERC','ERG','EC1','EXJ','ECX','ESG'})
  self.assertEqual(sum(a['row_count']*len(a['unresolved_fields']) for a in assessments),89)
  extras={s['source_id']:s for s in read('supplemental_source_inventory.json')}
  for a in assessments:
   self.assertEqual(set(a['affected_rows']),{r['research_row_id'] for r in rows if r['engine_code']==a['engine_code']})
   self.assertEqual(a['approval_status'],'not_requested_or_applied')
   for field in a['unresolved_fields']:self.assertIsNone(a['directly_supported_normalized_fields'][field])
   for ref in a['source_observation_refs']:
    s=extras[ref['source_id']];self.assertEqual(ref['source_sha256'],s['document_sha256']);self.assertTrue(all(1<=p<=s['pages'] for p in ref['pages_1_based']))
 def test_secondary_coverage_has_no_manufactured_codes(self):
  comparison=read('edmunds_comparison.json');self.assertEqual(len(comparison['comparison']),74)
  rows=read('preliminary_factory_offerings.json');self.assertEqual({r['research_row_id'] for r in rows},{r['research_row_id'] for r in comparison['comparison']})
  observations=read('evidence/edmunds_observations.json');self.assertEqual(len(observations['sources']),25)
  self.assertTrue(all(not r['exact_structured_identity_confirmation'] for r in comparison['comparison']))
  self.assertEqual(observations['kind'],'research_transcription_not_original_source_bytes')
 def test_package_excerpt_lineage(self):
  guides={r['source_id']:r for r in read('source_revision_inventory.json')}
  excerpts=read('factory_package_availability_excerpts.json');self.assertEqual(len(excerpts),312)
  seen=set()
  for e in excerpts:
   source=guides[e['source_id']];self.assertEqual(e['source_sha256'],source['sha256'])
   self.assertEqual(e['text'],read_relative(source['extraction_path'])[e['pdf_page_1_based']-1])
   key=(e['source_id'],e['pdf_page_1_based']);self.assertNotIn(key,seen);seen.add(key)
 def test_read_only_database_preservation(self):
  baseline=read('baseline.json');db=ROOT/'db.sqlite3';self.assertEqual(sha(db),baseline['db_sha256'])
  c=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
  self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
  for table,count in baseline['counts'].items():self.assertEqual(c.execute('SELECT count(*) FROM '+table).fetchone()[0],count)
  self.assertEqual(c.execute('SELECT count(*) FROM reference_vehicledefinition WHERE generation_id=32 AND model_year=2021').fetchone()[0],0);c.close();self.assertEqual(sha(db),baseline['db_sha256'])
def read_relative(p):return json.loads((ROOT/p).read_text())
if __name__=='__main__':unittest.main(verbosity=2)
