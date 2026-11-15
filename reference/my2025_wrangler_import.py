"""Owner-authorized, local-only MY2025 Edmunds inventory publication.

This bounded path uses authored Engines, existing bodies and atomic audit receipts.
It does not extend or impersonate the MY2024 Candidate/Matrix wire contracts.
"""
import hashlib
import json
import sys
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.db.models import Q

from reference.body_identity import baseline_preimage, body_preimage, semantic_digest
from reference.engine_registry import prepare_registered_vehicle, resolve_engine
from reference.ingestion.importing.body_identity import family_slugs
from reference.models import (
    BODY_ATTRIBUTES, Engine, FactoryBodyConfiguration, Generation,
    ImportExecutionReceipt, VehicleDefinition,
)
from reference.powertrain import FIELDS, record_powertrain


INVENTORY = 'docs/research/MY2025_JL_edmunds_builder_20261114/inventory.json'
INVENTORY_SHA = '53e05b5b3c4bb0843f2c1d16436a77a42eceef8cd46352affaaa6258399e92cc'
ENGINE_CODES = {'gas_36_v6': 'ERC', 'gas_20_turbo': 'EC1',
                'gas_64_v8': 'ESG', 'phev_20_turbo': 'ECX'}
SCOPE = {'manufacturer_key': 'jeep', 'model_key': 'wrangler', 'generation_key': 'jl'}
VERSION = 'my2025-edmunds-registry/1'


def digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(',', ':'), default=str,
    ).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def snapshot(obj):
    """Bind all stored parent/registry fields, including UUID and update time."""
    return {f.attname: str(getattr(obj, f.attname)) if getattr(obj, f.attname) is not None else None
            for f in obj._meta.concrete_fields}


def _vehicle(row, generation):
    fields = row['fields'].copy()
    fields['engine_displacement_liters'] = Decimal(fields['engine_displacement_liters'])
    return VehicleDefinition(generation=generation, **fields)


def preview():
    """Pure reads: no parents, Engines, receipts or definitions are created."""
    raw = (Path(settings.BASE_DIR) / INVENTORY).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == INVENTORY_SHA, 'Approved inventory bytes changed.')
    inventory = json.loads(raw)
    source_rows = inventory['canonical_configurations']
    require(len(source_rows) == 31, 'Expected exactly 31 approved configurations.')
    generation = Generation.objects.select_related('vehicle_model__manufacturer').get(
        slug='jl', vehicle_model__slug='wrangler', vehicle_model__manufacturer__slug='jeep',
        is_active=True, vehicle_model__is_active=True, vehicle_model__manufacturer__is_active=True,
    )
    model = generation.vehicle_model
    manufacturer = model.manufacturer
    require(list(Generation.objects.filter(
        vehicle_model=model, is_active=True, start_year__lte=2025,
    ).filter(Q(end_year__isnull=True) | Q(end_year__gte=2025))
        .values_list('pk', flat=True)) == [generation.pk], 'MY2025 Generation is ambiguous.')
    engines = {}
    for profile, code in ENGINE_CODES.items():
        require(Engine.objects.filter(manufacturer=manufacturer, engine_code=code).count() == 1,
                f'Engine {code} missing or duplicated.')
        engine = resolve_engine(manufacturer, code)
        incoming = {k: inventory['engine_profiles'][profile][k] for k in FIELDS}
        resolve_engine(manufacturer, code, incoming_powertrain=incoming)
        engines[profile] = engine
    bodies = {}
    for doors in ('two-door', 'four-door'):
        attrs = {k: None for k in BODY_ATTRIBUTES}
        attrs['door_configuration'] = doors
        matches = FactoryBodyConfiguration.objects.filter(generation=generation, **attrs)
        require(matches.count() == 1, f'Expected one existing exact {doors} body.')
        bodies[doors] = matches.get()
    rows = []
    baselines = set()
    for source in source_rows:
        original = source['canonical_fields']
        require(all(original[k] == v for k, v in {
            'manufacturer': 'Jeep', 'vehicle_model': 'Wrangler', 'generation': 'JL',
            'model_year': 2025, 'market': 'US', 'drivetrain': '4WD',
        }.items()), 'Inventory row outside approved scope.')
        profile = source['engine_profile']
        engine = engines[profile]
        resolve_engine(manufacturer, engine.engine_code,
                       incoming_powertrain={k: original[k] for k in FIELDS})
        body = bodies[original['factory_body_configuration']['door_configuration']]
        vehicle = prepare_registered_vehicle(
            manufacturer, engine.engine_code, generation=generation, model_year=2025,
            market='US', drivetrain='4WD', trim_name=original['trim_name'],
            factory_body_configuration=body,
        )
        powertrain = record_powertrain(engine)
        basis = baseline_preimage(scope=SCOPE, model_year=2025, trim_name=vehicle.trim_name,
            drivetrain='4WD', market='US', canonical_powertrain=powertrain,
            body_digest=semantic_digest(body_preimage(SCOPE, {'door_configuration': body.door_configuration})))
        identity = semantic_digest(basis)
        require(identity not in baselines, 'Duplicate canonical identity in inventory.')
        baselines.add(identity)
        rows.append({'inventory_id': source['inventory_id'], 'identity_digest': identity,
            'edmunds_style_ids': source['edmunds_style_ids'], 'source_urls': source['source_urls'],
            'source_fields': original, 'baseline': basis, 'engine_code': engine.engine_code,
            'fields': {'model_year': 2025, 'trim_name': vehicle.trim_name,
                'engine_name': engine.name, 'engine_id': engine.pk,
                'factory_body_configuration_id': body.pk, 'market': 'US', 'drivetrain': '4WD',
                **powertrain}, 'legacy_base_slug': vehicle.build_slug(),
            'body_attributes': {k: getattr(body, k) for k in BODY_ATTRIBUTES},
            'candidate_reference': source['inventory_id']})
    slugs = family_slugs(rows)
    namespace = list(VehicleDefinition.objects.filter(generation=generation, model_year=2025)
                     .order_by('pk'))
    for row in rows:
        row['fields']['slug'] = slugs[row['inventory_id']]
        equal = []
        conflicts = []
        for peer in namespace:
            same_group = (peer.trim_name == row['fields']['trim_name'] and peer.market == 'US'
                          and peer.drivetrain == '4WD')
            same_body = peer.factory_body_configuration_id == row['fields']['factory_body_configuration_id']
            if same_group and (same_body or peer.factory_body_configuration_id is None):
                if any(getattr(peer, k) is None for k in FIELDS):
                    conflicts.append('Existing peer has incomplete identity.')
                elif record_powertrain(peer) == row['baseline']['canonical_powertrain']:
                    if same_body and peer.is_active and all(
                        getattr(peer, key) == (Decimal(value) if key == FIELDS[0] else value)
                        for key, value in row['fields'].items()
                    ):
                        equal.append(peer)
                    else:
                        conflicts.append('Existing semantic identity differs from exact target.')
            if peer.slug == row['fields']['slug'] and peer not in equal:
                conflicts.append('Target slug occupied by a different or inactive record.')
        if len(equal) > 1:
            conflicts.append('Duplicate existing semantic identity.')
        try:
            if not equal:
                _vehicle(row, generation).full_clean()
        except ValidationError as exc:
            conflicts.append(str(exc))
        row['action'] = 'block' if conflicts else ('skip' if equal else 'create')
        row['reasons'] = conflicts
        row['existing_id'] = equal[0].pk if len(equal) == 1 else None
    plan = {'version': VERSION, 'source_sha256': INVENTORY_SHA,
        'extraction_date': inventory['extraction_date'],
        'parents': [snapshot(manufacturer), snapshot(model), snapshot(generation)],
        'engines': {key: snapshot(value) for key, value in engines.items()},
        'bodies': {key: snapshot(value) for key, value in bodies.items()},
        'namespace': [snapshot(peer) for peer in namespace], 'rows': rows,
        'counts': {action: sum(r['action'] == action for r in rows) for action in ('create', 'skip', 'block')}}
    plan['plan_hash'] = digest(plan)
    return plan


def require_local_database():
    require(connection.vendor == 'sqlite' and settings.DEBUG
            and sys.platform != 'linux'
            and Path(str(connection.settings_dict['NAME'])).resolve()
                == (Path(settings.BASE_DIR) / 'db.sqlite3').resolve(),
            'Execution requires the local desktop development SQLite database with DEBUG enabled.')


def execute(approved_hash, *, operator='project_owner', agent='codex'):
    """Rebuild the exact preview inside the same transaction as all writes."""
    require_local_database()
    from reference.ingestion.attribution import resolve_attribution
    attribution = resolve_attribution(operator=operator, agent=agent)
    with transaction.atomic():
        # Parent/registry locks also document the effective dependency set.
        list(Engine.objects.select_for_update().filter(engine_code__in=ENGINE_CODES.values()))
        list(FactoryBodyConfiguration.objects.select_for_update().filter(generation__slug='jl'))
        plan = preview()
        require(plan['plan_hash'] == approved_hash, 'Stale or unapproved preview; regenerate and review.')
        require(plan['counts']['block'] == 0, 'Blocked rows prevent the entire batch.')
        generation = Generation.objects.get(pk=int(plan['parents'][2]['id']))
        outcomes = []
        for row in plan['rows']:
            created = row['action'] == 'create'
            vehicle = _vehicle(row, generation) if created else VehicleDefinition.objects.get(pk=row['existing_id'])
            if created:
                vehicle.full_clean()
                vehicle.save(force_insert=True)
            outcome = 'created' if created else 'no_op_exact_match'
            prefix = 'created' if created else 'existing'
            receipt = ImportExecutionReceipt.objects.create(
                operator_label=attribution.director, execution_channel='cli',
                manifest_hash=approved_hash, candidate_reference=row['inventory_id'],
                planned_action='create' if created else 'no_op_exact_match',
                create_basis='body_aware_identity' if created else '',
                source_id='edmunds_my2025_wrangler_builder', raw_artifact_hash='sha256:' + INVENTORY_SHA,
                raw_artifact_reference=INVENTORY, source_identity_type='style_id',
                native_identifier=','.join(row['edmunds_style_ids']),
                resolved_generation_id=generation.pk, target_slug=vehicle.slug,
                target_model_year=2025, target_trim_name=vehicle.trim_name,
                target_engine_name=vehicle.engine_name, target_drivetrain=vehicle.drivetrain,
                target_market=vehicle.market, target_fields_json=row['fields'],
                resolution_snapshot_json={'version': VERSION, 'execution_agent': attribution.agent,
                    'source_urls': row['source_urls'], 'extraction_date': plan['extraction_date'],
                    'row': row, 'parents': plan['parents'], 'engines': plan['engines'],
                    'bodies': plan['bodies'], 'plan_hash': approved_hash},
                execution_outcome=outcome, messages_json=['Exact preview revalidated; owner-authorized MY2025 registry mapping.'],
                **{prefix + '_vehicle_definition': vehicle,
                   prefix + '_vehicle_definition_pk_snapshot': vehicle.pk,
                   prefix + '_vehicle_definition_uuid_snapshot': str(vehicle.uuid),
                   prefix + '_vehicle_definition_slug_snapshot': vehicle.slug},
            )
            outcomes.append({'inventory_id': row['inventory_id'], 'outcome': outcome,
                'pk': vehicle.pk, 'uuid': str(vehicle.uuid), 'slug': vehicle.slug, 'receipt_pk': receipt.pk})
        return {'plan_hash': approved_hash, 'created': plan['counts']['create'],
                'skipped': plan['counts']['skip'], 'failed': 0, 'outcomes': outcomes}
