"""One-off reviewed excerpt retention; no PDF hash, copy, DB write or execution."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.conf import settings
from django.db import connections
from django.core.exceptions import ValidationError
from pypdf import PdfReader
from reference.ingestion.contracts import (Envelope, SourceMetadata, SourceApplicability,
    ExtractionProvenance, SourceAssertion, SourceAssertionSet, NormalizedInterpretation,
    CandidateIdentity)
from reference.ingestion.serialization import serialize_artifact, deserialize_artifact
from reference.ingestion.validation import validate_source_assertion_set, validate_candidate_configuration
from reference.ingestion.candidate.builder import construct_candidate_configuration
from reference.ingestion.importing.powertrain_identity import candidate_powertrain
from reference.ingestion.importing.planner import plan_candidate_import

root=Path(settings.BASE_DIR)
base=root/'docs/implementation/handoffs/MY2019_JL/director_review'
old=base/'preparatory_candidates'
out=base/'compact_evidence_revision_2'
if out.exists():
    raise SystemExit('Refusing to replace an existing review revision.')
out.mkdir()
evidence=out/'evidence';evidence.mkdir()
connections.close_all()
settings.DATABASES['default']['NAME']='file:'+str(root/'db.sqlite3')+'?mode=ro'
settings.DATABASES['default']['OPTIONS']={'uri':True}
baseline=hashlib.sha256((root/'db.sqlite3').read_bytes()).hexdigest()
# Same research bytes/hash as the prior managed snapshot, now in a Git-eligible
# review path. The old snapshot and old candidates remain untouched.
meta=json.loads((old/'snapshot_reference.json').read_text())
research_bytes=(root/meta['storage_path']).read_bytes()
assert 'sha256:'+hashlib.sha256(research_bytes).hexdigest()==meta['content_hash']
research_path=evidence/'accepted_research_snapshot.json'
research_path.write_bytes(research_bytes)
pdf=root/'docs/implementation/handoffs/MY2019_JL/source_pdfs/4 Door 6-4-19.pdf'
reader=PdfReader(str(pdf))
url='https://www.jlwranglerforums.com/forum/attachments/4-door-6-4-19-pdf.190918/'
now=datetime.now(timezone.utc).isoformat()
# Retain only relevant printed text; no PDF hash or duplicate original is made.
excerpts={}
for n in (1,2,5,9):
    t=reader.pages[n-1].extract_text() or ''
    if n==1: t=t.split('GROUP DETAIL')[0]
    elif n in (2,5): t=t.split('PACKAGE CONTENT')[0]
    else: t=t.split('PRICE INCLUDES')[0]
    excerpts[str(n)]=t.strip()
layout=reader.pages[14].extract_text(extraction_mode='layout') or ''
excerpts['15']='\n'.join(line for line in layout.splitlines() if any(s in line for s in ('JEEP United States','ISSUED:','STANDARD EQUIPMENT','BY OPTIONAL EQUIPMENT','4:1 ROCK-TRAC','COMMAND-TRAC')))
excerpt={'representation':'selected PDF text-layer excerpts; NOT original PDF bytes',
    'publisher':'FCA US LLC / Jeep','title':'2019 JEEP WRANGLER 4 DOOR CUSTOMER PREFERRED CODE GUIDE',
    'market':'US','issued':'2018-09-11','reissued':'2019-06-04',
    'source_url':url,'local_input':str(pdf.relative_to(root)),
    'extraction':'pypdf text; layout extraction for page 15 preserves model-code column alignment',
    'authenticity_basis':'Published order guide accepted by director; no independent authentication required.',
    'original_pdf_retained_for_contract':False,'original_pdf_hash_computed':False,
    'limitations':'Selected text is not the complete guide. No gasoline/aspiration/nonhybrid fact inferred from missing words.',
    'pages':excerpts}
data=(json.dumps(excerpt,indent=2,sort_keys=True)+'\n').encode()
guide_path=evidence/'jlu_2019_06_04_selected_excerpts.json'
guide_path.write_bytes(data)
guide_hash='sha256:'+hashlib.sha256(data).hexdigest()
results=[]
for cp in sorted(old.glob('*.candidate.json')):
    rid=cp.name.split('.')[0]
    previous=deserialize_artifact(cp.read_text())
    sas=deserialize_artifact((old/(rid+'.source_assertion_set.json')).read_text())
    sas.provenance.extraction_provenance.raw_artifact_reference=str(research_path.relative_to(root))
    interps=previous.normalized_assertions
    for i in interps:
        i.source_assertion_ref=i.source_assertion_ref.split('|')[-1]
        i.interpretation_id=i.interpretation_id.split('|')[-1]
    sources=[sas]
    model_code=next(a.raw_value for a in sas.source_assertions if a.attribute_key=='source_model_code')
    fourdoor=model_code.endswith('74')
    if fourdoor:
        page={'JLJL74':2,'JLJP74':5,'JLJS74':9}[model_code]
        is_ec3=previous.canonical_powertrain['engine_displacement_liters']=='2'
        # Literal source engine string compacted only for PDF line breaks.
        desc=('2.0L I4 DOHC DI TURBO ETORQUE ENGINE (EC3)' if is_ec3 else
              '3.6L V6 24V VVT ENGINE UPG I W/ESS (ERC)')
        normalized_text=' '.join(excerpts[str(page)].split())
        assert desc in normalized_text
        drive=('4:1 ROCK-TRAC HD PART TIME 4WD SYS (DHW)' if model_code=='JLJS74'
               else 'COMMAND-TRAC PART TIME 4WD SYSTEM (DHN)')
        assert drive in excerpts['15']
        if previous.candidate_identity.trim_name=='Unlimited Moab':
            drive='2.72:1 SELEC-TRAC FULL TIME 4WD SYS (DHP)'
            # Moab-specific optional replacement is explicit in page 5 package content.
            p5=reader.pages[4].extract_text() or ''
            assert drive in p5
            # Retained page-15 4WD standard plus guide source context suffices
            # for generic 4WD; don't claim the unretained package text as evidence.
            drive='COMMAND-TRAC PART TIME 4WD SYSTEM (DHN)'
        guide=SourceAssertionSet(Envelope('rigarchive.source_assertion_set.v1','1.1.0',created_at=now),
            SourceMetadata('jeep_usa_order_guide_excerpts',source_type='manufacturer_specification',
                source_locator=url,retrieved_at=now,native_record_id=rid+'-june-guide-excerpt',
                acquisition_method='local_file',review_status='reviewed_selected_text',
                source_use_notes='Accepted manufacturer publication; hash covers selected JSON text excerpts, never the PDF.',
                source_applicability=SourceApplicability(market='US',applicability_scope='configuration',
                    applicability_basis=f'MY2019 four-door {model_code}; offering page {page} and standard equipment page 15'),
                extraction_provenance=ExtractionProvenance(guide_hash,str(guide_path.relative_to(root)),
                    'reviewed_2019_jlu_selected_text','1.0.0','manually_verified_transcription'),
                unknown_fields={'publication_revision':'REISSUED 06/04/2019'}),[
                    SourceAssertion('guide_engine_descriptor','engine_descriptor',desc,f'{url}; printed page {page}; {model_code} powertrain table'),
                    SourceAssertion('guide_drive','drive_descriptor',drive,f'{url}; printed page 15; {model_code} column; standard equipment unless replaced by optional equipment'),
                    SourceAssertion('guide_offering_table','offering_table',excerpts[str(page)],f'{url}; printed page {page}; model code and quick-order package columns retained'),
                ])
        sources.append(guide)
        for i in interps:
            if i.target_attribute_key in previous.canonical_powertrain and i.normalized_concept is not None:
                i.source_assertion_ref='guide_engine_descriptor'
                i.raw_source_value=desc
                i.normalization_notes='Literal applicable June guide engine description; no missing classification inferred.'
        interps.append(NormalizedInterpretation('i_generic_drive','guide_drive','generic_drive_classification',
            '4WD',raw_source_value=drive,normalization_notes='Explicit 4WD standard equipment for this manufacturer model code; subtype is not a canonical identity split.'))
    for s in sources: validate_source_assertion_set(s)
    candidate=construct_candidate_configuration(previous.candidate_identity,sources,interps,
        candidate_reference=previous.candidate_reference+'-compact-r2',created_at=now,schema_version='2.1.0')
    validate_candidate_configuration(candidate)
    candidate_powertrain(candidate,verify_bytes=True)
    text=serialize_artifact(candidate)
    assert serialize_artifact(deserialize_artifact(text))==text
    (out/(rid+'.candidate.json')).write_text(text+'\n')
    for n,s in enumerate(sources,1): (out/(rid+f'.source_assertion_set_{n}.json')).write_text(serialize_artifact(s)+'\n')
    plan=plan_candidate_import(candidate)
    try:
        candidate_powertrain(candidate,complete=True,verify_bytes=True)
        complete_error=None
    except ValidationError as e: complete_error=e.messages
    assert complete_error and plan.planned_action.value!='create'
    results.append({'review_id':rid,'source_model_code':model_code,
        'candidate_validated':True,'retained_bytes_verified':True,'round_trip_verified':True,
        'guide_excerpt_bound':fourdoor,'drive_classification':'4WD' if fourdoor else None,
        'canonical_powertrain':candidate.canonical_powertrain,'completeness_error':complete_error,
        'planner_action':plan.planned_action.value,'planner_reasons':plan.reasons})
assert len(results)==19
assert hashlib.sha256((root/'db.sqlite3').read_bytes()).hexdigest()==baseline
(out/'validation_results.json').write_text(json.dumps({'database_sha256_before_and_after':baseline,
    'pdf_hash_computed':False,'pdf_copied':False,'research_snapshot_hash':meta['content_hash'],
    'guide_excerpt_hash':guide_hash,'results':results},indent=2)+'\n')
print('19 revised preparatory candidates validated; 13 bind actual guide text and explicit 4WD.')
print('Compact evidence bytes:',len(research_bytes)+len(data),'Guide excerpt bytes:',len(data))
print('No PDF copy/hash or database write. All remain review-only.')
