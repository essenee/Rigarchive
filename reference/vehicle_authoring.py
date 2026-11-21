"""Atomic, human-directed ORM authoring with current body/Engine meaning.

This is not an adapter for historical Candidate/Matrix contracts. Those closed
formats continue to reject unsupported pickup dimensions and Engine variants.
Callers retain reviewed observations, obtain scoped owner authorization and back
up the database before invoking this write operation.
"""
import hashlib
import json
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

from reference.body_identity import (
    authoring_body_dimensions, authoring_configuration_key, canonical_json, has_implicit_factory_body,
)
from reference.models import Engine, FactoryBodyConfiguration, ImportExecutionReceipt, VehicleDefinition
from reference.powertrain import FIELDS, record_powertrain
from reference.transmission import normalize_source_transmission, transmission_identity


def _require(condition, message):
    if not condition:
        raise ValidationError(message)


def _overlaps(left, right):
    """Unknown legacy discriminators cannot establish distinct active identities."""
    if any(getattr(left, f) != getattr(right, f) for f in
           ('generation_id', 'model_year', 'market', 'trim_name', 'drivetrain')):
        return False
    if (left.transmission and right.transmission
            and transmission_identity(left.transmission) != transmission_identity(right.transmission)):
        return False
    a, b = record_powertrain(left), record_powertrain(right)
    if any(a[f] is not None and b[f] is not None and a[f] != b[f] for f in FIELDS):
        return False
    a = authoring_body_dimensions(left.factory_body_configuration) or {}
    b = authoring_body_dimensions(right.factory_body_configuration) or {}
    return not any(a.get(f) is not None and b.get(f) is not None and a[f] != b[f]
                   for f in a.keys() | b.keys())


def reviewed_transmission_manifest(rows, *, evidence_hash, authorization, lock=False):
    """Bind exact authoring scope and peers for the transmission-aware receipt contract."""
    vehicles = []
    scopes = {}
    for proposal, pk in rows:
        key = (proposal.generation_id, proposal.model_year, proposal.market)
        scopes[key] = None
        vehicles.append({"identity": authoring_configuration_key(proposal), "reuse_pk": pk,
                         "engine_uuid": str(proposal.engine.uuid) if proposal.engine_id else None,
                         "body_uuid": (str(proposal.factory_body_configuration.uuid)
                                       if proposal.factory_body_configuration_id else None),
                         "slug": proposal.build_slug() if pk is None else None,
                         "is_public": proposal.is_public})
    for key in sorted(scopes):
        generation, year, market = key
        peers = VehicleDefinition.objects.filter(generation_id=generation, model_year=year, market=market)
        if lock:
            peers = peers.select_for_update()
        scopes[key] = list(peers.order_by("pk").values(
            "pk", "uuid", "slug", "trim_name", "drivetrain", "transmission", "is_active",
            "is_public", "base_msrp", "factory_body_configuration_id", "engine_id", "engine_name", *FIELDS,
        ))
    payload = {
        "profile": "human-body-authoring/2", "observations": evidence_hash, "authorization": authorization,
        "rows": vehicles, "scopes": [{"scope": key, "peers": peers} for key, peers in sorted(scopes.items())],
    }
    # UUID and Decimal scalar snapshots are serialized as their exact string representations.
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return {**json.loads(raw), "manifest_hash": "sha256:" + hashlib.sha256(raw.encode()).hexdigest()}


@transaction.atomic
def author_configurations(rows, *, evidence_reference, evidence_hash, authorization, operator_label,
                          approved_manifest_hash=None):
    """Create/reuse exactly reviewed rows, recording compact receipts atomically.

    rows: (unsaved proposed VehicleDefinition, optional existing PK) pairs. Reuse
    may only activate a fully matching existing identity; no other field changes.
    Evidence is a retained human observation record, never mislabelled raw OEM bytes.
    Engine option pins permit a collapsed transmission family without inventing a
    single output association. Every option must share the full five-field tuple.
    """
    rows = list(rows)
    _require(bool(rows) and bool(authorization.strip()) and bool(operator_label.strip()),
             'Exact rows, owner authorization and operator are required.')
    root = Path(settings.BASE_DIR).resolve()
    path = (root / evidence_reference).resolve()
    _require(path.is_relative_to(root) and path.is_file(), 'Retained observation record is unavailable.')
    raw = path.read_bytes()
    digest = 'sha256:' + hashlib.sha256(raw).hexdigest()
    _require(digest == evidence_hash, 'Reviewed observations changed.')
    evidence = json.loads(raw)
    _require(evidence.get('record_type') == 'human-reviewed-factory-observations',
             'Evidence must distinguish observations from manufacturer document bytes.')
    observations = {r['identity']: r for r in evidence['configurations']}
    keys = [authoring_configuration_key(v) for v, _ in rows]
    _require(len(set(keys)) == len(keys) == len(observations)
             and set(keys) == set(observations), 'Reviewed scope differs or contains duplicates.')
    for i, (left, _) in enumerate(rows):
        _require(not any(_overlaps(left, right) for right, _ in rows[i + 1:]),
                 'Reviewed rows contain ambiguous overlapping identities.')
    manifest_hash = 'sha256:' + hashlib.sha256(canonical_json({
        'observations': digest, 'authorization': authorization,
        'rows': [{'identity': key, 'reuse_pk': pk} for key, (_, pk) in zip(keys, rows)],
    }).encode()).hexdigest()
    if any(v.transmission for v, _ in rows):
        review = reviewed_transmission_manifest(rows, evidence_hash=digest, authorization=authorization, lock=True)
        _require(approved_manifest_hash == review["manifest_hash"], 'Transmission authoring manifest is stale or not approved.')
        manifest_hash = review["manifest_hash"]
    prepared = []
    b3_evidence = {}
    # Validate the entire set before the first write; rollback covers every receipt.
    for key, (proposed, reuse_pk) in zip(keys, rows):
        _require(proposed._state.adding and proposed.pk is None and proposed.is_active,
                 'Expected an unsaved active proposal.')
        if proposed.factory_body_configuration_id:
            body = FactoryBodyConfiguration.objects.select_for_update().select_related('bed_length').get(
                pk=proposed.factory_body_configuration_id)
            _require(body.generation_id == proposed.generation_id and
                     authoring_body_dimensions(body) == authoring_body_dimensions(proposed.factory_body_configuration),
                     'Body parent changed or belongs to another Generation.')
            body.full_clean()
            proposed.factory_body_configuration = body
        else:
            _require(has_implicit_factory_body(proposed.generation)
                     and not FactoryBodyConfiguration.objects.filter(generation=proposed.generation).exists(),
                     'This Generation requires a reviewed body parent.')
        observation = observations[key]
        _require(proposed.engine_name == observation['engine_name'] and
                 (str(proposed.base_msrp) if proposed.base_msrp is not None else None) == observation['base_msrp'],
                 'Reviewed presentation name or price differs.')
        if proposed.transmission:
            offer = observation.get('selected_toyota_model') or {}
            proof = observation.get('transmission_evidence') or {}
            if proof.get("working_revision"):
                from reference.configuration_logic_google import read_registry
                from reference.configuration_logic_authoring import prepare_b3_authoring
                generation = str(proposed.generation.uuid)
                registry = read_registry(root / ".configuration-logic" / f"{generation}.json", generation)
                _require(registry and registry.get("working_revision") == proof["working_revision"],
                         "B3 working revision changed after review.")
                source_path = (root / proof["reference"]).resolve()
                _require(source_path.is_relative_to(root) and source_path.is_file() and
                         "sha256:" + hashlib.sha256(source_path.read_bytes()).hexdigest() == proof["sha256"],
                         "B3 source evidence changed after review.")
                source_key = (generation, proposed.model_year, proof["reference"], proof["sha256"])
                if source_key not in b3_evidence:
                    _, reviewed = prepare_b3_authoring(proposed.generation, proposed.model_year,
                                                       proof["reference"], proof["sha256"])
                    b3_evidence[source_key] = {item["identity"]: item for item in reviewed["configurations"]}
                _require(b3_evidence[source_key].get(key) == observation,
                         "Reviewed transmission observation differs from the registered B3 offer.")
            _require(normalize_source_transmission(offer.get('transmission')) == transmission_identity(proposed.transmission)
                     and bool(offer.get('code')) and proposed.engine_id is not None
                     and offer.get('variant') == proposed.engine.internal_variant_key
                     and bool(proof),
                     'Reviewed factory transmission and exact Engine evidence are required.')
        engines = []
        for pin in observation['engine_options']:
            engine = Engine.objects.select_for_update().get(pk=pin['pk'], uuid=pin['uuid'])
            _require(engine.engine_code == pin['engine_code'] and
                     engine.internal_variant_key == pin['internal_variant_key'] and
                     engine.name == pin['name'] and record_powertrain(engine) == pin['powertrain'],
                     'Reviewed Engine state changed.')
            _require(Engine.objects.available_for_manufacturer(
                proposed.generation.vehicle_model.manufacturer_id).filter(pk=engine.pk).exists(),
                'Engine is unavailable for this manufacturer.')
            _require(record_powertrain(engine) == record_powertrain(proposed), 'Conflicting Engine output family.')
            engines.append(engine)
        _require(bool(engines) and len({e.pk for e in engines}) == len(engines), 'Missing/duplicate Engine options.')
        _require(proposed.engine_id == (engines[0].pk if len(engines) == 1 else None),
                 'Multiple output variants cannot be forced into one Engine association.')
        proposed._validate_registry_engine()
        existing = None
        if reuse_pk is not None:
            existing = VehicleDefinition.objects.select_for_update().select_related(
                'generation', 'factory_body_configuration__bed_length').get(pk=reuse_pk)
            _require(authoring_configuration_key(existing) == key and
                     existing.engine_id == proposed.engine_id and existing.engine_name == proposed.engine_name and
                     existing.base_msrp == proposed.base_msrp and existing.is_public == proposed.is_public,
                     'Existing row is not an exact reusable configuration.')
            proposed.slug = existing.slug  # Never regenerate a valid historical URL.
        else:
            _require(not proposed.slug, 'New authoring must derive its deterministic slug.')
            proposed.slug = proposed.build_slug()
        for peer in VehicleDefinition.objects.select_for_update().filter(
                generation_id=proposed.generation_id, model_year=proposed.model_year, is_active=True
                ).select_related('factory_body_configuration__bed_length'):
            _require(peer.pk == reuse_pk or not _overlaps(peer, proposed),
                     'An active exact or ambiguous legacy identity overlaps this proposal.')
        proposed.full_clean(validate_unique=existing is None, validate_constraints=existing is None)
        prepared.append((proposed, existing, key))
    results = []
    for proposed, existing, key in prepared:
        if existing:
            vehicle = existing
            outcome = 'no_op' if vehicle.is_active else 'reactivated'
            if not vehicle.is_active:
                vehicle.is_active = True
                vehicle.save(update_fields=['is_active'])
        else:
            vehicle = proposed
            vehicle.save(force_insert=True)
            outcome = 'created'
        fields = json.loads(key)
        snapshot = {'profile': 'human-body-authoring/2' if vehicle.transmission else 'human-body-authoring/1',
                    'identity': fields,
                    'evidence_reference': evidence_reference, 'evidence_hash': digest,
                    'observation': observations[key], 'authorization': authorization,
                    'engine_uuid': str(vehicle.engine.uuid) if vehicle.engine_id else None,
                    'outcome': outcome, 'vehicle_uuid': str(vehicle.uuid), 'slug': vehicle.slug}
        snapshot['snapshot_hash'] = 'sha256:' + hashlib.sha256(canonical_json(snapshot).encode()).hexdigest()
        prefix = 'created' if outcome == 'created' else 'existing'
        receipt = ImportExecutionReceipt(
            operator_label=operator_label, execution_channel='cli', manifest_hash=manifest_hash,
            candidate_reference='human-authoring:' + str(vehicle.uuid), planned_action='create' if not existing else 'reuse',
            create_basis='reviewed_factory_configuration', source_id='human-reviewed-observations',
            raw_artifact_hash=digest, raw_artifact_reference=evidence_reference,
            source_identity_type='model_code' if vehicle.transmission else 'reviewed_observation',
            native_identifier=(observations[key]['selected_toyota_model']['code']
                               if vehicle.transmission else str(vehicle.uuid)),
            resolved_generation_id=vehicle.generation_id, target_slug=vehicle.slug,
            target_model_year=vehicle.model_year, target_trim_name=vehicle.trim_name,
            target_engine_name=vehicle.engine_name, target_drivetrain=vehicle.drivetrain,
            target_market=vehicle.market, target_fields_json=fields, execution_outcome=outcome,
            messages_json=[{'code': 'OWNER_AUTHORIZED', 'message': authorization}],
            resolution_snapshot_json=snapshot,
            **{prefix + '_vehicle_definition': vehicle,
               prefix + '_vehicle_definition_pk_snapshot': vehicle.pk,
               prefix + '_vehicle_definition_uuid_snapshot': str(vehicle.uuid),
               prefix + '_vehicle_definition_slug_snapshot': vehicle.slug})
        receipt.full_clean()
        receipt.save(force_insert=True)
        results.append((vehicle, receipt))
    return results
