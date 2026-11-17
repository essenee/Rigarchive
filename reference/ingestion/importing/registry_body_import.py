"""Bounded 3.1.0 Engine envelope over RA-049 body planning and atomic execution.

Nested 3.0.0 body projections are validation/reuse components, not independently
executable registry plans. Candidate v3 wire bytes and legacy reader meaning stay fixed.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib

from django.core.exceptions import ValidationError
from django.db import OperationalError

from reference import candidate_v3 as wire
from reference.engine_registry import resolve_engine, validate_engine_properties, EngineRegistryError
from reference.models import Engine, Manufacturer, VehicleDefinition, normalize_engine_code
from reference.powertrain import FIELDS, record_powertrain, TAXONOMIES
from reference.ingestion import body_import_contracts as c
from reference.ingestion.matrix_approval import validate_matrix_approval
from . import body_import as legacy
from .body_identity import Release, ResolutionError, need, read_retained, stamp, plan_resolved

VERSION = '3.1.0'
LOCAL = {
    'Binding': {'manufacturer': 'Parent', 'engine': 'Parent', 'engine_code': 'Text', 'name': 'StoredText',
                'properties': 'Powertrain', 'updated_at': 'Timestamp', 'state_hash': 'Hash'},
    'Candidate': {'registry_candidate_version': c.constant(VERSION), 'candidate': 'Candidate',
                  'binding': 'Binding', 'code_reference': 'Text', 'source_candidate': c.nullable('ArtifactPin'), 'artifact_hash': 'Hash'},
}
# Avoid recursive Candidate ambiguity: native wire document is handled by c directly.
LOCAL['Candidate']['candidate'] = 'WireCandidate'
BINDINGS = c.array('BindingRow', lambda x: x['candidate_reference'], 31)
LOCAL.update({
    'BindingRow': {'candidate_reference': 'Text', 'binding': 'Binding', 'code_reference': 'Text', 'artifact_hash': 'Hash'},
    'Plan': {'plan_version': c.constant(VERSION), 'body_plan': 'Plan3', 'engine_bindings': BINDINGS,
             'peer_engines': c.array({'vehicle_uuid': 'UUID', 'engine_uuid': c.nullable('UUID')}, lambda x:x['vehicle_uuid']), 'plan_hash': 'Hash'},
    'Matrix': {'matrix_version': c.constant(VERSION), 'body_matrix': 'Matrix3',
               'registry_rows': c.array({'candidate_reference':'Text','plan_hash':'Hash','engine_state_hash':'Hash','engine_uuid':'UUID'}, lambda x:x['candidate_reference'], 1)},
    'Manifest': {'manifest_version': c.constant(VERSION), 'matrix':'Matrix', 'matrix_digest':'Hash', 'approval':'Approval1', 'approval_hash':'Hash', 'manifest_hash':'Hash'},
    'Revalidation': {'revalidation_version': c.constant(VERSION), 'manifest_hash':'Hash',
                     'plan_hashes': c.array({'candidate_reference':'Text','plan_hash':'Hash'},lambda x:x['candidate_reference'],1),
                     'result':c.enum('valid','stale'), 'diagnostics':c.DIAGNOSTICS, 'revalidation_hash':'Hash'},
    'Receipt': {'receipt_version': c.constant(VERSION), 'manifest':'Manifest', 'plan':'Plan', 'revalidation':'Revalidation',
                'outcome':c.enum('created','no_op'), 'vehicle':{'pk':'Int','uuid':'UUID','slug':'Text'},
                'persisted_fields':'TargetFields','engine_uuid':c.nullable('UUID'), 'execution_agent':'Text','executed_at_utc':'Timestamp','snapshot_hash':'Hash'},
})
HASHES = {'Binding':'state_hash','Candidate':'artifact_hash','Plan':'plan_hash','Manifest':'manifest_hash','Revalidation':'revalidation_hash','Receipt':'snapshot_hash'}


def _expand(schema):
    if schema == 'WireCandidate': return 'Candidate'
    if isinstance(schema,str) and schema in LOCAL: return _expand(LOCAL[schema])
    if isinstance(schema,dict): return {k:_expand(v) for k,v in schema.items()}
    if isinstance(schema,tuple) and schema[0] in ('nullable','array'): return (schema[0],_expand(schema[1]),*schema[2:])
    return schema


def _hash(kind, value):
    return c.digest({'registry_import_contract': VERSION+'/'+kind, 'payload':{k:v for k,v in value.items() if k!=HASHES[kind]}})


def seal(kind, value):
    value=deepcopy(value);value[HASHES[kind]]=_hash(kind,value)
    return validate(kind,value)


def _nested(schema, value):
    if isinstance(schema,str) and schema in LOCAL:
        _semantic(schema,value);_nested(LOCAL[schema],value)
    elif isinstance(schema,dict):
        for k,s in schema.items(): _nested(s,value[k])
    elif isinstance(schema,tuple) and schema[0]=='array':
        for item in value:_nested(schema[1],item)
    elif isinstance(schema,tuple) and schema[0]=='nullable' and value is not None:_nested(schema[1],value)


def subject(plan):
    return next(r for r in plan['engine_bindings'] if r['candidate_reference']==plan['body_plan']['candidate_reference'])


def _semantic(kind,v):
    if kind in HASHES:c.require(v[HASHES[kind]]==_hash(kind,v),'Registry '+kind+' hash mismatch.')
    if kind=='Binding':c.require(v['engine_code']==normalize_engine_code(v['engine_code']),'Noncanonical complete engine code.')
    elif kind=='Candidate':
        c.require(v['candidate']['canonical_powertrain']==v['binding']['properties'],'Registry candidate properties differ.')
        code_from_candidate(v['candidate'],v['code_reference'],v['binding']['engine_code'])
    elif kind=='Plan':
        body=v['body_plan'];members=body['proof']['family']['release_members'];rows=v['engine_bindings']
        c.require(len(rows)==31 and [r['candidate_reference'] for r in rows]==[m['candidate_reference'] for m in members],'Registry family incomplete.')
        for r,m in zip(rows,members):
            c.require(r['binding']['manufacturer']==body['generation']['scope']['manufacturer'] and r['binding']['properties']==m['target_fields']['canonical_powertrain'],'Registry family scope/property mismatch.')
        code_from_candidate(body['candidate_snapshot'],subject(v)['code_reference'],subject(v)['binding']['engine_code'])
        c.require(body['candidate_snapshot']['canonical_powertrain']==subject(v)['binding']['properties'],'Subject engine mismatch.')
    elif kind=='Matrix':
        c.require([r['candidate_reference'] for r in v['registry_rows']]==[r['candidate_reference'] for r in v['body_matrix']['rows']],'Registry Matrix membership differs.')
    elif kind=='Manifest':
        c.require(v['matrix_digest']==c.digest(v['matrix'])==v['approval']['matrix_digest'] and v['approval_hash']==c.digest(v['approval']),'Registry approval mismatch.')
    elif kind=='Revalidation':c.require((v['result']=='valid')==(not v['diagnostics']),'Registry revalidation diagnostics differ.')
    elif kind=='Receipt':
        plan=v['plan'];body=plan['body_plan'];report=v['revalidation'];manifest=v['manifest']
        validate_selection(manifest,[plan], subset=True)
        c.require(report['result']=='valid' and report['manifest_hash']==manifest['manifest_hash'],'Registry receipt revalidation mismatch.')
        c.require(report['plan_hashes']==[{'candidate_reference':r['candidate_reference'],'plan_hash':r['plan_hash']} for r in manifest['matrix']['registry_rows']],'Incomplete registry revalidation.')
        c.require(v['persisted_fields']==body['target_fields'] and v['vehicle']['slug']==body['target_slug'],'Registry receipt fields differ.')
        c.require(v['outcome']==('created' if body['action']=='create' else 'no_op') and body['action'] in ('create','no_op'),'Registry receipt outcome differs.')
        if body['action']=='create':c.require(v['engine_uuid']==subject(plan)['binding']['engine']['uuid'],'Persisted Engine differs.')
        else:
            old=next(p for p in plan['peer_engines'] if p['vehicle_uuid']==body['existing_vehicle_uuid'])
            c.require(v['vehicle']['uuid']==body['existing_vehicle_uuid'] and v['engine_uuid']==old['engine_uuid'],'No-op changed Engine association.')


def validate(kind,value):
    try:
        c._json(value);c._check(_expand(LOCAL[kind]),value);_semantic(kind,value);_nested(LOCAL[kind],value)
    except (KeyError,TypeError,ValueError,StopIteration,AttributeError) as exc:raise c.ContractError(str(exc)) from exc
    return value


def parse(kind,raw):
    import json
    return validate(kind,json.loads(raw,object_pairs_hook=c._pairs,parse_constant=lambda _:c.require(False,'Nonfinite JSON.')))


def serialize(kind,value):
    validate(kind,value)
    return c.canonical_json(value).encode("utf-8")


def engine_binding(engine):
    need(engine.internal_variant_key == '', 'ENGINE_VARIANT_UNSUPPORTED', 'Registry 3.1.0 cannot authorize nonempty Engine variants.')
    return seal('Binding',{'manufacturer':{'pk':engine.manufacturer_id,'uuid':str(engine.manufacturer.uuid)},
        'engine':{'pk':engine.pk,'uuid':str(engine.uuid)},'engine_code':engine.engine_code,'name':engine.name,
        'properties':record_powertrain(engine),'updated_at':stamp(engine.updated_at)})


def code_from_candidate(candidate,reference,expected=None):
    index=wire.evidence_index(candidate)
    need(reference in index,'ENGINE_CODE_UNESTABLISHED','Qualified engine-code assertion is unavailable.')
    doc,ast=index[reference];raw=ast['raw_value']
    need(type(raw) is dict and type(raw.get('engine_code')) is str,'ENGINE_CODE_UNESTABLISHED','Explicit qualified configuration engine code is required.')
    if ast['attribute_key']=='research_offering_correspondence':
        need(raw.get('candidate_id')==candidate['candidate_reference'],'ENGINE_CODE_UNESTABLISHED','Engine code row belongs to another offering.')
        need(any(wire.evidence_index(candidate)[q][0] is doc for q in candidate['configuration_refs']),'ENGINE_CODE_UNESTABLISHED','Code row lacks a positive source group.')
    else:need(ast['attribute_key']=='configuration' and reference in candidate['configuration_refs'],'ENGINE_CODE_UNESTABLISHED','Code is not part of the positive configuration.')
    code=normalize_engine_code(raw['engine_code'])
    need(expected is None or code==expected,'ENGINE_REGISTRY_CONFLICT','Complete source engine code differs from registered binding.')
    return code


def _conflicts(candidate,engine,code_reference):
    claims=[candidate.get('canonical_powertrain') or {}]
    technical=((candidate.get('normalized_technical_details') or {}).get('engine') or {})
    if technical.get('cylinders') is not None:claims.append({'engine_cylinders':technical['cylinders']})
    for i in candidate['normalized_assertions']:
        if i['target_attribute_key'] in FIELDS and i['mapping_status']=='mapped':claims.append({i['target_attribute_key']:i['normalized_concept']})
    for claim in claims:
        validate_engine_properties(engine,incoming_powertrain=claim)
    # Only explicit, recognized source claims can contradict a registry value.
    # Missing assertions or different raw spelling are never a conflict.
    from reference.powertrain_evidence import supports
    selected_doc=wire.evidence_index(candidate)[code_reference][0]
    for doc in candidate['evidence_documents']:
        if doc is not selected_doc:continue
        for ast in doc['assertions']:
            raw=ast['raw_value']
            values=({k:raw[k] for k in FIELDS if k in raw} if type(raw) is dict and ast['attribute_key'] in ('configuration','research_offering_correspondence')
                    else {ast['attribute_key']:raw} if ast['attribute_key'] in FIELDS else {k:raw for k in FIELDS} if ast['attribute_key']=='engine_descriptor' else {})
            for key,value in values.items():
                if value is None or supports(value,key,record_powertrain(engine)[key],jeep=True):continue
                if key in TAXONOMIES:
                    conflict=any(supports(value,key,other,jeep=True) for other in TAXONOMIES[key])
                else:
                    conflict=type(value) in (str,int) and str(value).replace('.','',1).isdigit()
                if conflict:raise EngineRegistryError('ENGINE_REGISTRY_CONFLICT','Explicit source '+key+' contradicts the registered engine.')


def verify_code_bytes(root,candidate,reference,code):
    """Verify only the explicit configuration/code join, not engine classifications."""
    import json,csv,io
    doc,ast=wire.evidence_index(candidate)[reference]
    raw=read_retained(root,doc['raw_artifact_reference'],doc['raw_artifact_hash'])
    try:native=json.loads(raw,object_pairs_hook=c._pairs)
    except (ValueError,UnicodeError):native=None
    if type(native) is dict and type(native.get('assertions')) is list:
        ids=[a.get('assertion_id') for a in native['assertions'] if type(a) is dict]
        need(len(ids)==len(native['assertions'])==len(set(ids)),'ENGINE_CODE_UNESTABLISHED','Duplicate or malformed native assertion identities.')
        need(any(c.canonical_json(a)==c.canonical_json(ast) for a in native['assertions']),'ENGINE_CODE_UNESTABLISHED','Code assertion is not in retained native bytes.')
    elif doc['raw_artifact_reference'].endswith(('/candidate_inventory.csv','/factory_reconciliation.csv')):
        rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
        codes={normalize_engine_code(row.get('engine_code','')) for row in rows if row.get('candidate_id')==candidate['candidate_reference']}
        need(codes=={code},'ENGINE_CODE_UNESTABLISHED','Retained offering row does not establish this engine code.')
    else:raise ResolutionError('UNSUPPORTED_SOURCE_READER','No approved explicit configuration/code reader for this artifact.',stage='dependency')


def prepare_registry_candidate(candidate,code_reference, *, root=None, source_candidate=None):
    candidate=deepcopy(candidate);wire.validate_structure(candidate)
    code=code_from_candidate(candidate,code_reference)
    from django.conf import settings
    verify_code_bytes(root or settings.BASE_DIR,candidate,code_reference,code)
    maker=Manufacturer.objects.get(name=candidate['candidate_identity']['manufacturer_name'])
    try:engine=resolve_engine(maker,code)
    except OperationalError as exc:
        if 'no such table: reference_engine' in str(exc):raise EngineRegistryError('ENGINE_NOT_REGISTERED','Registry migration/Engine authoring is unavailable.') from exc
        raise
    _conflicts(candidate,engine,code_reference)
    candidate['canonical_powertrain']=record_powertrain(engine)
    review=candidate.get('reconciliation_and_review')
    if review:
        states=review.get('attribute_states',{})
        for field in FIELDS:states.pop(field,None)
        review['requires_human_review']=any(s['review_disposition'] not in ('not_required','resolved') for s in states.values())
        if not review['requires_human_review']:review['review_workflow_disposition']='resolved'
    candidate['candidate_hash']=wire.candidate_hash(candidate)
    return seal('Candidate',{'registry_candidate_version':VERSION,'candidate':candidate,'binding':engine_binding(engine),'code_reference':code_reference,'source_candidate':source_candidate})


class RegistryRelease(Release):
    registry_aware=True

    def load(self):
        self.bindings={}
        return super().load()

    def _read_candidate(self,reference):
        wrapped=parse('Candidate',read_retained(self.root,reference).decode())
        candidate=wrapped['candidate'];binding=wrapped['binding']
        if wrapped['source_candidate']:
            pin=wrapped['source_candidate'];read_retained(self.root,pin['reference'],pin['byte_hash'])
        code_from_candidate(candidate,wrapped['code_reference'],binding['engine_code'])
        verify_code_bytes(self.root,candidate,wrapped['code_reference'],binding['engine_code'])
        try:engine=resolve_engine(binding['manufacturer']['pk'],binding['engine_code'],
                                  engine_pk=binding['engine']['pk'],engine_uuid=binding['engine']['uuid'])
        except EngineRegistryError as exc:raise ResolutionError(exc.code,str(exc),stage='dependency') from exc
        try:_conflicts(candidate,engine,wrapped['code_reference'])
        except EngineRegistryError as exc:raise ResolutionError(exc.code,str(exc),stage='evidence') from exc
        need(engine_binding(engine)==binding,'ENGINE_REGISTRY_CONFLICT','Pinned Engine identity/state changed; regenerate and obtain fresh approval.')
        self.bindings[candidate['candidate_reference']]={'candidate_reference':candidate['candidate_reference'], 'binding':binding,'code_reference':wrapped['code_reference'],'artifact_hash':wrapped['artifact_hash']}
        return candidate

    def _resolve(self,candidate,row,audit):
        binding=self.bindings[candidate['candidate_reference']]['binding']
        need(binding['engine_code']==normalize_engine_code(row['engine_code']),'ENGINE_REGISTRY_CONFLICT','Source code differs from pinned offering code.')
        return super()._resolve(candidate,row,audit)

    def _source_claims(self,doc):
        return [a for a in doc['assertions'] if a['attribute_key'] not in (*FIELDS,'engine_descriptor','transmission_descriptor')]

    def _requires_source_reader(self,doc):
        return bool(self._source_claims(doc))

    def _reviewed_csv_projection(self, doc, raw, candidate, inventory, generation):
        """Validate MY2024 family selectors and offering rows at their own scopes."""
        import csv
        import io
        from .body_identity import INVENTORY_ROOT
        reference = doc['raw_artifact_reference']
        if reference not in (INVENTORY_ROOT + 'candidate_inventory.csv',
                             INVENTORY_ROOT + 'factory_reconciliation.csv'):
            return False
        need(doc['source_id'] == inventory['source_id'], 'PROJECTION_MISMATCH',
             'CSV source differs from the offering source.', stage='evidence')
        rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8'))))
        selected = [row for row in rows if row.get('candidate_id') == candidate['candidate_reference']]
        need(bool(selected), 'PROJECTION_MISMATCH', 'CSV lacks the exact offering.', stage='evidence')
        for row in selected:
            need(all(row.get(k) == inventory[k] for k in
                     ('model_code', 'marketed_trim', 'body_style', 'engine_code')),
                 'PROJECTION_MISMATCH', 'CSV offering identity differs.', stage='evidence')
        need(set(inventory['quick_order_package'].split(';')) ==
             {q for row in selected for q in row['quick_order_package'].split(';')},
             'PROJECTION_MISMATCH', 'CSV offering QOPs differ.', stage='evidence')
        published = [doc for revision in generation['correspondences']
                     for doc in revision['review_payload']['evidence']]
        if doc in published:
            # The exact immutable published document establishes a family heading,
            # not an individual trim/QOP heading. Its selector still must match.
            need(any(a['attribute_key'] == 'source_model_code' and
                     a['raw_value'] == inventory['model_code'] for a in doc['assertions']),
                 'PROJECTION_MISMATCH', 'Published selector differs from offering.', stage='evidence')
            return True
        expected_heading = (f"United States / MY2024 / Jeep Wrangler ({inventory['body_style']}) / "
                            f"{inventory['marketed_trim']} [{inventory['model_code']} / {inventory['quick_order_package']}]")
        for assertion in self._source_claims(doc):
            key, value = assertion['attribute_key'], assertion['raw_value']
            if key == 'source_model_code':
                ok = value == inventory['model_code']
            elif key == 'source_document_heading':
                ok = value == expected_heading
            elif key == 'research_offering_correspondence':
                ok = (type(value) is dict and value.get('candidate_id') == candidate['candidate_reference']
                      and all(k in inventory and type(v) in (str, int) and str(v) == inventory[k]
                              for k,v in value.items()))
            else:
                raise ResolutionError('UNSUPPORTED_SOURCE_READER',
                                      'Unsupported MY2024 CSV claim: ' + key, stage='dependency')
            need(ok, 'PROJECTION_MISMATCH', 'CSV offering assertion differs.', stage='evidence')
        return True

    def _established_drive(self, candidate):
        """Read the already-reviewed MY2024 offering row, never a prior-year PDF."""
        drives = [i for i in candidate['normalized_assertions']
                  if i['target_attribute_key'] == 'generic_drive_classification']
        # Synthetic/native configuration evidence continues through the ordinary
        # pure validator. Only the retained MY2024 row spelling needs this adapter.
        if len(drives) != 1:
            return False
        item = drives[0]
        doc, assertion = wire.evidence_index(candidate)[item['source_assertion_ref']]
        if assertion['attribute_key'] != 'research_offering_correspondence':
            return False
        from .body_identity import INVENTORY_ROOT
        need(doc['raw_artifact_reference'] in (
                 INVENTORY_ROOT + 'candidate_inventory.csv',
                 INVENTORY_ROOT + 'factory_reconciliation.csv'),
             'UNSUPPORTED_SOURCE_READER', 'Unsupported MY2024 drivetrain row source.', stage='dependency')
        raw = assertion['raw_value']
        need(type(raw) is dict and raw.get('candidate_id') == candidate['candidate_reference']
             and raw.get('model_year') == 2024 and raw.get('market') == 'US',
             'PROJECTION_MISMATCH', 'Drivetrain row belongs to another offering.', stage='evidence')
        need(raw.get('drivetrain') == item['normalized_concept'] == candidate['drivetrain'] == '4WD'
             and item['mapping_status'] == 'mapped'
             and item['normalization'] == {'id': 'source_literal', 'version': '1.0.0'},
             'PROJECTION_MISMATCH', 'MY2024 offering drivetrain differs.', stage='evidence')
        app = next(a for a in candidate['applicability'] if a['applicability_id'] == item['applicability_ref'])
        need(app['market'] == 'US' and app['start_year'] == app['end_year'] == 2024
             and item['source_assertion_ref'] in app['source_assertion_refs']
             and any(wire.evidence_index(candidate)[q][0] is doc
                     for q in app['configuration_refs'] if q in candidate['configuration_refs']),
             'COEXISTENCE_NOT_ESTABLISHED', 'MY2024 drivetrain lacks its exact offering grouping.', stage='evidence')
        # Retained byte and exact CSV-row verification remains in _evidence;
        # this projection adapter grants no source-reader exemption.
        return True

    def _evidence_projection(self,candidate):
        # Registry authority supplies only the five engine targets. Body/scope/drive,
        # source bytes, positive coexistence and all other diagnostics stay mandatory.
        value=deepcopy(candidate);value['canonical_powertrain']=None
        if self._established_drive(candidate):
            value['drivetrain'] = None
            value['normalized_assertions'] = [i for i in value['normalized_assertions']
                                             if i['target_attribute_key'] != 'generic_drive_classification']
            value['attribute_provenance'] = {k:v for k,v in value.get('attribute_provenance',{}).items()
                                           if k != 'generic_drive_classification'}
        value['normalized_assertions']=[i for i in value['normalized_assertions'] if i['target_attribute_key'] not in FIELDS]
        value['attribute_provenance']={k:v for k,v in value.get('attribute_provenance',{}).items() if k not in FIELDS}
        value['candidate_hash']=wire.candidate_hash(value)
        return value

    def _peer_receipt(self,snapshot):
        if snapshot.get('receipt_version')!=VERSION:return super()._peer_receipt(snapshot)
        validate('Receipt',snapshot)
        body=snapshot['plan']['body_plan'];row=subject(snapshot['plan'])
        verify_code_bytes(self.root,body['candidate_snapshot'],row['code_reference'],row['binding']['engine_code'])
        return {**snapshot,'plan':snapshot['plan']['body_plan']}

    def wrap_plan(self,body):
        links=[{'vehicle_uuid':str(v.uuid),'engine_uuid':str(v.engine.uuid) if v.engine_id else None} for v in VehicleDefinition.objects.filter(generation_id=body['generation']['scope']['generation']['pk'],model_year=2024,market='US').select_related('engine').order_by('uuid')]
        selected=self.bindings[body['candidate_reference']]['binding']
        for v in VehicleDefinition.objects.filter(generation_id=body['generation']['scope']['generation']['pk'],model_year=2024,market='US',trim_name=body['target_fields']['trim_name'],drivetrain=body['target_fields']['drivetrain'],engine_id=selected['engine']['pk']):
            need(record_powertrain(v)==selected['properties'],'ENGINE_REGISTRY_CONFLICT','Existing Engine-associated snapshot contradicts its registry definition; no automatic correction.')
        if body['action']=='no_op':
            link=next(p for p in links if p['vehicle_uuid']==body['existing_vehicle_uuid'])
            expected=self.bindings[body['candidate_reference']]['binding']['engine']['uuid']
            need(link['engine_uuid'] in (None,expected),'ENGINE_REGISTRY_CONFLICT','Equal legacy peer has a different registered Engine; no automatic correction.')
        return seal('Plan',{'plan_version':VERSION,'body_plan':body,'engine_bindings':sorted(self.bindings.values(),key=lambda x:x['candidate_reference']),'peer_engines':links})

    def plan(self,reference):
        body=super().plan(reference)
        if 'assessment_version' in body:return body
        try:return self.wrap_plan(body)
        except ResolutionError as exc:
            return c.validate('Assessment3',{'assessment_version':c.VERSION,'candidate_reference':reference,'candidate_hash':body['candidate_hash'],'diagnostics':[exc.diagnostic]})


def build_matrix(plans):
    plans=sorted(plans,key=lambda p:p['body_plan']['candidate_reference'])
    c.require(bool(plans),'No selected registry plans.')
    for p in plans:validate('Plan',p)
    c.require(all(p['engine_bindings']==plans[0]['engine_bindings'] and p['peer_engines']==plans[0]['peer_engines'] for p in plans),'Registry plans do not share pre-batch state.')
    return validate('Matrix',{'matrix_version':VERSION,'body_matrix':legacy.build_matrix([p['body_plan'] for p in plans]),
        'registry_rows':[{'candidate_reference':p['body_plan']['candidate_reference'],'plan_hash':p['plan_hash'],'engine_state_hash':subject(p)['binding']['state_hash'],'engine_uuid':subject(p)['binding']['engine']['uuid']} for p in plans]})


def build_manifest(matrix,approval):
    validate('Matrix',matrix);validate_matrix_approval(matrix,approval)
    return seal('Manifest',{'manifest_version':VERSION,'matrix':matrix,'matrix_digest':c.digest(matrix),'approval':approval,'approval_hash':c.digest(approval)})


def validate_selection(manifest,plans,subset=False):
    validate('Manifest',manifest);validate_matrix_approval(manifest['matrix'],manifest['approval'])
    matrix=build_matrix(plans)
    if subset:
        c.require(all(matrix['body_matrix'][k]==manifest['matrix']['body_matrix'][k] for k in ('scope','family_hash','body_writes')),'Receipt family/scope differs from authorization.')
        c.require(all(row in manifest['matrix']['registry_rows'] for row in matrix['registry_rows']) and all(row in manifest['matrix']['body_matrix']['rows'] for row in matrix['body_matrix']['rows']),'Receipt plan not authorized.')
    else:c.require(matrix==manifest['matrix'],'Exact registry plan selection differs from approval.')


def lock_engines(plans):
    pks={r['binding']['engine']['pk'] for p in plans for r in p['engine_bindings']}
    list(Engine.objects.select_for_update().filter(pk__in=pks).order_by('pk'))


def revalidate(manifest,plans,release):
    validate_selection(manifest,plans);diagnostics=[]
    try:
        candidates,contexts,family=release.load()
        for old in plans:
            key=old['body_plan']['candidate_reference']
            fresh=release.wrap_plan(plan_resolved(candidates[key],*contexts[key],family,release))
            c.require(fresh==old,'Candidate/body/evidence/family/peer/Engine state changed.')
    except (ValidationError,OSError,ValueError,KeyError) as exc:
        diagnostics=[{'stage':'resolution','code':'STALE_PLAN','path':'/','message':str(exc)}]
    return seal('Revalidation',{'revalidation_version':VERSION,'manifest_hash':manifest['manifest_hash'],
        'plan_hashes':[{'candidate_reference':p['body_plan']['candidate_reference'],'plan_hash':p['plan_hash']} for p in plans],
        'result':'stale' if diagnostics else 'valid','diagnostics':diagnostics})


def receipt_snapshot(plan,manifest,report,vehicle,persisted,agent):
    return seal('Receipt',{'receipt_version':VERSION,'manifest':manifest,'plan':plan,'revalidation':report,
        'outcome':'created' if plan['body_plan']['action']=='create' else 'no_op',
        'vehicle':{'pk':vehicle.pk,'uuid':str(vehicle.uuid),'slug':vehicle.slug},'persisted_fields':persisted,
        'engine_uuid':str(vehicle.engine.uuid) if vehicle.engine_id else None,'execution_agent':agent,'executed_at_utc':stamp(datetime.now(timezone.utc))})


def persist(plan,manifest,report,agent):
    return legacy._persist(plan['body_plan'],manifest,report,agent,registry_plan=plan)


def prepare_retained_candidate(reference, *, root=None):
    """Prepare one retained 2.1.0 offering in memory; never write source/candidates.

    Registry rows must already exist. Retained MY2024 rows establish offering
    taxonomy, code and the already-reviewed drivetrain, not engine reclassification.
    Non-engine source/Generation/body dependencies still gate executable planning.
    """
    import json
    from pathlib import Path
    from reference.body_identity import body_preimage, semantic_digest
    from reference.ingestion.normalization.generation import generation_evidence_from_documents
    from django.conf import settings
    root=Path(root or settings.BASE_DIR)
    active,audit,_=Release([],root=root)._inventories()
    need(reference in active,'UNKNOWN_CANDIDATE','Offering is not an active retained consumer member.')
    from .body_identity import INVENTORY_ROOT, SCOPE
    path=INVENTORY_ROOT+'candidates/'+reference+'.provisional-r1.candidate.2.1.0.json'
    raw=read_retained(root,path);original=json.loads(raw,object_pairs_hook=c._pairs)
    from reference.ingestion.serialization import deserialize_artifact
    from reference.ingestion.validation import validate_candidate_configuration
    validate_candidate_configuration(deserialize_artifact(original))
    documents=deepcopy(original['evidence_documents'])
    for doc in documents:
        for key in ('retrieved_at',):
            if doc.get(key):doc[key]=stamp(datetime.fromisoformat(doc[key].replace('Z','+00:00')))
        applicability=doc.get('source_applicability')
        if applicability is not None:
            need(not applicability.get('unknown_fields'),'UNSUPPORTED_SOURCE_READER','Nonempty legacy source extensions require explicit interpretation.')
            applicability.pop('unknown_fields',None)
            if applicability.get('applicability_scope')=='generation':
                applicability.pop('applicability_scope')
                applicability['applicability_basis']='Original legacy scope: generation (not MY2024 applicability proof). '+(applicability.get('applicability_basis') or '')
        doc['assertions'].sort(key=lambda a:a['assertion_id'])
    documents.sort(key=lambda d:(d['source_id'],d['raw_artifact_hash'],d['assertion_set_id']))
    refs={'|'.join((d['source_id'],d['raw_artifact_hash'],d['assertion_set_id'],a['assertion_id'])):(d,a) for d in documents for a in d['assertions']}
    code_refs=[q for q,(_,a) in refs.items() if a['attribute_key']=='research_offering_correspondence' and type(a['raw_value']) is dict and a['raw_value'].get('candidate_id')==reference and a['raw_value'].get('engine_code')==active[reference]['engine_code']]
    need(len(code_refs)==1,'ENGINE_CODE_UNESTABLISHED','Exactly one retained positive engine-code association is required.')
    doc=refs[code_refs[0]][0]
    headings=[q for q,(d,a) in refs.items() if d is doc and a['attribute_key']=='source_document_heading']
    need(len(headings)==1,'ENGINE_CODE_UNESTABLISHED','Engine code must join an explicit offering heading.')
    q=headings[0];door={'2-door':'two-door','4-door':'four-door'}[active[reference]['body_style']]
    values={'make':'Jeep','model':'Wrangler','model_year':2024,'market':'US','trim_name':audit[reference]['owner_required_canonical_trim'],'factory_body.door_configuration':door}
    interpretations=[{'interpretation_id':'registry-preparation-'+k,'source_assertion_ref':q,'target_attribute_key':k,'normalized_concept':v,'mapping_status':'mapped','applicability_ref':'offering','normalization':{'id':'wrangler_door_taxonomy' if k.startswith('factory_body.') else 'wrangler_selector_heading','version':'1.0.0'},'finding_refs':[]} for k,v in values.items()]
    drive = refs[code_refs[0]][1]['raw_value'].get('drivetrain')
    need(drive == active[reference]['drivetrain'] == '4WD', 'PROJECTION_MISMATCH',
         'Retained MY2024 offering lacks its established drivetrain.', stage='evidence')
    interpretations.append({'interpretation_id':'registry-preparation-drive','source_assertion_ref':code_refs[0],
        'target_attribute_key':'generic_drive_classification','normalized_concept':drive,'mapping_status':'mapped',
        'applicability_ref':'offering','normalization':{'id':'source_literal','version':'1.0.0'},'finding_refs':[]})
    # Retain full historical provenance in the hash-pinned source_candidate.
    # Its MY2022 technical layout is no longer an active MY2024 evidence source.
    documents = [d for d in documents if not (
        d['source_id'] == '2022_JP_Wrangler_SP'
        and d['assertion_set_id'] == 'MY2024_Wrangler_technical_layout')]
    pre=body_preimage(SCOPE,{'door_configuration':door})
    candidate={'envelope':{'artifact_type':wire.ARTIFACT_TYPE,'schema_version':'3.0.0','$schema':'urn:rigarchive:contract:candidate_configuration:3.0.0','generator':'registry-aware-preparation/3.1.0'},
        'candidate_reference':reference,'candidate_identity':{'manufacturer_name':'Jeep','vehicle_model_name':'Wrangler','model_year':2024,'market':'US','trim_name':values['trim_name']},
        'canonical_scope':SCOPE,'canonical_identity_contract':'vehicle-definition-body/2','drivetrain':active[reference]['drivetrain'],
        'configuration_refs':[q],'applicability':[{'applicability_id':'offering','scope':SCOPE,'market':'US','start_year':2024,'end_year':2024,'configuration_refs':[q],'source_assertion_refs':sorted([q,code_refs[0]]),'finding_refs':[]}],
        'evidence_documents':documents,'evidence_raw_hashes':sorted({d['raw_artifact_hash'] for d in documents}),
        'generation_evidence':sorted(generation_evidence_from_documents(documents),key=lambda g:(g['source_id'],g['document_hash'],g['assertion_set_id'],g['assertion_id'])),
        'normalized_assertions':sorted(interpretations,key=lambda i:i['interpretation_id']), 'canonical_powertrain':original['canonical_powertrain'],
        'factory_body':{'disposition':'pending','identity':{'semantic_digest':semantic_digest(pre),'preimage':pre},'support':{'applicability_ref':'offering','configuration_refs':[q],'interpretation_refs':['registry-preparation-factory_body.door_configuration'],'equivalence_interpretation_ref':None}},
        'factory_series':None,'reconciliation_and_review':deepcopy(original['reconciliation_and_review'])}
    candidate['candidate_hash']=wire.candidate_hash(candidate)
    return prepare_registry_candidate(candidate,code_refs[0],root=root,source_candidate={'reference':path,'byte_hash':'sha256:'+hashlib.sha256(raw).hexdigest()})
