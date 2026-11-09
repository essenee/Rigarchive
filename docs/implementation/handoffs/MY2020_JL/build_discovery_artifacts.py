"""Offline MY2020 research ledger builder. Never constructs candidates or writes DB.

Run from the repository root with .venv/bin/python -B. Inputs are retained PDFs
and pypdf layout-text snapshots. Exclusive outputs preserve reviewed artifacts.
"""
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()
OUT = ROOT / 'docs/implementation/handoffs/MY2020_JL'
PREFIX = 'https://www.jlwranglerforums.com/forum/attachments/'
ARCHIVES = {
    '2-door': 'https://www.jlwranglerforums.com/forum/threads/2020-jeep-wrangler-jl-order-guide-2-door.32991/',
    '4-door': 'https://www.jlwranglerforums.com/forum/threads/2020-jeep-wrangler-unlimited-order-guide-4-door.32990/',
}
LINKS = {
    '2020_JL_2_door_08_15_2019.pdf': '2020_jl_2_door_08_15_2019-pdf.215559/',
    '2 Door 9-5-19.pdf': '2-door-9-5-19-pdf.227937/',
    '2 Door 10-8-19.pdf': '2-door-10-8-19-pdf.239598/',
    '2 Door 11-4-19.pdf': '2-door-11-4-19-pdf.255143/',
    '2 Door 1-15-20.pdf': '2-door-1-15-20-pdf.272500/',
    '2 Door 1-23-20.pdf': '2-door-1-23-20-pdf.275369/',
    '2 Door 2-12-20.pdf': '2-door-2-12-20-pdf.281244/',
    '2 Door 3-3-20.pdf': '2-door-3-3-20-pdf.288455/',
    '2 Door 4-17-20.pdf': '2-door-4-17-20-pdf.312615/',
    '2020_JL_4_door_07_02_2019.pdf': '2020_jl_4_door_07_02_2019-pdf.199502/',
    '2020_JL_4_door_08_15_2019.pdf': '2020_jl_4_door_08_15_2019-pdf.215555/',
    '4 Door 9-5-19.pdf': '4-door-9-5-19-pdf.227935/',
    '4 Door 10-15-19.pdf': '4-door-10-15-19-pdf.239596/',
    '4 Door 11-13-19.pdf': '4-door-11-13-19-pdf.255141/',
    '4 Door 12-3-19.pdf': '4-door-12-3-19-pdf.261313/',
    '4 Door 1-2-20.pdf': '4-door-1-2-20-pdf.268620/',
    '4 Door 1-23-20.pdf': '4-door-1-23-20-pdf.275367/',
    '4 Door 2-11-20.pdf': '4-door-2-11-20-pdf.281242/',
    '4 Door 3-3-20.pdf': '4-door-3-3-20-pdf.288452/',
    '4 Door 4-17-20.pdf': '4-door-4-17-20-pdf.312614/',
}
ENGINE_PREFIX = {'23': ('ERC', 'DEM'), '24': ('ERC', 'DFT'), '22': ('EC1', 'DFT'),
                 '25': ('ERG', 'DFT'), '28': ('EC3', 'DFT'), '26': ('EXJ', 'DFV')}
LABELS = {
    'Sport': {'B': 'Sport', 'K': 'Willys Sport', 'S': 'Sport S', 'L': 'Sport Altitude',
              'W': 'Willys', 'D': 'Black and Tan', 'F': 'Freedom'},
    'Sahara': {'G': 'Sahara', 'L': 'Sahara Altitude', 'E': 'North Edition', 'N': 'Sahara High Altitude'},
    'Rubicon': {'R': 'Rubicon', 'Y': 'Rubicon Recon'},
}
PROPOSED = {
    'ERC': {'engine_displacement_liters': '3.6', 'engine_cylinders': 6, 'engine_aspiration': 'naturally_aspirated', 'fuel_type': 'gasoline', 'electrification_type': 'none'},
    'ERG': {'engine_displacement_liters': '3.6', 'engine_cylinders': 6, 'engine_aspiration': 'naturally_aspirated', 'fuel_type': 'gasoline', 'electrification_type': 'mild_hybrid'},
    'EC1': {'engine_displacement_liters': '2', 'engine_cylinders': 4, 'engine_aspiration': 'turbocharged', 'fuel_type': 'gasoline', 'electrification_type': 'none'},
    'EC3': {'engine_displacement_liters': '2', 'engine_cylinders': 4, 'engine_aspiration': 'turbocharged', 'fuel_type': 'gasoline', 'electrification_type': 'mild_hybrid'},
    'EXJ': {'engine_displacement_liters': '3', 'engine_cylinders': 6, 'engine_aspiration': 'turbocharged', 'fuel_type': 'diesel', 'electrification_type': 'none'},
}
PENDING = {'ERC': ['engine_aspiration', 'electrification_type'], 'ERG': ['engine_aspiration'],
           'EC1': ['electrification_type'], 'EC3': [], 'EXJ': ['electrification_type']}

def sha(path):
    return 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, data):
    with (OUT / name).open('x', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write('\n')

def table(name, rows):
    with (OUT / name).open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def iso(value):
    return datetime.strptime(value, '%m/%d/%Y').date().isoformat()

now = datetime.now(timezone.utc).isoformat()
all_cells, excerpts, sources = [], [], []
for name, fragment in LINKS.items():
    path = OUT / 'source_pdfs' / name
    extraction = OUT / 'evidence' / (name + '.text.json')
    doc = json.loads(extraction.read_text())
    assert sha(path) == doc['sha256']
    pages = doc['pages']
    cover = pages[0]
    assert 'FCA' in cover and 'United States' in cover and '2020' in cover
    dates = re.findall(r'(?:REISSUED|ISSUED):\s*(\d\d/\d\d/\d{4})', cover)
    revision = iso(dates[0])
    body = '2-door' if re.search(r'\bJLJ[LPS]72\b', cover) else '4-door'
    source_id = ('MY2020-JL-2D-' if body == '2-door' else 'MY2020-JL-4D-') + revision
    cells = []
    for number, text in enumerate(pages, 1):
        if 'POWERTRAIN AVAILABILITY' not in text:
            continue
        models = set(re.findall(r'\bJLJ[LPS]7[24]\b', text))
        assert len(models) == 1
        model = models.pop()
        assert model.endswith('72' if body == '2-door' else '74')
        family = {'L': 'Sport', 'P': 'Sahara', 'S': 'Rubicon'}[model[3]]
        raw = text.split('POWERTRAIN AVAILABILITY', 1)[1].split('PACKAGE CONTENT', 1)[0].split('E - EXTRA COST', 1)[0]
        starts = [m.start() for m in re.finditer(r'(?m)^\s*\d\.\dL\s+[VI][46]\b', raw)]
        assert starts
        excerpt_id = source_id + '-p' + str(number)
        page_cells = []
        for k, start in enumerate(starts):
            segment = raw[start:starts[k + 1] if k + 1 < len(starts) else len(raw)]
            engines = set(re.findall(r'\((E[A-Z0-9]{2})\)', segment))
            assert len(engines) == 1
            engine = engines.pop()
            for cpos in re.findall(r'\b2[234568][A-Z]\b', segment):
                if cpos == '24V':  # Valve-count descriptor, not a package cell.
                    continue
                expected, transmission = ENGINE_PREFIX[cpos[:2]]
                assert expected == engine and '(' + transmission + ')' in segment
                trim = ('Unlimited ' if body == '4-door' else '') + LABELS[family][cpos[-1]]
                cell = {'body_style': body, 'model_code': model, 'marketed_trim_proposal': trim,
                        'engine_code': engine, 'transmission_code': transmission, 'cpos': cpos,
                        'source_id': source_id, 'revision_date_printed': revision,
                        'pdf_page': number, 'excerpt_id': excerpt_id,
                        'manufacturer_engine_description': ' '.join(segment.splitlines()[0].strip().split())}
                cells.append(cell)
                page_cells.append(cell)
        assert page_cells
        excerpts.append({'excerpt_id': excerpt_id, 'source_id': source_id,
                         'document': str(path.relative_to(ROOT)), 'document_sha256': sha(path),
                         'pdf_page_1_based': number, 'model_code': model,
                         'extraction_method': 'pypdf 6.16.1 layout text; selected critical pages visually checked',
                         'powertrain_table_text': raw.strip(), 'observed_package_cells': page_cells,
                         'interpretation_notice': 'Research transcription. Trim label expansion is proposed normalization, not a manufacturer quote or executable assertion artifact.'})
    assert len({(c['model_code'], c['cpos']) for c in cells}) == len(cells)
    sources.append({'source_id': source_id, 'source_type': 'manufacturer_issued_order_guide_archived_copy',
                    'title': '2020 Jeep Wrangler ' + body + ' United States Customer Preferred Code Guide',
                    'archive_index': ARCHIVES[body], 'url': PREFIX + fragment,
                    'issue_date_printed': '2019-07-02', 'revision_date_printed': revision,
                    'body_style': body, 'market': 'US', 'model_year': 2020,
                    'document_sha256': sha(path), 'retained_path': str(path.relative_to(ROOT)),
                    'extraction_path': str(extraction.relative_to(ROOT)), 'pdf_pages': len(pages),
                    'acquired_on_utc_date': now[:10], 'acquisition': 'Public archive browser download control; copied unchanged from returned download path',
                    'authenticity_basis': 'FCA copyright/dealer-use footer, United States/MY2020 heading, internal issued/reissued dates, model-code/package tables and archive linkage. Archived copy; no digital-signature claim.',
                    'package_cells': len(cells), 'unique_offerings': len({(c['marketed_trim_proposal'], c['engine_code']) for c in cells})})
    all_cells.extend(cells)
assert len(sources) == 20 and len(excerpts) == 51
sources.sort(key=lambda s: (s['body_style'], s['revision_date_printed']))
unavailable = [
    {'source_id': 'MY2020-JL-2D-2019-07-02-UNRETAINED', 'body_style': '2-door',
     'url': PREFIX + '2020_jl_2_door_07_02_2019-pdf.199518/',
     'archive_index': ARCHIVES['2-door'], 'revision_date_printed': None,
     'date_from_link_label_only': '2019-07-02', 'document_sha256': None,
     'status': 'Linked July guide; browser download timed out and web fetch inaccessible. Internal date and content unverified.'},
    {'source_id': 'MY2020-JL-4D-2020-02-07-UNRETAINED', 'body_style': '4-door',
     'url': PREFIX + '4-door-2-7-20-pdf.280869/', 'archive_index': None,
     'revision_date_printed': '2020-02-07', 'document_sha256': None,
     'status': 'Additional web-readable guide located outside current first-post attachment list; header and selected engine tables inspected through web reader, but raw bytes not acquired. Not used to establish a unique offering.'},
]
spec = OUT / 'source_pdfs/FCA_2020_Wrangler_US_specifications.pdf'
spec_url = 'https://s3.amazonaws.com/chryslermedia.iconicweb.com/mediasite/specs/2020_JP_Wrangler_SPmrgun0frgq245rkio8imc5var6.pdf'
extra_sources = [
    {'source_id': 'FCA-US-MY2020-Wrangler-specifications', 'url': spec_url,
     'title': '2020 Jeep Wrangler Specifications (New 2020 Wrangler EcoDiesel footer)',
     'retained_path': str(spec.relative_to(ROOT)), 'document_sha256': sha(spec), 'pdf_pages': 12,
     'issue_date_printed': None, 'market_applicability': 'US technical specification: US units, EPA references and FCA North America publisher; not the separately located Canadian specification.',
     'sections': {'3.6L and gasoline': [1, 2, 12], '2.0L turbo/gasoline/eTorque': [2, 12], '3.0L diesel': [3, 12], 'four_wheel_drive': [1, 5]},
     'limitation': 'Generic availability is a publication snapshot, not a complete edition/revision union. Its 2.0 eTorque four-door-only economy/availability statement does not cover later two-door Recon; specific guide 28Y overrides that broad availability for discovery.'},
    {'source_id': 'FCA-High-Altitude-release-2020-02-06',
     'url': 'https://cas.vporoom.com/2020-02-06-Jeep-R-Brand-Expands-Wrangler-and-Gladiator-Lineup-With-Premium-High-Altitude-Model',
     'title': 'Jeep Brand Expands Wrangler and Gladiator Lineup With Premium High Altitude Model',
     'issue_date_printed': '2020-02-06', 'retained_path': str((OUT / 'evidence/FCA_High_Altitude_release_2020-02-06.html').relative_to(ROOT)),
     'document_sha256': sha(OUT / 'evidence/FCA_High_Altitude_release_2020-02-06.html'),
     'provenance': 'Manufacturer-issued FCA release syndicated by Virtual Press Office/PR Newswire; SOURCE FCA attribution retained.',
     'scope': 'Corroborates marketed High Altitude edition; exact engine/code cells remain governed by order guides.'},
    {'source_id': 'FCA-2020-fact-sheet-web-only', 'url': 'https://device.report/m/7963d8f5a504b4981496bbcb12c6abfa70e03985a3abb998ec807bd7e1c9e073.pdf',
     'title': '2020 Jeep Wrangler Fact Sheet', 'issue_date_printed': '2019-08-31', 'document_sha256': None,
     'status': 'Web-readable archived manufacturer fact sheet; direct raw retrieval returned HTTP 403. Context only; not an executable byte-bound evidence input.',
     'summary': 'Distinguishes 3.6 ESS and mild-hybrid eTorque variants, 2.0 ESS and mild-hybrid eTorque variants, and late-availability four-door diesel. Early broad model lineup omits subsequent editions. Updated corporate boilerplate limits assumptions about original document bytes.'},
]
save('source_revision_inventory.json', {'recorded_at': now, 'retained_guides': sources, 'unretained_guides': unavailable, 'supplementary_sources': extra_sources,
    'coverage_limit': 'Union of the 20 retained US MY2020 guides. Twenty-two distinct guide URLs located including two not retained. No claim that every factory revision issued is archived. First observed does not establish production/order opening date; last observed is not a certified cessation date.'})
table('source_revision_inventory.csv', [{'source_id': s['source_id'], 'body_style': s['body_style'], 'revision_date_printed': s['revision_date_printed'], 'url': s['url'], 'sha256': s['document_sha256'], 'retained_path': s['retained_path'], 'pages': s['pdf_pages'], 'unique_offerings': s['unique_offerings']} for s in sources])
save('evidence/powertrain_table_excerpts.json', {'kind': 'research evidence excerpts; not SourceAssertionSet or Candidate', 'tables': excerpts})
save('evidence_index.json', {'order_guide_sources': sources, 'supplementary_sources': extra_sources, 'table_excerpt_file': 'evidence/powertrain_table_excerpts.json',
    'table_count': len(excerpts), 'lineage_rule': 'Each cell binds source_id, full source PDF SHA-256, printed revision and 1-based PDF page. Revisions and shared family publications are not independent corroboration merely because repeated.'})
union = defaultdict(list)
for cell in all_cells:
    union[(cell['body_style'], cell['marketed_trim_proposal'], cell['engine_code'])].append(cell)
assert len(union) == 49
rows = []
for number, (key, supporting) in enumerate(sorted(union.items()), 1):
    body, trim, engine = key
    dates = sorted({c['revision_date_printed'] for c in supporting})
    rows.append({'research_row_id': f'JL20-{number:02d}', 'model_year': 2020, 'market': 'US', 'body_style': body,
                 'trim_name_proposal': trim, 'model_code': supporting[0]['model_code'], 'engine_code': engine,
                 'cpos_codes': sorted({c['cpos'] for c in supporting}), 'transmission_codes': sorted({c['transmission_code'] for c in supporting}),
                 'proposed_structured_powertrain': PROPOSED[engine], 'unapproved_classification_fields': PENDING[engine],
                 'first_observed_retained_revision': dates[0], 'last_observed_retained_revision': dates[-1],
                 'source_ids': sorted({c['source_id'] for c in supporting}), 'evidence_excerpt_ids': sorted({c['excerpt_id'] for c in supporting}),
                 'scope_status': 'Proposed discovery row; not a constructed or approved candidate',
                 'deduplication': 'Transmission/QOP alternatives collapsed; body+marketed-grade+assessed-engine tuple proposed. Engine code retained for traceability, not a new canonical identity dimension.'})
assert Counter(r['body_style'] for r in rows) == {'2-door': 15, '4-door': 34}
assert Counter(r['engine_code'] for r in rows) == {'ERC': 17, 'ERG': 3, 'EC1': 15, 'EC3': 6, 'EXJ': 8}
identities = [(r['body_style'], r['trim_name_proposal'], tuple(sorted(r['proposed_structured_powertrain'].items()))) for r in rows]
assert len(set(identities)) == len(rows)
save('preliminary_factory_offerings.json', {'created': now, 'status': 'Proposed', 'research_only': True, 'candidate_construction_performed': False,
    'unique_configurations': 49, 'body_trim_variants': 21, 'rows': rows})
table('preliminary_factory_offerings.csv', [{'row_id': r['research_row_id'], 'body_style': r['body_style'], 'trim_name_proposal': r['trim_name_proposal'],
    'model_code': r['model_code'], 'engine_code': r['engine_code'], 'cpos_codes': '|'.join(r['cpos_codes']), 'transmission_codes': '|'.join(r['transmission_codes']),
    'first_observed': r['first_observed_retained_revision'], 'last_observed': r['last_observed_retained_revision'],
    'unapproved_fields': '|'.join(r['unapproved_classification_fields']), 'source_ids': '|'.join(r['source_ids']), 'excerpt_ids': '|'.join(r['evidence_excerpt_ids'])} for r in rows])
comparisons = []
for body in ['2-door', '4-door']:
    previous = None
    for s in [s for s in sources if s['body_style'] == body]:
        current = {(c['marketed_trim_proposal'], c['engine_code']) for c in all_cells if c['source_id'] == s['source_id']}
        cp = {(c['model_code'], c['cpos']) for c in all_cells if c['source_id'] == s['source_id']}
        comparisons.append({'body_style': body, 'source_id': s['source_id'], 'revision': s['revision_date_printed'], 'offering_count': len(current),
            'added_since_previous_retained': sorted(current - previous[0]) if previous else sorted(current),
            'omitted_since_previous_retained': sorted(previous[0] - current) if previous else [],
            'package_cells_added': sorted(cp - previous[1]) if previous else sorted(cp),
            'package_cells_omitted': sorted(previous[1] - cp) if previous else [],
            'date_meaning': 'Observed in printed revision only; not production start/end certification.'})
        previous = current, cp
save('revision_comparison.json', comparisons)
assessments = []
for engine, proposed in PROPOSED.items():
    direct = {k: v for k, v in proposed.items() if k not in PENDING[engine]}
    assessments.append({'engine_code': engine, 'proposed_tuple_for_human_review': proposed, 'manufacturer_supported_values_with_code_family_join': direct,
        'unapproved_fields': PENDING[engine], 'covered_research_rows': [r['research_row_id'] for r in rows if r['engine_code'] == engine],
        'confidence_in_proposed_unapproved_fields': ('Unresolved working proposal; additional positive hardware/classification evidence required before approval.' if engine == 'EXJ' else 'moderate; human decision required' if PENDING[engine] else None),
        'support': ['Exact engine descriptor/code and availability cells in retained US order guides', 'FCA US MY2020 specifications engine and fuel sections; source IDs and page list in evidence_index.json'],
        'reasoning_for_derived_classifications': ('Naturally aspirated is a proposed Pentastar-family induction conclusion, not explicit US MY2020 specifications wording. ' if engine in ('ERC', 'ERG') else '') + ('Nonhybrid is a proposed bounded architectural classification based on the differentiated MY2020 powertrain offering/specification descriptions; ESS wording or absence of eTorque alone is insufficient. Obtain specific hardware corroboration or exact human adjudication before filling this field.' if engine in ('ERC', 'EC1', 'EXJ') else ''),
        'limitations': ['MY2019 human approvals do not authorize MY2020 facts.', 'Marketed liters are preserved (3.6, 2.0, 3.0); do not substitute swept-volume cc conversions.', 'Technical family descriptions must be joined to the exact model-year/code offering; not global engine-code propagation.', 'Generic eTorque body/trim availability in early specifications omits later Recon; use its specific guide evidence.'],
        'additional_engine_code': False})
save('engine_classification_assessment.json', {'status': 'Proposed research assessment; no human classifications approved', 'engine_codes': assessments,
    'additional_engine_codes_found': [], 'non_engine_code_exclusion': 'ERS occurs in the technical specification as Electronic Range Select transmission control, not an engine code.'})
# Database reconciliation is read-only and cannot affect the live database.
db = ROOT / 'db.sqlite3';db_before = sha(db);assert db_before == 'sha256:f0d32327e0d688b56711a572375e4e462a266ebb8fdb250b97965e392dff07ab'
con = sqlite3.connect(db.as_uri() + '?mode=ro', uri=True);con.execute('PRAGMA query_only=ON')
assert con.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
assert not con.execute('PRAGMA foreign_key_check').fetchall()
assert con.execute('SELECT COUNT(*) FROM reference_vehicledefinition').fetchone()[0] == 812
assert con.execute('SELECT COUNT(*) FROM reference_importexecutionreceipt').fetchone()[0] == 2880
existing = con.execute('SELECT id,uuid,slug,trim_name,engine_name,drivetrain,market FROM reference_vehicledefinition WHERE generation_id=32 AND model_year=2020').fetchall();assert not existing
correspondences = con.execute('SELECT id,start_year,end_year,native_identifier FROM reference_generationcorrespondencerevision WHERE generation_id=32 ORDER BY id').fetchall()
assert not [r for r in correspondences if r[1] <= 2020 <= r[2]]
con.close()
old = json.loads((ROOT / 'docs/implementation/handoffs/MY2019_JL/director_review/erc_approved_classifications_20261108/complete_19_candidate_index.json').read_text())['rows']
old_identities = {(r['trim'], tuple(sorted(r['canonical_powertrain'].items()))) for r in old}
new_identities = {(r['trim_name_proposal'], tuple(sorted(r['proposed_structured_powertrain'].items()))) for r in rows}
save('canonical_and_MY2019_reconciliation.json', {'database_access': 'SQLite URI mode=ro plus PRAGMA query_only=ON', 'definitions_total': 812, 'receipts_total': 2880,
    'MY2020_JL_existing_records': existing, 'MY2020_JL_existing_correspondences': [], 'published_JL_correspondence_scopes': correspondences,
    'generation': {'pk': 32, 'uuid': '38d3c3ac-f825-4406-abb5-c2d12b9129a4'}, 'MY2019_candidate_count': len(old),
    'same_trim_and_proposed_tuple_across_years': len(old_identities & new_identities),
    'MY2019_trim_tuple_pairs_not_repeated': sorted(old_identities - new_identities, key=repr),
    'interpretation': 'Cross-year comparison is research continuity only, never a same-year duplicate or permission to propagate approvals. Existing MY2019 source mappings are year-bounded and cannot resolve MY2020. No canonical planning or eligibility assessment performed.',
    'database_sha256_before': db_before, 'database_sha256_after': sha(db)})
assert sha(db) == db_before
save('discovery_validation.json', {'research_rows': 49, 'body_counts': dict(Counter(r['body_style'] for r in rows)), 'engine_counts': dict(Counter(r['engine_code'] for r in rows)),
    'body_trim_variants': len({(r['body_style'], r['trim_name_proposal']) for r in rows}), 'retained_order_guides': 20, 'unretained_located_guides': 2,
    'powertrain_table_excerpts': len(excerpts), 'observed_cpos_cells_across_revisions': len(all_cells),
    'unique_model_cpos_pairs': len({(c['model_code'], c['cpos']) for c in all_cells}),
    'all_guide_byte_hashes_verified': True, 'unique_proposed_body_trim_tuple_identities': True, 'every_row_has_exact_positive_availability_cells': True,
    'no_transmission_only_duplicates': True, 'model_codes': sorted({c['model_code'] for c in all_cells}),
    'rows_with_unapproved_classification_fields': sum(bool(r['unapproved_classification_fields']) for r in rows),
    'classifications_approved_in_this_task': 0, 'candidates_constructed': 0, 'canonical_imports_or_plans': 0,
    'development_database_unchanged': True, 'database_sha256': db_before,
    'scope_note': 'Discovery assertions and source rehashing only. No executable candidate contract certification or full test suite claimed.'})
print(json.dumps({'configurations': len(rows), 'body_counts': dict(Counter(r['body_style'] for r in rows)), 'engine_counts': dict(Counter(r['engine_code'] for r in rows)), 'cells': len(all_cells), 'table_excerpts': len(excerpts), 'database_unchanged': True}))
