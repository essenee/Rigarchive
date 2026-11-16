"""Bounded, owner-approved registry association; never authors Engines."""
from collections import Counter
import hashlib
import json

from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction

from reference.engine_reconciliation import preview_engine_assignments
from reference.models import Engine, VehicleDefinition
from reference.powertrain import FIELDS

APPROVED_DIGEST = 'sha256:7ab06c7f7afa590ff7bcd4172e196b5e4b19e596305987467c76ed2b3676bbb8'
APPROVED_COUNTS = {'EXACT_MATCH': 485, 'APPROVED_ALIAS_MATCH': 22}
MATCHES = frozenset(APPROVED_COUNTS)


def wire(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def canonical_state():
    """Every concrete field, not just the identity/display subset in the preview."""
    return wire(dict(vehicles=list(VehicleDefinition.objects.order_by('pk').values()),
                     engines=list(Engine.objects.order_by('pk').values())))


def validate_assignments(plan):
    if (plan.get('schema_version') != 'engine-assignment-preview/1'
            or plan.get('snapshot_digest') != APPROVED_DIGEST
            or digest({k: v for k, v in plan.items() if k != 'snapshot_digest'}) != APPROVED_DIGEST):
        raise ValidationError('Unapproved or altered assignment artifact.')
    proposals = [r for r in plan['rows'] if r['status'] in MATCHES]
    if dict(Counter(r['status'] for r in proposals)) != APPROVED_COUNTS:
        raise ValidationError('Approved assignment counts differ.')
    if len({r['pk'] for r in proposals}) != len(proposals):
        raise ValidationError('Duplicate approved VehicleDefinition PK.')
    current = preview_engine_assignments()
    if current['engines'] != plan['engines']:
        raise ValidationError('Stale Engine registry: records or registered properties changed.')
    rows = {r['pk']: r for r in current['rows']}
    pending, completed, errors = [], [], []
    for approved in proposals:
        pk = approved['pk']
        now = rows.get(pk)
        if now is None or now['uuid'] != approved['uuid']:
            errors.append(f'{pk}: VehicleDefinition missing or UUID changed.')
            continue
        if now['existing_engine_pk'] is None:
            if now != approved:
                errors.append(f'{pk}: stale proposal, match or VehicleDefinition state changed.')
            else:
                vehicle = VehicleDefinition.objects.get(pk=pk, uuid=approved['uuid'])
                vehicle.engine = Engine.objects.get(pk=approved['proposed_engine']['pk'],
                                                    uuid=approved['proposed_engine']['uuid'])
                try:
                    vehicle.full_clean()
                except ValidationError as exc:
                    errors.append(f'{pk}: model validation failed: {exc}')
                else:
                    pending.append(approved)
            continue
        # A rerun may retain exactly the approved association and filled unknowns.
        target = approved['proposed_engine']
        stable = ('uuid', 'manufacturer_pk', 'manufacturer_uuid', 'model_pk', 'model_uuid',
                  'generation_pk', 'generation_uuid', 'model_year', 'market', 'trim', 'slug',
                  'base_msrp', 'factory_body_configuration_pk', 'is_active', 'is_public', 'engine_name')
        expected_powertrain = {k: (target['powertrain'][k] if approved['powertrain'][k] is None
                                   else approved['powertrain'][k]) for k in FIELDS}
        if (any(now[k] != approved[k] for k in stable)
                or now['existing_engine'] != target or now['powertrain'] != expected_powertrain):
            errors.append(f'{pk}: existing association or preserved fields differ from approved result.')
        else:
            completed.append(approved)
    if errors:
        raise ValidationError(errors)
    return pending, completed


def execute_assignments(plan, *, baseline=None):
    """All-or-nothing, full-field preservation checked before transaction commit."""
    with transaction.atomic():
        # SQLite serializes writers. Other supported DBs also take row locks here.
        list(Engine.objects.select_for_update().order_by('pk'))
        list(VehicleDefinition.objects.select_for_update().order_by('pk'))
        before = canonical_state()
        if baseline is not None and before != baseline:
            raise ValidationError('Canonical records changed after the verified backup/baseline.')
        pending, completed = validate_assignments(plan)
        counts, fills = Counter(), Counter()
        for row in pending:
            vehicle = VehicleDefinition.objects.get(pk=row['pk'], uuid=row['uuid'], engine__isnull=True)
            vehicle.engine = Engine.objects.get(pk=row['proposed_engine']['pk'], uuid=row['proposed_engine']['uuid'])
            vehicle.full_clean()
            # Explicit fields prevent unrelated historical state from being saved.
            # full_clean has already completed unknowns through the model repair.
            unknown = row['compatibility']['fills_unknown']
            vehicle.save(update_fields={'engine', 'updated_at', *unknown})
            counts[row['status']] += 1
            fills.update(unknown)
        after = canonical_state()
        if before['engines'] != after['engines']:
            raise ValidationError('Engine registry preservation failure.')
        old = {r['id']: r for r in before['vehicles']}
        new = {r['id']: r for r in after['vehicles']}
        if old.keys() != new.keys():
            raise ValidationError('VehicleDefinition creation/deletion detected.')
        approved_by_pk = {r['pk']: r for r in pending}
        changes = []
        for pk, original in old.items():
            diff = {k: {'before': v, 'after': new[pk][k]} for k, v in original.items() if v != new[pk][k]}
            if not diff:
                continue
            proposal = approved_by_pk.get(pk)
            if proposal is None:
                raise ValidationError(f'{pk}: unapproved record changed.')
            allowed = {'engine_id', 'updated_at', *proposal['compatibility']['fills_unknown']}
            if set(diff) - allowed or new[pk]['engine_id'] != proposal['proposed_engine']['pk']:
                raise ValidationError(f'{pk}: unauthorized field change.')
            for field in proposal['compatibility']['fills_unknown']:
                engine = next(e for e in after['engines'] if e['id'] == new[pk]['engine_id'])
                if original[field] not in (None, '') or new[pk][field] != engine[field]:
                    raise ValidationError(f'{pk}: invalid unknown-attribute completion.')
            changes.append(dict(pk=pk, uuid=new[pk]['uuid'], match_method=proposal['match_method'], fields=diff))
        if {r['pk'] for r in changes} != set(approved_by_pk):
            raise ValidationError('Changed row set differs from approved pending set.')
        return dict(schema_version='engine-assignment-execution/1', approval_digest=APPROVED_DIGEST,
                    assigned=len(pending), skipped_already_applied=len(completed), failed=0,
                    assignments_by_method=dict(counts), unknown_attributes_completed=dict(fills),
                    before_digest=digest(before), after_digest=digest(after),
                    engines_preserved=True, identities_and_unrelated_fields_preserved=True,
                    changes=changes)
