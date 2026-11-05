"""Exact-manifest specification/transmission publication; no baseline imports."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import IntegrityError, transaction
from reference.models import VehicleDefinition, GenerationCorrespondenceRevision
from .models import (
    publication_writes, SpecificationUnitRegistry, EvidenceDocument,
    EvidenceAssertionReference, SpecificationDefinition, SpecificationDefinitionRevision,
    SpecificationDefinitionDependency, SpecificationAssertion, SpecificationCatalogue,
    SpecificationCatalogueRevision, SpecificationCatalogueMembership,
    SpecificationCatalogueCoverage, SpecificationEvidenceLink, SpecificationPublicationReceipt,
    TransmissionDescription, TransmissionDescriptionRevision, TransmissionEngineeringAssertion,
    TransmissionOffering, TransmissionOfferingRevision,
    EquipmentItem, EquipmentItemRevision, EquipmentOffering, EquipmentOfferingRevision,
    CompatibilityRule, CompatibilityRuleRevision, MEMBERSHIP_TARGETS,
)
from .canonical import ContractError, canonical_bytes, content_hash, digest, loads, require, verify_hash, hash_string
from .artifacts import validate_manifest, publication_disposition, PublicationState
from .catalogue import record_ref
from .values import validate_unit_registry


MEMBER_MODELS = {
    'definition': SpecificationDefinitionRevision, 'specification_assertion': SpecificationAssertion,
    'transmission_description': TransmissionDescriptionRevision,
    'transmission_offering': TransmissionOfferingRevision,
    'equipment_item': EquipmentItemRevision,
    'equipment_offering': EquipmentOfferingRevision,
    'compatibility_rule': CompatibilityRuleRevision,
}
MEMBER_FIELDS = {kind: field for field, kind in MEMBERSHIP_TARGETS.items()}


class StalePublication(ContractError):
    """Reviewed live/evidence premises changed."""


class PublicationInfrastructureError(RuntimeError):
    """Publication/receipt storage failed; no success may be reported."""


class EvidenceStore:
    """Read only within an explicit authorized artifact root, including symlinks."""
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)

    def read(self, reference):
        path = (self.root / reference).resolve(strict=True)
        require(path.is_relative_to(self.root) and path.is_file(), 'Evidence reference escapes its authorized root')
        return path.read_bytes()


def _scope(manifest):
    d = manifest['draft']
    for item in d['catalogue']['members']:
        require(item['kind'] in MEMBER_MODELS, 'Feature mapping persistence remains outside B4')
    for key in ('body', 'series'):
        require(d['target']['identity'][key]['status'] == 'legacy_unassessed', 'Assessed body/series persistence is outside this milestone')
    require(all(v['kind'] in ('definition', 'transmission_description', 'transmission_offering', 'equipment_item', 'equipment_offering', 'compatibility_rule', 'evidence_document', 'evidence_assertion', 'unit_registry', 'generation_correspondence') for v in d['dependencies']), 'Dependency kind is outside this milestone')


def _ref(row):
    return {'uuid': str(row.uuid), 'content_hash': row.content_hash}


def _target(d, lock=False):
    query = VehicleDefinition.objects.select_related('generation__vehicle_model__manufacturer')
    if lock:
        query = query.select_for_update()
    vd = query.get(pk=d['target']['vehicle_definition_pk'], uuid=d['target']['vehicle_definition_uuid'])
    g, vm = vd.generation, vd.generation.vehicle_model
    m = vm.manufacturer
    require(vd.is_active and g.is_active and vm.is_active and m.is_active, 'Inactive canonical target/parent')
    parents = {
        'manufacturer': {'uuid': str(m.uuid), 'pk': m.pk, 'name': m.name, 'is_active': m.is_active},
        'vehicle_model': {'uuid': str(vm.uuid), 'pk': vm.pk, 'manufacturer_uuid': str(m.uuid), 'name': vm.name, 'is_active': vm.is_active},
        'generation': {'uuid': str(g.uuid), 'pk': g.pk, 'vehicle_model_uuid': str(vm.uuid), 'start_year': g.start_year, 'end_year': g.end_year, 'is_active': g.is_active},
    }
    identity = {'manufacturer_uuid': str(m.uuid), 'vehicle_model_uuid': str(vm.uuid), 'generation_uuid': str(g.uuid), 'model_year': vd.model_year, 'trim_name': vd.trim_name, 'engine_name': vd.engine_name, 'drivetrain': vd.drivetrain, 'market': vd.market, 'body': {'status': 'legacy_unassessed'}, 'series': {'status': 'legacy_unassessed'}}
    return vd, {'vehicle_definition_uuid': str(vd.uuid), 'vehicle_definition_pk': vd.pk, 'identity': identity, 'slug': vd.slug, 'parent_snapshot_hash': digest(parents)}, parents


def _current(vd):
    root = SpecificationCatalogue.objects.filter(vehicle_definition=vd).first()
    if root is None:
        return None
    leaves = list(root.revisions.filter(successor__isnull=True))
    require(len(leaves) == 1, 'Catalogue has no unique current leaf')
    row = leaves[0]
    expected = {(m['kind'], m['revision']['uuid'], m['revision']['content_hash']) for m in row.content['members']}
    actual = set()
    for link in row.memberships.select_related(*MEMBERSHIP_TARGETS):
        for field, kind in MEMBERSHIP_TARGETS.items():
            if getattr(link, field + '_id'):
                member = getattr(link, field)
                actual.add((kind, str(member.uuid), member.content_hash))
    require(expected == actual, 'Stored catalogue membership is incomplete/inconsistent')
    require({c.area: c.content for c in row.coverage_records.all()} == row.content['coverage'], 'Stored catalogue coverage is incomplete/inconsistent')
    return row


def _inputs(manifest, store):
    _scope(manifest)
    d = manifest['draft']
    records = {}
    for kind, model in MEMBER_MODELS.items():
        for row in model.objects.all():
            records[(kind, str(row.uuid))] = {'kind': kind, 'content': row.content}
    pred = d['catalogue']['supersedes']
    predecessor = None
    if pred:
        predecessor = SpecificationCatalogueRevision.objects.get(uuid=pred['uuid'], content_hash=pred['content_hash']).content
    new_doc_ids = {v['uuid'] for v in d['evidence_documents']}
    new_assertion_ids = {v['uuid'] for v in d['assertion_references']}
    # Exact immutable records supply the external references; no latest-member substitution.
    hashes = set()
    def scan(value):
        if type(value) is dict:
            for key, child in value.items():
                if type(child) is str and child.startswith('sha256:'):
                    hashes.add(child)
                scan(child)
        elif type(value) is list:
            for child in value:
                scan(child)
    scan(d)
    for p in d['proposed_members']:
        key = (p['member']['kind'], p['member']['revision']['uuid'])
        if key in records:
            scan(records[key])
    assertions = [r.content for r in EvidenceAssertionReference.objects.filter(content_hash__in=hashes).exclude(uuid__in=new_assertion_ids)]
    scan(assertions)
    documents = [r.content for r in EvidenceDocument.objects.filter(content_hash__in=hashes).exclude(uuid__in=new_doc_ids)]
    artifacts = {}
    def collect(value):
        if type(value) is dict:
            if set(value) == {'reference', 'content_hash'}:
                try:
                    raw = store.read(value['reference'])
                except OSError as exc:
                    raise StalePublication('Retained artifact is unavailable') from exc
                from .artifacts import byte_hash
                if byte_hash(raw) != value['content_hash']:
                    raise StalePublication('Retained artifact bytes changed')
                artifacts[value['reference']] = raw
            else:
                for child in value.values():
                    collect(child)
        elif type(value) is list:
            for child in value:
                collect(child)
    collect(d)
    collect(documents)
    collect(assertions)
    return {'artifacts': artifacts, 'existing_members': records, 'predecessor': predecessor,
            'external_documents': documents, 'external_assertions': assertions}


def _correspondences(vd, draft, inputs=None):
    refs = {v['revision']['uuid'] for v in draft['dependencies'] if v['kind'] == 'generation_correspondence'}
    if not refs:
        return
    from reference.ingestion.generation_correspondence import _applicable_revisions, digest as correspondence_digest
    rows = list(GenerationCorrespondenceRevision.objects.filter(uuid__in=refs))
    require(len(rows) == len(refs), 'Correspondence dependency missing')
    identities = [{k: getattr(row, k) for k in ('source_id', 'source_namespace', 'identity_type', 'native_identifier')} for row in rows]
    current = _applicable_revisions(vd.generation.vehicle_model, vd.model_year, vd.market, identities)
    require({str(row.uuid) for row in current} == refs, 'Relevant correspondence bindings changed')
    fields = {'trim_name': vd.trim_name, 'engine_name': vd.engine_name, 'drivetrain': vd.drivetrain}
    raw_hashes = {doc['raw_artifact']['content_hash'] for doc in [*draft['evidence_documents'], *(inputs or {}).get('external_documents', ())]}
    for row in current:
        require(row.finding == 'established' and row.generation_id == vd.generation_id and row.content_hash == correspondence_digest(row.review_payload()), 'Conflicting/withdrawn correspondence')
        require(all(fields.get(k) == v for k, v in row.restrictions.items()), 'Correspondence restrictions changed')
        require(all(e['raw_artifact_hash'] in raw_hashes for e in row.evidence), 'Correspondence source revisions are not bound')


def _revision_root(kind, content, vd, draft, inputs):
    logical_uuid = content['meta']['logical_uuid']
    if kind == 'definition':
        root = SpecificationDefinition.objects.filter(uuid=logical_uuid).first()
        require(root is None or root.key == content['key'], 'Property logical identity changed')
    elif kind == 'transmission_description':
        root = TransmissionDescription.objects.filter(uuid=logical_uuid).first()
        require(root is None or (str(root.manufacturer.uuid) == content['manufacturer_uuid'] and root.namespace == content['namespace'] and root.source_native_identity == content['source_native_identity']), 'Transmission hardware identity changed')
    elif kind == 'transmission_offering':
        root = TransmissionOffering.objects.filter(uuid=logical_uuid).first()
        description = inputs['existing_members'].get(('transmission_description', content['description']['uuid']))
        for p in draft['proposed_members']:
            if p['state'] == 'new' and p['member']['kind'] == 'transmission_description' and p['member']['revision'] == content['description']:
                description = p['payload']
        require(description is not None, 'Offering lacks exact description revision')
        require(root is None or (root.vehicle_definition_id == vd.pk and str(root.description.uuid) == description['content']['meta']['logical_uuid']), 'Transmission offering baseline/hardware identity changed')
    elif kind == 'equipment_item':
        root = EquipmentItem.objects.filter(uuid=logical_uuid).first()
        require(root is None or (str(root.manufacturer.uuid) == content['manufacturer_uuid'] and root.namespace == content['namespace'] and root.source_native_identity == content['source_native_identity']), 'Equipment hardware identity changed')
    elif kind == 'equipment_offering':
        root = EquipmentOffering.objects.filter(uuid=logical_uuid).first()
        item = inputs['existing_members'].get(('equipment_item', content['item']['uuid']))
        for p in draft['proposed_members']:
            if p['state'] == 'new' and p['member']['kind'] == 'equipment_item' and p['member']['revision'] == content['item']:
                item = p['payload']
        require(item is not None, 'Equipment offering lacks exact item revision')
        require(root is None or (root.vehicle_definition_id == vd.pk and str(root.item.uuid) == item['content']['meta']['logical_uuid']), 'Equipment offering baseline/item identity changed')
    elif kind == 'compatibility_rule':
        root = CompatibilityRule.objects.filter(uuid=logical_uuid).first()
        require(root is None or root.vehicle_definition_id == vd.pk, 'Compatibility rule baseline identity changed')
    return root


def _chain(row, kind):
    return getattr(row, {
        'definition': 'definition',
        'transmission_description': 'description',
        'transmission_offering': 'offering',
        'equipment_item': 'item',
        'equipment_offering': 'offering',
        'compatibility_rule': 'rule',
    }[kind])


def _state(manifest, vd, target, parents, inputs):
    d = manifest['draft']
    _correspondences(vd, d, inputs)
    current = _current(vd)
    successes = frozenset(SpecificationPublicationReceipt.objects.filter(catalogue_revision=current, outcome='published').values_list('manifest_hash', flat=True)) if current else frozenset()
    exact_replay = current is not None and current.content == d['catalogue'] and manifest['manifest_hash'] in successes
    new_revisions = {(p['member']['kind'], p['member']['revision']['uuid']): p['payload']['content'] for p in d['proposed_members'] if p['state'] == 'new' and p['member']['kind'] != 'specification_assertion'}
    dependencies = []
    for dep in d['dependencies']:
        observed = deepcopy(dep)
        kind, ref = dep['kind'], dep['revision']
        model = {**MEMBER_MODELS, 'evidence_document': EvidenceDocument, 'evidence_assertion': EvidenceAssertionReference, 'unit_registry': SpecificationUnitRegistry, 'generation_correspondence': GenerationCorrespondenceRevision}[kind]
        row = model.objects.filter(uuid=ref['uuid']).first()
        if (kind, ref['uuid']) in new_revisions:
            payload = new_revisions[(kind, ref['uuid'])]
            if row is not None:
                require(exact_replay and row.content == payload and not model.objects.filter(supersedes=row).exists(), 'Proposed member already exists or changed')
            else:
                chain = _revision_root(kind, payload, vd, d, inputs)
                leaf = chain.revisions.filter(successor__isnull=True).first() if chain else None
                require((_ref(leaf) if leaf else None) == dep['expected_leaf'], 'Definition chain became stale')
        elif row is None and kind in ('evidence_document', 'evidence_assertion', 'unit_registry'):
            proposed = d['evidence_documents'] if kind == 'evidence_document' else d['assertion_references']
            if kind == 'unit_registry':
                registry = loads(inputs['artifacts'][d['unit_registry']['reference']])
                require(ref['content_hash'] == registry['content_hash'] and dep['expected_leaf'] is None and not model.objects.filter(content_hash=ref['content_hash']).exists(), 'Registry dependency conflict')
            else:
                require(any(p['uuid'] == ref['uuid'] and p['content_hash'] == ref['content_hash'] for p in proposed) and dep['expected_leaf'] is None, 'Missing evidence dependency')
        else:
            require(row is not None and _ref(row) == ref, 'Missing/changed dependency')
            if kind in ('definition', 'transmission_description', 'transmission_offering', 'equipment_item', 'equipment_offering', 'compatibility_rule'):
                leaf = _chain(row, kind).revisions.get(successor__isnull=True)
                observed['expected_leaf'] = _ref(leaf)
                observed['finding'] = row.finding
            elif kind == 'generation_correspondence':
                leaf = row
                while GenerationCorrespondenceRevision.objects.filter(supersedes=leaf).exists():
                    leaf = GenerationCorrespondenceRevision.objects.get(supersedes=leaf)
                observed['expected_leaf'] = _ref(leaf)
                observed['finding'] = row.finding
                require(row.vehicle_model_id == vd.generation.vehicle_model_id and row.generation_id == vd.generation_id and row.market == vd.market and row.start_year <= vd.model_year <= row.end_year, 'Correspondence target/scope mismatch')
        dependencies.append(observed)
    for p in d['proposed_members']:
        if p['state'] != 'new':
            continue
        model = MEMBER_MODELS[p['member']['kind']]
        row = model.objects.filter(uuid=p['member']['revision']['uuid']).first()
        if row is not None:
            require(exact_replay and row.content == p['payload']['content'], 'Proposed new revision already exists')
            require(not model.objects.filter(supersedes=row).exists(), 'Published dependency was superseded')
        elif model is not SpecificationAssertion:
            c = p['payload']['content']
            root = _revision_root(p['member']['kind'], c, vd, d, inputs)
            if model is SpecificationDefinitionRevision:
                require(not SpecificationDefinition.objects.filter(key=c['key']).exclude(uuid=c['meta']['logical_uuid']).exists(), 'Property key already belongs to another identity')
            leaf = root.revisions.filter(successor__isnull=True).first() if root else None
            require((_ref(leaf) if leaf else None) == c['meta']['supersedes'], 'Member predecessor is not current')
        else:
            previous = p['payload']['content']['supersedes_assertion_uuid']
            require(previous is None or not SpecificationAssertion.objects.filter(supersedes__uuid=previous).exists(), 'Assertion predecessor already has a successor')
    # Existing assertions are immutable but a successor invalidates their current-use premise.
    for p in d['proposed_members']:
        if p['state'] == 'existing' and p['member']['kind'] == 'specification_assertion':
            require(not SpecificationAssertion.objects.filter(supersedes__uuid=p['member']['revision']['uuid']).exists(), 'Assertion was superseded')
    return PublicationState(target, parents, current.content if current else None, tuple(dependencies), successes, True)


def plan_publication(draft, *, artifact_root, authorization_scope):
    """Zero database writes, including parents, receipts and current pointers."""
    manifest = {'artifact_type': 'rigarchive.full_specifications_publication_manifest.v1', 'schema_version': '1.0.0', 'operation_type': 'specification_catalogue_publication', 'created_at': datetime.now(timezone.utc).isoformat(), 'draft': loads(canonical_bytes(draft)), 'draft_hash': draft['content_hash'], 'planned_outcome': 'publish', 'replay_policy': 'exact_current_only', 'authorization_scope': authorization_scope}
    manifest['manifest_hash'] = content_hash(manifest, 'manifest_hash')
    store = EvidenceStore(artifact_root)
    inputs = _inputs(manifest, store)
    validate_manifest(manifest, **inputs)
    vd, target, parents = _target(manifest['draft'])
    publication_disposition(manifest, _state(manifest, vd, target, parents, inputs), authorized_manifest_hash=manifest['manifest_hash'], **inputs)
    return loads(canonical_bytes(manifest))


def _existing_or_create(model, content, **fields):
    uid = content.get('uuid', content.get('assertion_uuid', content.get('meta', {}).get('revision_uuid')))
    row = model.objects.filter(uuid=uid).first()
    if row:
        require(row.content == content, 'Immutable record UUID/content conflict')
        return row
    return model.objects.create(uuid=uid, content=content, content_hash=content['content_hash'], **fields)


def _persist(manifest, vd, inputs):
    d = manifest['draft']
    registry_content = loads(inputs['artifacts'][d['unit_registry']['reference']])
    registry = SpecificationUnitRegistry.objects.filter(content_hash=registry_content['content_hash']).first()
    registry_deps = [v for v in d['dependencies'] if v['kind'] == 'unit_registry']
    if registry is None:
        fields = {'uuid': registry_deps[0]['revision']['uuid']} if registry_deps else {}
        registry = SpecificationUnitRegistry.objects.create(content=registry_content, content_hash=registry_content['content_hash'], artifact_reference=d['unit_registry']['reference'], artifact_hash=d['unit_registry']['content_hash'], **fields)
    else:
        require(registry.content == registry_content, 'Registry content conflict')
    for content in d['evidence_documents']:
        _existing_or_create(EvidenceDocument, content, source_id=content['source_id'], raw_artifact_hash=content['raw_artifact']['content_hash'])
    for content in d['assertion_references']:
        r = content['reference']
        doc = EvidenceDocument.objects.get(content_hash=r['document_reference_hash'])
        _existing_or_create(EvidenceAssertionReference, content, document=doc, **{k: r[k] for k in ('extractor_id', 'extractor_version', 'extraction_mode', 'assertion_set_id', 'local_assertion_id')})
    new = {p['member']['revision']['uuid']: p['payload']['content'] for p in d['proposed_members'] if p['state'] == 'new' and p['member']['kind'] == 'definition'}
    def definition(uid):
        row = SpecificationDefinitionRevision.objects.filter(uuid=uid).first()
        if row:
            require(uid not in new or row.content == new[uid], 'Definition UUID conflict')
            return row
        c = new[uid]
        for rule in c['qualifier_rules']:
            if rule['categorical_definition']:
                definition(rule['categorical_definition']['uuid'])
        root, _ = SpecificationDefinition.objects.get_or_create(uuid=c['meta']['logical_uuid'], defaults={'key': c['key']})
        require(root.key == c['key'], 'Definition logical identity conflict')
        previous = SpecificationDefinitionRevision.objects.get(uuid=c['meta']['supersedes']['uuid']) if c['meta']['supersedes'] else None
        row = _existing_or_create(SpecificationDefinitionRevision, c, definition=root, revision_number=c['meta']['revision_number'], supersedes=previous, finding=c['meta']['finding'])
        for rule in c['qualifier_rules']:
            if rule['categorical_definition']:
                SpecificationDefinitionDependency.objects.create(definition=row, qualifier_key=rule['key'], categorical_definition=definition(rule['categorical_definition']['uuid']))
        _links(row, 'definition_revision', [{'role': 'supports', 'reference': r} for r in c['evidence_refs']])
        return row
    for uid in new:
        definition(uid)
    for p in d['proposed_members']:
        if p['state'] == 'new' and p['member']['kind'] == 'specification_assertion':
            c = p['payload']['content']
            previous = SpecificationAssertion.objects.get(uuid=c['supersedes_assertion_uuid']) if c['supersedes_assertion_uuid'] else None
            existed = SpecificationAssertion.objects.filter(uuid=c['assertion_uuid']).exists()
            row = _existing_or_create(SpecificationAssertion, c, definition_revision=definition(c['definition_revision_uuid']), unit_registry=registry, supersedes=previous)
            if not existed:
                _links(row, 'assertion', c['evidence_links'])
    for p in d['proposed_members']:
        if p['state'] != 'new' or p['member']['kind'] != 'transmission_description':
            continue
        c = p['payload']['content']
        root, _ = TransmissionDescription.objects.get_or_create(uuid=c['meta']['logical_uuid'], defaults={'manufacturer': vd.generation.vehicle_model.manufacturer, 'namespace': c['namespace'], 'source_native_identity': c['source_native_identity']})
        previous = TransmissionDescriptionRevision.objects.get(uuid=c['meta']['supersedes']['uuid']) if c['meta']['supersedes'] else None
        row = _existing_or_create(TransmissionDescriptionRevision, c, description=root, revision_number=c['meta']['revision_number'], supersedes=previous, finding=c['meta']['finding'], designation=c['designation'], code=c['code'], transmission_type=c['type'], forward_speeds=c['forward_speeds'])
        for position, r in enumerate(c['engineering_assertions']):
            assertion = SpecificationAssertion.objects.get(uuid=r['uuid'], content_hash=r['content_hash'])
            TransmissionEngineeringAssertion.objects.create(description_revision=row, assertion=assertion, position=position)
        _links(row, 'transmission_description_revision', c['qualified']['evidence_links'])
    for p in d['proposed_members']:
        if p['state'] != 'new' or p['member']['kind'] != 'transmission_offering':
            continue
        c = p['payload']['content']
        description = TransmissionDescriptionRevision.objects.get(uuid=c['description']['uuid'], content_hash=c['description']['content_hash'])
        root, _ = TransmissionOffering.objects.get_or_create(uuid=c['meta']['logical_uuid'], defaults={'vehicle_definition': vd, 'description': description.description})
        previous = TransmissionOfferingRevision.objects.get(uuid=c['meta']['supersedes']['uuid']) if c['meta']['supersedes'] else None
        row = _existing_or_create(TransmissionOfferingRevision, c, offering=root, description_revision=description, revision_number=c['meta']['revision_number'], supersedes=previous, finding=c['meta']['finding'], availability=c['availability'])
        _links(row, 'transmission_offering_revision', c['qualified']['evidence_links'])
    for p in d['proposed_members']:
        if p['state'] != 'new' or p['member']['kind'] != 'equipment_item':
            continue
        c = p['payload']['content']
        root, _ = EquipmentItem.objects.get_or_create(uuid=c['meta']['logical_uuid'], defaults={'manufacturer': vd.generation.vehicle_model.manufacturer, 'namespace': c['namespace'], 'source_native_identity': c['source_native_identity']})
        previous = EquipmentItemRevision.objects.get(uuid=c['meta']['supersedes']['uuid']) if c['meta']['supersedes'] else None
        row = _existing_or_create(EquipmentItemRevision, c, item=root, revision_number=c['meta']['revision_number'], supersedes=previous, finding=c['meta']['finding'], name=c['name'], code=c['code'], kind=c['kind'], installation_channel=c['installation_channel'])
        _links(row, 'equipment_item_revision', c['qualified']['evidence_links'])
    for p in d['proposed_members']:
        if p['state'] != 'new' or p['member']['kind'] != 'equipment_offering':
            continue
        c = p['payload']['content']
        item = EquipmentItemRevision.objects.get(uuid=c['item']['uuid'], content_hash=c['item']['content_hash'])
        root, _ = EquipmentOffering.objects.get_or_create(uuid=c['meta']['logical_uuid'], defaults={'vehicle_definition': vd, 'item': item.item})
        previous = EquipmentOfferingRevision.objects.get(uuid=c['meta']['supersedes']['uuid']) if c['meta']['supersedes'] else None
        row = _existing_or_create(EquipmentOfferingRevision, c, offering=root, item_revision=item, revision_number=c['meta']['revision_number'], supersedes=previous, finding=c['meta']['finding'], assignment=c['assignment'])
        _links(row, 'equipment_offering_revision', c['qualified']['evidence_links'])
    for p in d['proposed_members']:
        if p['state'] != 'new' or p['member']['kind'] != 'compatibility_rule':
            continue
        c = p['payload']['content']
        root, _ = CompatibilityRule.objects.get_or_create(uuid=c['meta']['logical_uuid'], defaults={'vehicle_definition': vd})
        previous = CompatibilityRuleRevision.objects.get(uuid=c['meta']['supersedes']['uuid']) if c['meta']['supersedes'] else None
        row = _existing_or_create(CompatibilityRuleRevision, c, rule=root, revision_number=c['meta']['revision_number'], supersedes=previous, finding=c['meta']['finding'], rule_kind=c['rule']['kind'])
        _links(row, 'compatibility_rule_revision', c['qualified']['evidence_links'])
    c = d['catalogue']
    root, _ = SpecificationCatalogue.objects.get_or_create(vehicle_definition=vd, defaults={'uuid': c['logical_uuid']})
    require(str(root.uuid) == c['logical_uuid'], 'Catalogue logical identity conflict')
    previous = SpecificationCatalogueRevision.objects.get(uuid=c['supersedes']['uuid']) if c['supersedes'] else None
    row = SpecificationCatalogueRevision.objects.create(uuid=c['revision_uuid'], catalogue=root, revision_number=c['revision_number'], supersedes=previous, unit_registry=registry, finding=c['finding'], content=c, content_hash=c['content_hash'], manifest=manifest)
    for member in c['members']:
        field, model = MEMBER_FIELDS[member['kind']], MEMBER_MODELS[member['kind']]
        obj = model.objects.get(uuid=member['revision']['uuid'], content_hash=member['revision']['content_hash'])
        SpecificationCatalogueMembership.objects.create(catalogue_revision=row, **{field: obj})
    for area, content in c['coverage'].items():
        SpecificationCatalogueCoverage.objects.create(catalogue_revision=row, area=area, content=content)
    _links(row, 'catalogue_revision', [{'role': 'supports', 'reference': r} for r in c['evidence_refs']])
    return row


def _links(owner, field, links):
    for position, link in enumerate(links):
        r = link['reference']
        evidence = EvidenceAssertionReference.objects.get(content_hash=r['assertion_hash'])
        SpecificationEvidenceLink.objects.create(**{field: owner}, evidence=evidence, position=position, role=link['role'])


def _receipt(manifest, operator, outcome, revision=None, messages=()):
    return SpecificationPublicationReceipt.objects.create(operator_label=operator, manifest_hash=manifest['manifest_hash'], manifest_text=canonical_bytes(manifest).decode('utf-8'), outcome=outcome, catalogue_revision=revision, messages=list(messages))


def _success_receipt(manifest, operator, outcome, revision):
    try:
        return _receipt(manifest, operator, outcome, revision)
    except Exception as exc:
        raise PublicationInfrastructureError('Success receipt failed; publication transaction must roll back') from exc


def publish(manifest, *, artifact_root, authorized=False, authorized_manifest_hash, operator_label):
    """Execute only this exact authorized manifest; never re-plan or auto-retry."""
    require(authorized is True and operator_label.strip() and len(operator_label) <= 150, 'Explicit authorization and truthful operator required')
    hash_string(authorized_manifest_hash)
    require(manifest.get('manifest_hash') == authorized_manifest_hash, 'Authorization hash differs from selected manifest')
    frozen = loads(canonical_bytes(manifest))
    verify_hash(frozen, 'manifest_hash')
    store = EvidenceStore(artifact_root)
    stage = 'rejected'
    try:
        with transaction.atomic(), publication_writes():
            inputs = _inputs(frozen, store)
            validate_manifest(frozen, **inputs)
            stage = 'aborted_stale_plan'
            vd, target, parents = _target(frozen['draft'], lock=True)
            state = _state(frozen, vd, target, parents, inputs)
            outcome = publication_disposition(frozen, state, authorized_manifest_hash=authorized_manifest_hash, **inputs)
            if outcome == 'no_op_exact_match':
                revision = SpecificationCatalogueRevision.objects.get(uuid=frozen['draft']['catalogue']['revision_uuid'])
                receipt = _success_receipt(frozen, operator_label, outcome, revision)
            else:
                revision = _persist(frozen, vd, inputs)
                receipt = _success_receipt(frozen, operator_label, 'published', revision)
            return revision, receipt
    except (ContractError, ValidationError, ObjectDoesNotExist, IntegrityError, KeyError, TypeError, OSError) as exc:
        # Domain/constraint failures rolled back the whole publication. Attempt
        # audit is a separate transaction, so no rejected operation creates data.
        try:
            with transaction.atomic(), publication_writes():
                receipt = _receipt(frozen, operator_label, 'aborted_stale_plan' if isinstance(exc, (StalePublication, ObjectDoesNotExist, IntegrityError)) else stage, messages=(str(exc),))
        except Exception as audit_error:
            raise PublicationInfrastructureError('Publication rejected and attempt receipt could not be persisted') from audit_error
        return None, receipt
