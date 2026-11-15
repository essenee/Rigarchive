"""Owner-authorized, local-only MY2026 inventory and America250 supplement.

This bounded adaptation reuses the MY2025 safety helpers and canonical services.
It does not change historical import contracts or author Engine records.
"""
import hashlib
import json
from decimal import Decimal
from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from reference.body_identity import baseline_preimage, body_preimage, semantic_digest
from reference.engine_registry import prepare_registered_vehicle, resolve_engine
from reference.ingestion.importing.body_identity import family_slugs
from reference.models import (
    BODY_ATTRIBUTES, Engine, FactoryBodyConfiguration, Generation,
    ImportExecutionReceipt, VehicleDefinition,
)
from reference.powertrain import FIELDS, record_powertrain
from reference.my2025_wrangler_import import digest, require, snapshot, _vehicle, require_local_database


INVENTORY = 'docs/research/MY2026_JL_edmunds_builder_20261114/inventory.json'
INVENTORY_SHA = 'aafe8c3005c95937d6269fee4a1808cf16b453e156cc1c500beddf17237525d0'
SUPPLEMENT = 'docs/research/MY2026_JL_edmunds_builder_20261114/america250_supplement.json'
SUPPLEMENT_SHA = '0032ae7ce345a962e9f16229ff96f72e892af6c1fbb558b336b2f5b7c7c85311'
ENGINE_CODES = {'gas_36_v6': 'ERC', 'gas_20_turbo': 'EC1',
                'gas_64_v8': 'ESG'}
SCOPE = {'manufacturer_key': 'jeep', 'model_key': 'wrangler', 'generation_key': 'jl'}
VERSION = 'my2026-registry/2'
EXPECTED_ENGINE_PKS = {'ERC': 1, 'EC1': 2, 'ESG': 3}


def validate_inventory(inventory):
    """Check source membership and expected counts without manufacturing rows."""
    styles = {s['edmunds_style_id']: s for s in inventory['styles']}
    rows = inventory['canonical_configurations']
    require(len(styles) == len(inventory['styles']) == 18, 'Expected 18 unique styles.')
    require(len(rows) == len({r['inventory_id'] for r in rows}) == 33,
            'Expected 33 unique inventory rows.')
    require(Counter(r['canonical_fields']['manufacturer_engine_code'] for r in rows)
            == {'ERC': 15, 'EC1': 16, 'ESG': 2}, 'Engine inventory counts differ.')
    require(Counter(r['canonical_fields']['factory_body_configuration']['door_configuration']
                    for r in rows) == {'two-door': 10, 'four-door': 23},
            'Factory body inventory counts differ.')
    require({sid for r in rows for sid in r['edmunds_style_ids']} == set(styles),
            'Inventory does not cover every observed style.')
    for row in rows:
        require(len(row['edmunds_style_ids']) == 1, 'Expected one observed style per row.')
        style = styles[row['edmunds_style_ids'][0]]
        fields = row['canonical_fields']
        offered = ([style['standard_engine_profile']] if row['engine_availability'] == 'standard'
                   else [o['engine_profile'] for o in style['optional_engines']])
        require(row['engine_availability'] in ('standard', 'optional')
                and row['engine_profile'] in offered
                and fields['trim_name'] == style['canonical_trim'] == style['marketed_trim']
                and fields['factory_body_configuration'] == style['factory_body']
                and style['builder_url'] in row['source_urls']
                and style['specifications_url'] in row['source_urls'],
                'Canonical row differs from its observed style/engine offering.')
        require(fields['fuel_type'] == 'gasoline' and fields['electrification_type'] == 'none',
                'MY2026 inventory must contain only the approved gasoline offerings.')


def validate_supplement(supplement):
    """Only the two owner-confirmed Jeep rows; never manufacture Edmunds IDs."""
    rows = supplement['canonical_configurations']
    require(len(rows) == 2 and len({r['inventory_id'] for r in rows}) == 2,
            'Expected exactly two unique America250 supplement rows.')
    require({r['engine_profile'] for r in rows} == {'gas_36_v6', 'gas_20_turbo'},
            'America250 requires exactly the confirmed ERC and EC1 offerings.')
    for row in rows:
        fields = row['canonical_fields']
        code = ENGINE_CODES[row['engine_profile']]
        confirmation = row['source_confirmation']
        require(fields['trim_name'] == 'America250'
                and fields['factory_body_configuration'] == {'door_configuration': 'four-door'}
                and fields['manufacturer_engine_code'] == row['source_engine_code'] == code
                and fields['fuel_type'] == 'gasoline' and fields['electrification_type'] == 'none'
                and row['engine_availability'] == 'owner_confirmed'
                and row['edmunds_style_ids'] == [] and row['transmission_pairing'] is None,
                'Supplement must preserve confirmed trim/body/engines and unknown pairings.')
        require(row['source_id'] == 'jeep_my2026_owner_confirmed_builder'
                and row['source_identity_type'] == 'owner_confirmed_configuration'
                and row['native_identifier'] == 'America250-four-door-' + code
                and confirmation['publisher'] == 'Jeep.com'
                and confirmation['confirmed_by'] == 'project_owner'
                and confirmation['supplied_url_demonstrates_engine_code'] == 'ERC'
                and confirmation['url_proves_this_engine'] is (code == 'ERC')
                and len(row['source_urls']) == 1
                and row['source_urls'][0].startswith('https://www.jeep.com/bmo.wrangler.html#')
                and ',ERC,' in row['source_urls'][0],
                'Jeep owner confirmation must remain distinct from Edmunds and EC1 URL proof.')


def preview():
    """Pure reads: no parents, Engines, receipts or definitions are created."""
    raw = (Path(settings.BASE_DIR) / INVENTORY).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == INVENTORY_SHA, 'Approved inventory bytes changed.')
    inventory = json.loads(raw)
    validate_inventory(inventory)
    supplement_raw = (Path(settings.BASE_DIR) / SUPPLEMENT).read_bytes()
    require(hashlib.sha256(supplement_raw).hexdigest() == SUPPLEMENT_SHA,
            'Approved America250 supplement bytes changed.')
    supplement = json.loads(supplement_raw)
    validate_supplement(supplement)
    sources = [
        {'source_id': 'edmunds_my2026_wrangler_builder', 'reference': INVENTORY,
         'sha256': INVENTORY_SHA, 'extraction_date': inventory['extraction_date']},
        {'source_id': 'jeep_my2026_owner_confirmed_builder', 'reference': SUPPLEMENT,
         'sha256': SUPPLEMENT_SHA, 'extraction_date': supplement['extraction_date']},
    ]
    source_rows = ([(row, sources[0]) for row in inventory['canonical_configurations']]
                   + [(row, sources[1]) for row in supplement['canonical_configurations']])
    require(len(source_rows) == 35, 'Expected exactly 35 approved configurations.')
    generation = Generation.objects.select_related('vehicle_model__manufacturer').get(
        slug='jl', vehicle_model__slug='wrangler', vehicle_model__manufacturer__slug='jeep',
        is_active=True, vehicle_model__is_active=True, vehicle_model__manufacturer__is_active=True,
    )
    model = generation.vehicle_model
    manufacturer = model.manufacturer
    require(list(Generation.objects.filter(
        vehicle_model=model, is_active=True, start_year__lte=2026,
    ).filter(Q(end_year__isnull=True) | Q(end_year__gte=2026))
        .values_list('pk', flat=True)) == [generation.pk], 'MY2026 Generation is ambiguous.')
    engines = {}
    for profile, code in ENGINE_CODES.items():
        require(Engine.objects.filter(manufacturer=manufacturer, engine_code=code).count() == 1,
                f'Engine {code} missing or duplicated.')
        engine = resolve_engine(manufacturer, code)
        reference = inventory['engine_profiles'][profile]
        require(engine.pk == EXPECTED_ENGINE_PKS[code] == reference['registered_engine_pk']
                and str(engine.uuid) == reference['registered_engine_uuid']
                and reference['manufacturer_engine_code'] == code,
                f'Engine {code} differs from its approved registry reference.')
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
    for source, binding in source_rows:
        original = source['canonical_fields']
        require(all(original[k] == v for k, v in {
            'manufacturer': 'Jeep', 'vehicle_model': 'Wrangler', 'generation': 'JL',
            'model_year': 2026, 'market': 'US', 'drivetrain': '4WD',
        }.items()), 'Inventory row outside approved scope.')
        profile = source['engine_profile']
        engine = engines[profile]
        require(original['manufacturer_engine_code'] == engine.engine_code
                and source['registered_engine_pk'] == engine.pk
                and source['registered_engine_uuid'] == str(engine.uuid),
                'Inventory engine association conflicts with the existing registry.')
        resolve_engine(manufacturer, engine.engine_code,
                       incoming_powertrain={k: original[k] for k in FIELDS})
        body = bodies[original['factory_body_configuration']['door_configuration']]
        vehicle = prepare_registered_vehicle(
            manufacturer, engine.engine_code, generation=generation, model_year=2026,
            market='US', drivetrain='4WD', trim_name=original['trim_name'],
            factory_body_configuration=body,
        )
        powertrain = record_powertrain(engine)
        basis = baseline_preimage(scope=SCOPE, model_year=2026, trim_name=vehicle.trim_name,
            drivetrain='4WD', market='US', canonical_powertrain=powertrain,
            body_digest=semantic_digest(body_preimage(SCOPE, {'door_configuration': body.door_configuration})))
        identity = semantic_digest(basis)
        require(identity not in baselines, 'Duplicate canonical identity in inventory.')
        baselines.add(identity)
        rows.append({'inventory_id': source['inventory_id'], 'identity_digest': identity,
            'edmunds_style_ids': source['edmunds_style_ids'], 'source_urls': source['source_urls'],
            'source_fields': original, 'source_engine_code': source['source_engine_code'],
            'source_details': source, 'source_binding': binding | {
                'source_identity_type': source.get('source_identity_type', 'style_id'),
                'native_identifier': source.get('native_identifier', ','.join(source['edmunds_style_ids'])),
            }, 'baseline': basis, 'engine_code': engine.engine_code,
            'fields': {'model_year': 2026, 'trim_name': vehicle.trim_name,
                'engine_name': engine.name, 'engine_id': engine.pk,
                'factory_body_configuration_id': body.pk, 'market': 'US', 'drivetrain': '4WD',
                **powertrain}, 'legacy_base_slug': vehicle.build_slug(),
            'body_attributes': {k: getattr(body, k) for k in BODY_ATTRIBUTES},
            'candidate_reference': source['inventory_id']})
    slugs = family_slugs(rows)
    namespace = list(VehicleDefinition.objects.filter(generation=generation, model_year=2026)
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
        'supplement_sha256': SUPPLEMENT_SHA, 'source_artifacts': sources,
        'extraction_date': inventory['extraction_date'],
        'parents': [snapshot(manufacturer), snapshot(model), snapshot(generation)],
        'engines': {key: snapshot(value) for key, value in engines.items()},
        'bodies': {key: snapshot(value) for key, value in bodies.items()},
        'namespace': [snapshot(peer) for peer in namespace], 'rows': rows,
        'counts': {action: sum(r['action'] == action for r in rows) for action in ('create', 'skip', 'block')}}
    plan['plan_hash'] = digest(plan)
    return plan


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
            source_binding = row['source_binding']
            receipt = ImportExecutionReceipt.objects.create(
                operator_label=attribution.director, execution_channel='cli',
                manifest_hash=approved_hash, candidate_reference=row['inventory_id'],
                planned_action='create' if created else 'no_op_exact_match',
                create_basis='body_aware_identity' if created else '',
                source_id=source_binding['source_id'], raw_artifact_hash='sha256:' + source_binding['sha256'],
                raw_artifact_reference=source_binding['reference'],
                source_identity_type=source_binding['source_identity_type'],
                native_identifier=source_binding['native_identifier'],
                resolved_generation_id=generation.pk, target_slug=vehicle.slug,
                target_model_year=2026, target_trim_name=vehicle.trim_name,
                target_engine_name=vehicle.engine_name, target_drivetrain=vehicle.drivetrain,
                target_market=vehicle.market, target_fields_json=row['fields'],
                resolution_snapshot_json={'version': VERSION, 'execution_agent': attribution.agent,
                    'source_urls': row['source_urls'], 'extraction_date': source_binding['extraction_date'],
                    'row': row, 'parents': plan['parents'], 'engines': plan['engines'],
                    'bodies': plan['bodies'], 'plan_hash': approved_hash},
                execution_outcome=outcome, messages_json=['Exact preview revalidated; owner-authorized MY2026 registry mapping.'],
                **{prefix + '_vehicle_definition': vehicle,
                   prefix + '_vehicle_definition_pk_snapshot': vehicle.pk,
                   prefix + '_vehicle_definition_uuid_snapshot': str(vehicle.uuid),
                   prefix + '_vehicle_definition_slug_snapshot': vehicle.slug},
            )
            outcomes.append({'inventory_id': row['inventory_id'], 'outcome': outcome,
                'pk': vehicle.pk, 'uuid': str(vehicle.uuid), 'slug': vehicle.slug, 'receipt_pk': receipt.pk})
        return {'plan_hash': approved_hash, 'created': plan['counts']['create'],
                'skipped': plan['counts']['skip'], 'failed': 0, 'outcomes': outcomes}
