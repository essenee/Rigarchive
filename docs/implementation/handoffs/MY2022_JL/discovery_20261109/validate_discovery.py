"""Offline integrity/lineage checks only. No Candidate, Matrix or import construction."""
import hashlib,json,re,sqlite3,unittest
from collections import Counter
from pathlib import Path
from pypdf import PdfReader
O=Path(__file__).resolve().parent;ROOT=O.parents[4]
def read(n):return json.loads((O/n).read_text())
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
class DiscoveryChecks(unittest.TestCase):
 def test_retained_sources_and_extraction(self):
  inv=read('manufacturer_source_inventory.json');self.assertEqual(len(inv),20)
  manifest=read('raw_source_retention_manifest.json');self.assertEqual(len(manifest),21)
  for r in manifest:
   self.assertEqual(sha(ROOT/r['retained_path']),r['sha256']);self.assertTrue(r['acquired_at']);self.assertTrue(r['acquisition_timestamp_basis'])
  self.assertEqual(Counter(s['body_style'] for s in inv if s['kind']=='ordering_guide'),{'2-door':9,'4-door':9})
  for s in inv:
   with self.subTest(source=s['source_id']):
    p=ROOT/s['retained_path'];self.assertEqual(sha(p),s['sha256']);self.assertEqual(p.stat().st_size,s['bytes'])
    pages=json.loads((ROOT/s['extraction_path']).read_text());self.assertEqual(sha(ROOT/s['extraction_path']),s['extraction_sha256'])
    self.assertEqual(pages,[p.extract_text(extraction_mode='layout') or '' for p in PdfReader(p).pages]);self.assertIn('2022',pages[0])
  for s in read('supplemental_source_inventory.json'):
   self.assertEqual(sha(ROOT/s['retained_path']),s['sha256']);self.assertEqual(sha(ROOT/s['extraction_path']),s['extraction_sha256'])
 def test_independent_plain_text_availability(self):
  cells=read('positive_package_observations.json')
  for s in read('manufacturer_source_inventory.json'):
   if s['kind']!='ordering_guide':continue
   found=[]
   for pg in PdfReader(ROOT/s['retained_path']).pages:
    t=pg.extract_text() or ''
    if 'POWERTRAIN AVAILABILITY' not in t:continue
    raw=re.split('PACKAGE CONTENT|PRICE INCLUDES|STEP #3|E - EXTRA COST',t.split('POWERTRAIN AVAILABILITY',1)[1])[0]
    found.extend(q for q in re.findall(r'\b2[23456789][A-Z]\b',raw) if q!='24V')
   self.assertEqual(Counter(found),Counter(c['quick_order_package'] for c in cells if c['source_id']==s['source_id']),s['source_id'])
 def test_exact_lineage_and_union(self):
  cells=read('positive_package_observations.json');rows=read('provisional_configuration_inventory.json')
  sources={s['source_id']:s for s in read('manufacturer_source_inventory.json')};excerpts={e['excerpt_id']:e for e in read('evidence_index.json')}
  self.assertEqual(len(cells),543);self.assertEqual(len(excerpts),81)
  seen=set()
  for c in cells:
   key=(c['source_id'],c['model_code'],c['quick_order_package']);self.assertNotIn(key,seen);seen.add(key)
   self.assertEqual(c['source_sha256'],sources[c['source_id']]['sha256']);self.assertEqual(c['model_code'],excerpts[c['excerpt_id']]['model_code'])
   self.assertIn(c['quick_order_package'],excerpts[c['excerpt_id']]['text']);self.assertIn('('+c['engine_code']+')',c['manufacturer_engine_segment']);self.assertIn('('+c['transmission_code']+')',c['manufacturer_engine_segment'])
  fields=['body_style','model_code','marketed_column_label','engine_code']
  self.assertEqual({tuple(c[k] for k in fields) for c in cells},{tuple(r[k] for k in fields) for r in rows});self.assertEqual(len(rows),56)
  for r in rows:
   obs=[c for c in cells if all(c[k]==r[k] for k in fields)]
   self.assertEqual(r['transmission_codes'],sorted({c['transmission_code'] for c in obs}));self.assertEqual(len(r['evidence']),len(obs))
   self.assertEqual(r['first_observed_revision'],min(c['revision_date'] for c in obs));self.assertEqual(r['last_observed_revision'],max(c['revision_date'] for c in obs))
 def test_review_and_scope_boundaries(self):
  rows=read('provisional_configuration_inventory.json');self.assertEqual(sum(r['scope_status']=='owner_RHD_scope_decision' for r in rows),1)
  for r in rows:
   if r['engine_code'] in ['EXJ','ECX','ESG']:self.assertEqual(r['body_style'],'4-door')
   if r['marketed_column_label']=='High Tide':self.assertEqual((r['engine_code'],r['transmission_codes']),('ERG',['DFT']))
  for a in read('powertrain_evidence_matrix.json'):
   self.assertEqual(a['approval_status'],'not_requested_or_applied')
   for f in a['unresolved_fields']:self.assertIsNone(a['research_values'][f])
 def test_comparison_and_package_pages(self):
  comp=read('MY2021_to_MY2022_comparison.json');self.assertEqual(Counter(x['status'] for x in comp),{'continuing_observed':55,'MY2021_only_not_observed_MY2022':19,'newly_observed_MY2022':1})
  src={s['source_id']:s for s in read('manufacturer_source_inventory.json')}
  for e in read('factory_package_availability_excerpts.json'):
   self.assertEqual(e['source_sha256'],src[e['source_id']]['sha256']);self.assertEqual(e['text'],json.loads((ROOT/src[e['source_id']]['extraction_path']).read_text())[e['pdf_page_1_based']-1])
 def test_preservation(self):
  for p,h in read('preservation_baseline.json').items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h)
  c=sqlite3.connect('file:'+str(ROOT/'db.sqlite3')+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
  self.assertEqual(c.execute('select count(*) from reference_vehicledefinition').fetchone()[0],934);self.assertEqual(c.execute('select count(*) from reference_importexecutionreceipt').fetchone()[0],3148)
  self.assertEqual(c.execute('select count(*) from reference_vehicledefinition where generation_id=32 and model_year=2022').fetchone()[0],0)
  self.assertEqual(c.execute('select uuid from reference_generation where id=32').fetchone()[0].replace('-',''),'38d3c3acf8254406abb5c2d12b9129a4');c.close()
if __name__=='__main__':unittest.main(verbosity=2)
