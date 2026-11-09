"""Offline review/preservation tests; no ingestion or database write operations."""
import unittest,json,hashlib,sqlite3,re
from pathlib import Path
from collections import Counter
from pypdf import PdfReader
R=Path(__file__).resolve().parent;O=R.parent;ROOT=O.parents[3]
def read(p):return json.loads(p.read_text())
def sha(p):return 'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()
def objsha(x):return 'sha256:'+hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
class ReviewChecks(unittest.TestCase):
 def test_all_original_artifacts_preserved(self):
  b=read(R/'baseline.json');self.assertEqual(len(b['original_artifact_hashes']),91)
  for p,d in b['original_artifact_hashes'].items():self.assertEqual(sha(O/p),d,p)
 def test_trim_review_covers_exact_scope(self):
  rows=read(O/'preliminary_factory_offerings.json');trims=read(R/'trim_edition_review.json')
  self.assertEqual(len(trims),25);self.assertEqual(sum(t['separate_canonical_trim_recommended'] for t in trims),24)
  self.assertEqual({t['normalized_display_name_proposal'] for t in trims},{r['marketed_trim_proposal'] for r in rows})
  for t in trims:
   rs=[r for r in rows if r['marketed_trim_proposal']==t['normalized_display_name_proposal']]
   self.assertEqual(t['research_row_ids'],[r['research_row_id'] for r in rs]);self.assertEqual(t['model_code'],rs[0]['model_code']);self.assertEqual(t['owner_approval_status'],'pending')
   self.assertEqual(set(t['powertrain_excerpt_ids']),{e for r in rs for e in r['excerpt_ids']})
 def test_all_89_classification_decisions_exactly_reviewed(self):
  original=read(O/'engine_classification_assessment.json');rows={r['research_row_id']:r for r in read(O/'preliminary_factory_offerings.json')};d=read(R/'classification_review_89_decisions.json');g=read(R/'classification_groups.json')
  expected={(rid,f,a['proposed_values_for_review'][f]) for a in original for f in a['unresolved_fields'] for rid in a['affected_rows']}
  self.assertEqual(len(d),89);self.assertEqual(len(g),7);self.assertEqual({(x['research_row_id'],x['field'],x['proposed_value']) for x in d},expected)
  self.assertEqual(len({x['research_row_id'] for x in d}),71)
  for x in d:
   self.assertEqual(x['research_row_sha256'],objsha(rows[x['research_row_id']]));self.assertIsNone(x['directly_supported_value']);self.assertIsNone(x['candidate_artifact']);self.assertEqual(x['approval_status'],'pending');self.assertEqual(x['confidence'],'moderate')
  self.assertEqual(Counter(x['recommended_disposition'] for x in d),{'request_owner_approval_before_later_application':88,'defer_with_RHD_representation':1})
 def test_partition_and_no_discovery_row_changes(self):
  orig={r['research_row_id']:r for r in read(O/'preliminary_factory_offerings.json')};consumer=read(R/'proposed_consumer_scope.json');rhd=read(R/'preserved_RHD_scope.json')
  self.assertEqual(len(consumer['rows']),73);self.assertEqual(Counter(r['body_style'] for r in consumer['rows']),{'2-door':23,'4-door':50})
  self.assertEqual({r['research_row_id'] for r in consumer['rows']}|{rhd['row']['research_row_id']},set(orig));self.assertEqual(rhd['row'],orig['JL21-71']);self.assertFalse(rhd['construction_authorized'])
  for x in consumer['rows']:
   original=orig[x['research_row_id']];self.assertEqual({k:x[k] for k in original},original);self.assertEqual(x['research_row_sha256'],objsha(original))
 def test_earlier_only_and_transmission_reconciliation(self):
  guides=read(O/'source_revision_inventory.json');cells=read(O/'positive_package_observations.json');c=read(R/'completeness_reconciliation.json');self.assertEqual(len(guides),27);self.assertEqual(len(cells),900);self.assertEqual(len(read(O/'evidence_index.json')),106);self.assertEqual(len(read(O/'factory_package_availability_excerpts.json')),312)
  last={s['source_id'] for s in guides if s['revision_date_printed']=='2021-08-06'};keys={(x['model_code'],x['marketed_trim_proposal'],x['engine_code']) for x in cells if x['source_id'] in last};rows=read(O/'preliminary_factory_offerings.json')
  earlier=[r for r in rows if (r['model_code'],r['marketed_trim_proposal'],r['engine_code']) not in keys];self.assertEqual(c['earlier_only_rows'],earlier);self.assertEqual(len(earlier),24);self.assertEqual(len(keys),50)
  self.assertEqual({r['research_row_id'] for r in c['merged_transmission_alternatives']},{r['research_row_id'] for r in rows if len(r['engine_transmission_pairings'])>1});self.assertEqual(c['remaining_package_only_rows_to_remove'],[])
 def test_new_source_bytes_and_manual_locators(self):
  for s in read(R/'additional_source_index.json'):
   self.assertEqual(sha(ROOT/s['path']),s['sha256']);self.assertEqual(sha(ROOT/s['extraction_path']),s['extraction_sha256'])
  manual=R/'sources/Jeep_MY2021_Wrangler_US_owners_manual_E5.pdf';r=PdfReader(manual);self.assertEqual(len(r.pages),380)
  for n in [143,145]:
   t=re.sub(r'\s+','',r.pages[n-1].extract_text()).lower();self.assertIn('heavydutystarter',t);self.assertIn('hybridelectricbattery',t);self.assertIn('etorque',t)
  self.assertIn('Fourth Edition V1',r.pages[0].extract_text());self.assertIn('2021 WRANGLER',r.pages[0].extract_text())
 def test_all_five_field_assessments_and_PHEV_distinction(self):
  engines=read(R/'engine_evidence_assessment.json');self.assertEqual(len(engines),6);ecx=next(a for a in engines if a['engine_code']=='ECX');self.assertEqual(ecx['directly_supported_normalized_fields'],{'engine_displacement_liters':'2','engine_cylinders':4,'engine_aspiration':'turbocharged','fuel_type':'gasoline','electrification_type':'plug_in_hybrid'});self.assertEqual(ecx['unresolved_fields'],[])
  esg=next(a for a in engines if a['engine_code']=='ESG');self.assertEqual(esg['directly_supported_normalized_fields']['engine_displacement_liters'],'6.4');self.assertEqual(esg['directly_supported_normalized_fields']['engine_cylinders'],8);self.assertEqual(set(esg['unresolved_fields']),{'engine_aspiration','electrification_type'})
 def test_database_and_counts_preserved(self):
  b=read(R/'baseline.json');db=ROOT/'db.sqlite3';self.assertEqual(sha(db),b['database_sha256']);c=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True);c.execute('PRAGMA query_only=ON')
  self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok');self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(),[])
  for t,n in b['counts'].items():self.assertEqual(c.execute('SELECT count(*) FROM '+t).fetchone()[0],n)
  c.close();self.assertEqual(sha(db),b['database_sha256'])
if __name__=='__main__':unittest.main(verbosity=2)
