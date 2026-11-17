"""Protected variant-key correction, never an ingestion or reassignment operation."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from uuid import uuid4, UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction

from reference.models import Engine, EngineIdentityCorrection, ImportExecutionReceipt, VehicleDefinition, normalize_internal_variant_key
from reference.powertrain import FIELDS, record_powertrain

VERSION = 'engine-identity-correction/1'


def wire(value):
    # Correction previews preserve exact database state, including microseconds.
    # DjangoJSONEncoder truncates datetimes to milliseconds.
    def exact(item):
        from datetime import date, time
        from decimal import Decimal
        if isinstance(item, (date, time)):
            return item.isoformat()
        if isinstance(item, (Decimal, UUID)):
            return str(item)
        raise TypeError(type(item).__name__)
    return json.loads(json.dumps(value, default=exact, allow_nan=False))


def digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(wire(value), sort_keys=True,
        separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def require_authorized(actor):
    if not (actor and actor.is_authenticated and actor.is_active and actor.is_staff
            and actor.has_perm('reference.change_engine')
            and actor.has_perm('reference.correct_engine_identity')):
        raise PermissionDenied('Engine correction requires change_engine and correct_engine_identity permissions.')


def _mentions(value, engine):
    """Conservative identification of registered Engine pins, not display-name joins."""
    if isinstance(value, dict):
        if (value.get('engine_id') == engine.pk or value.get('engine_pk') == engine.pk
                or (isinstance(value.get('engine'),dict) and value['engine'].get('pk') == engine.pk)):
            return True
        if (value.get('engine_code') == engine.engine_code
                and 'internal_variant_key' in value and value['internal_variant_key'] == engine.internal_variant_key):
            return True
        if value.get('engine_code') == engine.engine_code and str(value.get('id')) == str(engine.pk):
            return True
        return any(_mentions(v, engine) for v in value.values())
    if isinstance(value, list):
        return any(_mentions(v, engine) for v in value)
    return isinstance(value, str) and engine.uuid.hex in value.replace('-', '').lower()


def _retained_authorizations(engine):
    findings, blockers = [], []
    root = Path(settings.BASE_DIR)
    assignment = root/'docs/research/engine_registry_reconciliation_20261115/assignment_preview.json'
    if not assignment.is_file():
        return [], ['Original assignment approval is unavailable; impact cannot be established.']
    raw = assignment.read_bytes(); plan = json.loads(raw)
    from reference.engine_assignment import digest as assignment_digest, APPROVED_DIGEST
    if plan.get('snapshot_digest') != APPROVED_DIGEST or assignment_digest({k:v for k,v in plan.items() if k != 'snapshot_digest'}) != APPROVED_DIGEST:
        blockers.append('Original assignment approval integrity differs.')
    bound = [r['pk'] for r in plan['rows'] if r.get('status') in ('EXACT_MATCH','APPROVED_ALIAS_MATCH')
             and (r.get('proposed_engine') or {}).get('pk') == engine.pk
             and str((r.get('proposed_engine') or {}).get('uuid','')).replace('-','') == engine.uuid.hex]
    if bound:
        blockers.append('Original approved assignment targets this Engine; explicit variant-bearing historical binding must remain valid.')
    findings.append({'reference':str(assignment.relative_to(root)), 'sha256':hashlib.sha256(raw).hexdigest(),
                     'approved_assignments_to_engine':bound,
                     'registry_observation_only':not bool(bound),
                     'note':'Stored approval stays unchanged; registry drift requires fresh authorization for any future assignment.'})
    for year, names in [(2025, ['local_import_preview','local_import_rerun_preview']),
                        (2026, ['local_import_preview','local_import_rerun_preview','america250_incremental_preview','america250_rerun_preview'])]:
        for name in names:
            path=root/f'docs/research/MY{year}_JL_edmunds_builder_20261114/{name}_20261114.json'
            if not path.is_file():
                blockers.append('Historical registry approval unavailable: '+str(path.relative_to(root)));continue
            raw=path.read_bytes(); value=json.loads(raw)
            from reference.my2025_wrangler_import import digest as profile_digest
            if value.get('plan_hash') != profile_digest({k:v for k,v in value.items() if k != 'plan_hash'}):
                blockers.append('Historical profile approval integrity differs: '+str(path.relative_to(root)))
            mentioned=_mentions(value.get('engines', {}),engine)
            if mentioned: blockers.append('Legacy registry profile cannot represent a nonempty/corrected variant: '+str(path.relative_to(root)))
            findings.append({'reference':str(path.relative_to(root)),'sha256':hashlib.sha256(raw).hexdigest(),'engine_bound':mentioned})
    return findings, blockers


def assess_impact(engine):
    """Full current dependency fingerprints; closed historical formats fail closed."""
    vehicles=list(VehicleDefinition.objects.filter(engine=engine).order_by('pk').values())
    expected=record_powertrain(engine); conflicts=[]
    for row in vehicles:
        for key in FIELDS:
            actual=row[key]
            if key=='engine_displacement_liters' and actual is not None:
                from reference.powertrain import decimal_string
                actual=decimal_string(actual)
            if actual is not None and actual != expected[key]:
                conflicts.append(f"VehicleDefinition {row['id']} has incompatible {key}.")
    receipts=list(ImportExecutionReceipt.objects.order_by('pk').values())
    dependencies=[]; blockers=list(conflicts)
    for row in receipts:
        snapshot=row['resolution_snapshot_json']
        if not (_mentions(snapshot,engine) or _mentions(row['target_fields_json'],engine)):
            continue
        version=snapshot.get('version') if isinstance(snapshot,dict) else None
        if version in ('my2021-approved-matrix-revalidation/1','my2022-approved-matrix-revalidation/1'):
            from reference import my2021_wrangler_revalidation, my2022_wrangler_revalidation
            module=my2021_wrangler_revalidation if version.startswith('my2021') else my2022_wrangler_revalidation
            try:module.validate_compact(ImportExecutionReceipt.objects.get(pk=row['id']))
            except ValidationError: blockers.append(f"Compact receipt {row['id']} already fails current validation.")
            disposition='PK/UUID and unchanged five-field identity remain valid; no variant assertion.'
        else:
            blockers.append(f"Receipt {row['id']} binds this Engine under a legacy or unrecognized format; correction requires separately reviewed compatibility evidence.")
            disposition='blocked'
        dependencies.append({'receipt_pk':row['id'],'receipt_uuid':str(row['uuid']),'version':version,'disposition':disposition})
    artifacts, issues=_retained_authorizations(engine);blockers.extend(issues)
    return wire({'associated_vehicle_count':len(vehicles),'associated_vehicle_pks':[v['id'] for v in vehicles],
        'vehicles_digest':digest(vehicles),'receipt_corpus_digest':digest(receipts),
        'registry_digest':digest(list(Engine.objects.order_by('pk').values())),
        'receipt_dependencies':dependencies,'retained_authorizations':artifacts,'blockers':blockers,
        'eligible':not blockers,'historical_policy':'No receipt/manifest rewrite or empty-key reinterpretation. State-sensitive unexecuted plans become stale; old artifacts remain immutable.'})


def preview_correction(engine_pk, *, proposed_key, reason, actor, request_reference=None):
    require_authorized(actor)
    if not isinstance(reason,str) or not reason.strip(): raise ValidationError('A correction explanation is required.')
    key=normalize_internal_variant_key(proposed_key)
    engine=Engine.objects.select_related('manufacturer').get(pk=engine_pk)
    if key==engine.internal_variant_key:raise ValidationError('Proposed key must differ from the current key.')
    if Engine.objects.filter(manufacturer_id=engine.manufacturer_id,engine_code=engine.engine_code,internal_variant_key=key).exclude(pk=engine.pk).exists():
        raise ValidationError('The proposed manufacturer/code/key identity already exists.')
    before=wire(Engine.objects.filter(pk=engine.pk).values().get());after=deepcopy(before);after['internal_variant_key']=key
    review=wire({'version':VERSION,'request_reference':str(UUID(str(request_reference))) if request_reference else str(uuid4()),
        'actor_pk':actor.pk,'actor_label':actor.get_username(),'manufacturer_name':engine.manufacturer.name,
        'before':before,'after':after,'reason':reason.strip(),'impact':assess_impact(engine)})
    review['review_digest']=digest(review)
    return review


def execute_correction(review, *, actor, acknowledged=False, confirmed=False):
    """Only this transaction can perform the narrowly parameterized identity write."""
    require_authorized(actor)
    if acknowledged is not True or confirmed is not True:raise ValidationError('Explicit acknowledgment and confirmation are required.')
    if not isinstance(review,dict) or review.get('version')!=VERSION or review.get('review_digest')!=digest({k:v for k,v in review.items() if k!='review_digest'}):
        raise ValidationError('Invalid reviewed correction request.')
    if review['actor_pk'] != actor.pk:raise PermissionDenied('Review belongs to another administrator.')
    with transaction.atomic():
        if EngineIdentityCorrection._meta.db_table not in connection.introspection.table_names():
            raise ValidationError('Correction audit storage is unavailable; migration 0016 requires separate authorization.')
        try:
            engine=Engine.objects.select_for_update().get(pk=review['before']['id'],uuid=review['before']['uuid'])
        except Engine.DoesNotExist as exc:
            raise ValidationError('Stale correction preview: Engine PK/UUID is unavailable.') from exc
        current=preview_correction(engine.pk,proposed_key=review['after']['internal_variant_key'],reason=review['reason'],actor=actor,request_reference=review['request_reference'])
        if current != review:raise ValidationError('Stale correction preview; review the current state again.')
        if not current['impact']['eligible']:raise ValidationError(current['impact']['blockers'])
        # No public model bypass or unrestricted QuerySet update. SQLite serializes
        # writes; competing read-to-write upgrades fail/rollback, never lose a write.
        with connection.cursor() as cursor:
            cursor.execute('UPDATE reference_engine SET internal_variant_key=%s WHERE id=%s AND uuid=%s AND internal_variant_key=%s',
                [current['after']['internal_variant_key'],engine.pk,engine.uuid.hex,current['before']['internal_variant_key']])
            if cursor.rowcount!=1:raise ValidationError('Engine changed before correction; no update applied.')
        engine.refresh_from_db()
        actual=wire(Engine.objects.filter(pk=engine.pk).values().get())
        if actual != current['after']:raise ValidationError('Unexpected Engine preservation difference.')
        # Verify associations and all their values again; raising rolls back key+audit.
        if digest(list(VehicleDefinition.objects.filter(engine=engine).order_by('pk').values())) != current['impact']['vehicles_digest']:
            raise ValidationError('Vehicle preservation check failed.')
        return EngineIdentityCorrection.objects.create(engine=engine,engine_pk_snapshot=engine.pk,
            engine_uuid_snapshot=engine.uuid,actor=actor,actor_label=actor.get_username(),
            request_reference=current['request_reference'],review_digest=current['review_digest'],reason=current['reason'],
            before_state=current['before'],after_state=actual,impact=current['impact'])
