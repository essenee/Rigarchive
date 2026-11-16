"""Read-only correspondence preview. No Engine authoring or assignment executor."""
from collections import Counter, defaultdict
import hashlib
import json

from django.core.exceptions import ValidationError
from django.utils import timezone

from reference.models import Engine, ImportExecutionReceipt, VehicleDefinition
from reference.powertrain import FIELDS, record_powertrain, validate_powertrain

APPROVED_JL_ESS_NAMES = frozenset({'3.6L V6 with ESS', '3.6L V6 ESS'})
READY = frozenset({'EXACT_MATCH', 'APPROVED_ALIAS_MATCH', 'EXPLICIT_BINDING_MATCH'})
PROFILE_VERSIONS = {'my2025-edmunds-registry/1', 'my2026-edmunds-registry/1', 'my2026-registry/2'}


def _engine(engine):
    return dict(pk=engine.pk, uuid=str(engine.uuid), manufacturer_pk=engine.manufacturer_id,
                code=engine.engine_code, internal_variant_key=getattr(engine, 'internal_variant_key', ''),
                name=engine.name, powertrain=record_powertrain(engine), updated_at=engine.updated_at.isoformat())


def compatibility(vehicle, engine):
    actual = record_powertrain(vehicle)
    expected = record_powertrain(engine)
    conflicts = {key: {'vehicle': actual[key], 'engine': expected[key]}
                 for key in FIELDS if actual[key] not in (None, '') and actual[key] != expected[key]}
    if vehicle.generation.vehicle_model.manufacturer_id != engine.manufacturer_id:
        conflicts['manufacturer'] = 'Engine and vehicle manufacturers differ.'
    try:
        validate_powertrain(expected, complete=True)
    except ValidationError as exc:
        return dict(result='INCOMPLETE_REGISTRY', conflicts=conflicts, fills_unknown=[], reason='; '.join(exc.messages))
    return dict(result='CONFLICT' if conflicts else 'COMPATIBLE', conflicts=conflicts,
                fills_unknown=[key for key in FIELDS if actual[key] in (None, '')], reason='')


def _receipt_pins(receipt, vehicle):
    """Recognize only successful, vehicle-bound registry receipt formats."""
    snap = receipt.resolution_snapshot_json
    if not isinstance(snap, dict):
        return [], []
    body = snap.get('body_import', {})
    supported_body = isinstance(body, dict) and body.get('receipt_version') == '3.1.0'
    supported_profile = snap.get('version') in PROFILE_VERSIONS
    if not (supported_body or supported_profile):
        return [], []
    try:
        prefix = 'created' if receipt.created_vehicle_definition_id == vehicle.pk else 'existing'
        if str(getattr(receipt, prefix + '_vehicle_definition_uuid_snapshot')) != str(vehicle.uuid):
            raise ValueError('Receipt vehicle UUID differs.')
        if (receipt.resolved_generation_id != vehicle.generation_id or receipt.target_model_year != vehicle.model_year
                or receipt.target_trim_name != vehicle.trim_name or receipt.target_drivetrain != vehicle.drivetrain
                or receipt.target_market != vehicle.market):
            raise ValueError('Receipt configuration scope differs from current record.')
        target = receipt.target_fields_json
        if not isinstance(target, dict):
            raise ValueError('Receipt target fields are unavailable.')
        if ('factory_body_configuration_id' in target
                and target['factory_body_configuration_id'] != vehicle.factory_body_configuration_id):
            raise ValueError('Receipt factory body differs from current record.')
        if 'factory_body_configuration_uuid' in target:
            current_body = str(vehicle.factory_body_configuration.uuid) if vehicle.factory_body_configuration_id else None
            if target['factory_body_configuration_uuid'] != current_body:
                raise ValueError('Receipt factory body UUID differs from current record.')
        if supported_body:
            from reference.ingestion.importing.registry_body_import import validate
            validate('Receipt', body)
            if body['vehicle']['uuid'] != str(vehicle.uuid):
                raise ValueError('Registry receipt target differs.')
            candidate = body['plan']['body_plan']['candidate_reference']
            binding = next(r['binding'] for r in body['plan']['engine_bindings'] if r['candidate_reference'] == candidate)
            pin = dict(pk=binding['engine']['pk'], uuid=binding['engine']['uuid'], code=binding['engine_code'])
        else:
            if not isinstance(target, dict) or target.get('engine_id') != snap['row']['fields']['engine_id'] or not snap['plan_hash']:
                raise ValueError('Registry receipt lacks a consistent target binding.')
            engine = next(e for e in snap['engines'].values() if int(e['id']) == int(target['engine_id']))
            pin = dict(pk=int(engine['id']), uuid=engine['uuid'], code=engine['engine_code'])
        pin.update(receipt_pk=receipt.pk, receipt_uuid=str(receipt.uuid), source_id=receipt.source_id,
                   raw_artifact_hash=receipt.raw_artifact_hash, reference=receipt.raw_artifact_reference)
        return [pin], []
    except (KeyError, TypeError, ValueError, AttributeError, StopIteration, ValidationError) as exc:
        return [], [f'Receipt {receipt.pk}: {exc}']


def preview_engine_assignments():
    """Inventory every stored row, including hidden and inactive archival rows."""
    engines = list(Engine.objects.select_related('manufacturer').order_by('pk'))
    by_id = {e.pk: e for e in engines}
    by_manufacturer = defaultdict(list)
    for engine in engines:
        by_manufacturer[engine.manufacturer_id].append(engine)
    vehicles = list(VehicleDefinition.objects.select_related(
        'generation__vehicle_model__manufacturer', 'engine', 'factory_body_configuration').order_by('pk'))
    by_vehicle = {v.pk: v for v in vehicles}
    pins, binding_errors, receipt_info = defaultdict(list), defaultdict(list), defaultdict(list)
    receipts = ImportExecutionReceipt.objects.filter(operation_type='vehicle_definition_import',
        execution_outcome__in=['created', 'no_op_exact_match']).order_by('pk')
    for receipt in receipts.iterator():
        ids = {receipt.created_vehicle_definition_id, receipt.existing_vehicle_definition_id} - {None}
        for pk in ids & by_vehicle.keys():
            found, errors = _receipt_pins(receipt, by_vehicle[pk])
            pins[pk].extend(found); binding_errors[pk].extend(errors)
            receipt_info[pk].append(dict(pk=receipt.pk, source_id=receipt.source_id,
                                        candidate_reference=receipt.candidate_reference,
                                        raw_artifact_reference=receipt.raw_artifact_reference,
                                        raw_artifact_hash=receipt.raw_artifact_hash,
                                        has_supported_registry_binding=bool(found)))
    rows = []
    for v in vehicles:
        model = v.generation.vehicle_model
        manufacturer = model.manufacturer
        candidates = by_manufacturer[manufacturer.pk]
        row = dict(pk=v.pk, uuid=str(v.uuid), manufacturer=manufacturer.name, manufacturer_pk=manufacturer.pk,
                   manufacturer_uuid=str(manufacturer.uuid), model_uuid=str(model.uuid), generation_uuid=str(v.generation.uuid),
                   model=model.name, model_pk=model.pk, generation=v.generation.name, generation_pk=v.generation_id,
                   model_year=v.model_year, market=v.market, trim=v.trim_name,
                   slug=v.slug, base_msrp=str(v.base_msrp) if v.base_msrp is not None else None,
                   updated_at=v.updated_at.isoformat(), factory_body_configuration_pk=v.factory_body_configuration_id,
                   is_active=v.is_active, is_public=v.is_public, engine_name=v.engine_name,
                   existing_engine_pk=v.engine_id, existing_engine=_engine(v.engine) if v.engine_id else None,
                   powertrain=record_powertrain(v), proposed_engine=None, match_method=None,
                   compatibility=None, candidates=[], binding_evidence=pins[v.pk],
                   binding_errors=binding_errors[v.pk], receipts=receipt_info[v.pk],
                   requires_archival_review=not v.is_active)
        if v.engine_id:
            row.update(status='ALREADY_LINKED', match_method='EXISTING_FK', proposed_engine=_engine(v.engine),
                       compatibility=compatibility(v,v.engine), reason='Existing exact FK retained; no reassignment proposed.')
        elif binding_errors[v.pk]:
            row.update(status='CONFLICT', match_method='EXPLICIT_BINDING', reason='Supported registry receipt cannot be safely reused.')
        elif pins[v.pk]:
            identities = {(p['pk'],p['uuid'],p['code']) for p in pins[v.pk]}
            if len(identities) != 1:
                row.update(status='AMBIGUOUS',match_method='EXPLICIT_BINDING',reason='Approved receipts identify different Engines.')
            else:
                pk, uid, code = next(iter(identities)); engine = by_id.get(pk)
                if engine is None:
                    row.update(status='NO_REGISTERED_ENGINE',match_method='EXPLICIT_BINDING',reason='Pinned Engine no longer exists.')
                elif str(engine.uuid) != uid or engine.engine_code != code:
                    row.update(status='CONFLICT',match_method='EXPLICIT_BINDING',reason='Pinned Engine PK/UUID/code differs from registry.')
                else:
                    comp=compatibility(v,engine)
                    row.update(status='EXPLICIT_BINDING_MATCH' if comp['result']=='COMPATIBLE' else 'CONFLICT',
                        match_method='EXPLICIT_BINDING', compatibility=comp,
                        candidates=[_engine(engine)], proposed_engine=_engine(engine) if comp['result']=='COMPATIBLE' else None,
                        reason='Retained registry receipt PK/UUID correspondence; current known values checked.')
        else:
            matches = [e for e in candidates if e.name == v.engine_name]
            method='EXACT_NAME'
            is_alias = (manufacturer.slug=='jeep' and model.slug=='wrangler' and v.generation.slug=='jl'
                        and v.engine_name in APPROVED_JL_ESS_NAMES)
            if not matches and is_alias and v.electrification_type=='none':
                matches=[e for e in candidates if e.name=='3.6L V6'
                         and record_powertrain(e)['engine_displacement_liters']=='3.6'
                         and e.engine_cylinders==6 and e.electrification_type=='none']
                method='WRANGLER_JL_NONHYBRID_36_ESS'
            checked=[(e,compatibility(v,e)) for e in matches]
            compatible=[(e,c) for e,c in checked if c['result']=='COMPATIBLE']
            row['candidates']=[dict(**_engine(e),compatibility=c) for e,c in checked]
            if len(compatible)==1:
                engine,comp=compatible[0]
                row.update(status='EXACT_MATCH' if method=='EXACT_NAME' else 'APPROVED_ALIAS_MATCH',
                    match_method=method, proposed_engine=_engine(engine),compatibility=comp,
                    reason='Exactly one compatible registered Engine for this scoped correspondence.')
            elif len(compatible)>1:
                row.update(status='AMBIGUOUS',match_method=method,reason='Multiple compatible Engine identities; no code/default/first-row selection.')
            elif checked:
                row.update(status='CONFLICT',match_method=method,reason='Named Engine conflicts with known facts or lacks a complete registry identity.')
            elif not candidates:
                row.update(status='NO_REGISTERED_ENGINE',reason='No Engine registered for this manufacturer.')
            else:
                reason=('ESS alias requires known non-hybrid scope; no year/label-based classification inferred.'
                        if is_alias else 'No exact name or approved scoped alias; a reviewed correspondence is needed.')
                row.update(status='INSUFFICIENT_EVIDENCE',reason=reason)
        rows.append(row)
    grouped, patterns, exceptions = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in rows:
        grouped[(row['manufacturer'],row['model'],row['generation'],row['model_year'])].append(row)
        patterns[(row['manufacturer'],row['model'],row['generation'],row['engine_name'],
                  json.dumps(row['powertrain'],sort_keys=True))].append(row)
        if row['status'] not in READY | {'ALREADY_LINKED'}:
            exceptions[(row['manufacturer'],row['model'],row['generation'],row['engine_name'],row['status'],row['reason'],
                        json.dumps(row['powertrain'],sort_keys=True))].append(row['pk'])
    def group_summary(key, values):
        return dict(manufacturer=key[0],model=key[1],generation=key[2],model_year=key[3],
                    total=len(values),linked=sum(r['existing_engine_pk'] is not None for r in values),
                    statuses=dict(sorted(Counter(r['status'] for r in values).items())))
    ready = [r for r in rows if r['status'] in READY]
    report=dict(schema_version='engine-assignment-preview/1', inventory_date=timezone.localdate().isoformat(),
        totals=dict(vehicle_definitions=len(rows),linked=sum(v.engine_id is not None for v in vehicles),
                    unlinked=sum(v.engine_id is None for v in vehicles),registered_engines=len(engines),
                    proposed_compatible=len(ready),proposed_active=sum(r['is_active'] for r in ready),
                    proposed_archived=sum(not r['is_active'] for r in ready),
                    linked_with_conflicts=sum(r['status']=='ALREADY_LINKED' and r['compatibility']['result']!='COMPATIBLE' for r in rows),
                    rows_with_binding_errors=sum(bool(r['binding_errors']) for r in rows),
                    statuses=dict(sorted(Counter(r['status'] for r in rows).items()))),
        engines=[_engine(e) for e in engines],
        groups=[group_summary(k,v) for k,v in sorted(grouped.items())],
        name_patterns=[dict(manufacturer=k[0],model=k[1],generation=k[2],engine_name=k[3],
            powertrain=json.loads(k[4]),count=len(v),linked=sum(r['existing_engine_pk'] is not None for r in v))
            for k,v in sorted(patterns.items())],
        exception_groups=[dict(manufacturer=k[0],model=k[1],generation=k[2],engine_name=k[3],status=k[4],
                               reason=k[5],powertrain=json.loads(k[6]),pks=pks,count=len(pks)) for k,pks in sorted(exceptions.items())], rows=rows)
    report['snapshot_digest']='sha256:'+hashlib.sha256(json.dumps(report,sort_keys=True,default=str).encode()).hexdigest()
    return report
