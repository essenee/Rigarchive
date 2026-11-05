"""Pure W2 enrichment/publication validation against explicit in-memory inputs.

No filesystem resolver, ORM, authorization execution or publication is provided.
Byte and state inputs must be supplied by a future separately authorized boundary.
"""
from dataclasses import dataclass
import hashlib
import json

from .canonical import (
    array, canonical_bytes, content_hash, digest, enum, hash_string, obj, require,
    text, utc_time, verify_hash, ContractError,
)
from . import schemas as s
from .catalogue import record_key, record_ref, validate_snapshot
from .values import validate_unit_registry


def byte_hash(raw):
    require(type(raw) is bytes, 'Original artifact bytes required')
    return 'sha256:' + hashlib.sha256(raw).hexdigest()


def artifact_bytes(reference, artifacts):
    s.artifact_ref(reference)
    raw = artifacts.get(reference['reference'])
    require(raw is not None and byte_hash(raw) == reference['content_hash'], 'Missing/changed retained artifact bytes')
    return raw


def _legacy_assertion_binding(assertion, artifacts):
    """Read existing SourceAssertionSet bytes without rehashing normalized content.

    JSON floating-point lexemes are read as strings, not binary floats. This does
    not rewrite the legacy payload or change its historical byte identity.
    """
    raw = artifact_bytes(assertion['retained_assertion_artifact'], artifacts)
    def pairs(items):
        result = {}
        for k, v in items:
            require(k not in result, 'Duplicate retained assertion JSON key')
            result[k] = v
        return result
    class NumberLexeme(str):
        pass
    def legacy_text(value):
        if isinstance(value, NumberLexeme):
            return str(value)
        if type(value) is dict:
            return '{' + ','.join(json.dumps(k, ensure_ascii=False) + ':' + legacy_text(v) for k, v in sorted(value.items())) + '}'
        if type(value) is list:
            return '[' + ','.join(legacy_text(v) for v in value) + ']'
        return json.dumps(value, ensure_ascii=False)
    try:
        retained = json.loads(raw, parse_float=NumberLexeme, parse_constant=lambda v: (_ for _ in ()).throw(ContractError('Nonfinite source JSON')), object_pairs_hook=pairs)
        provenance = retained['provenance']
        extraction = provenance['extraction_provenance']
        key = assertion['reference']
        require(retained['envelope']['artifact_type'] == 'rigarchive.source_assertion_set.v1' and retained['envelope']['schema_version'] in ('1.0.0', '1.1.0'), 'Unsupported retained assertion artifact/version')
        require(provenance['source_id'] == key['source_id'], 'Retained source identity mismatch')
        set_id = retained.get('assertion_set_id', provenance.get('native_record_id'))
        require(set_id == key['assertion_set_id'], 'Retained assertion set mismatch')
        for field in ('extractor_id', 'extractor_version', 'extraction_mode'):
            require(extraction[field] == key[field], 'Retained extraction identity mismatch')
        require(extraction['raw_artifact_hash'] == key['document_hash'], 'Retained document hash mismatch')
        matches = [a for a in retained['source_assertions'] if a['assertion_id'] == key['local_assertion_id']]
        require(len(matches) == 1, 'Retained assertion missing/ambiguous')
        source = matches[0]
        require(source['attribute_key'] == assertion['attribute_key'], 'Retained assertion key mismatch')
        raw_value = source['raw_value']
        if isinstance(raw_value, NumberLexeme):
            displayed = str(raw_value)
        elif type(raw_value) in (str, int, bool) or raw_value is None:
            # String source wording and numeric lexical forms remain separate
            # from W2 normalized values. Structured values remain source JSON.
            displayed = raw_value if type(raw_value) is str else json.dumps(raw_value, ensure_ascii=False)
        else:
            displayed = legacy_text(raw_value)
        require(displayed == assertion['original_value_text'], 'Retained original assertion value mismatch')
    except (KeyError, TypeError, ValueError, UnicodeError) as exc:
        raise ContractError(f'Unverifiable retained assertion binding: {exc}') from exc


def proposed_member(value):
    require(type(value) is dict, 'Proposed member object required')
    fields = {'state': enum('existing'), 'member': s.member_ref}
    if value.get('state') == 'new':
        fields = {'state': enum('new'), 'member': s.member_ref, 'payload': s.member}
    obj(value, fields)
    if value['state'] == 'new':
        require(value['payload']['kind'] == value['member']['kind'] and record_ref(value['payload']) == value['member']['revision'], 'Proposed member identity/hash mismatch')


def validate_enrichment(draft, *, artifacts, existing_members=None, predecessor=None,
                        feature_states=None, external_documents=(), external_assertions=()):
    """Validate an exact draft without resolving latest state or performing I/O."""
    obj(draft, {
        'artifact_type': enum('rigarchive.full_specifications_enrichment.v1'), 'schema_version': enum('1.0.0'),
        'draft_reference': text, 'target': s.target, 'parents': s.parents,
        'evidence_documents': array(s.document, key=lambda v: v['uuid'], ordered=True),
        'assertion_references': array(s.evidence_assertion, key=lambda v: v['uuid'], ordered=True),
        'corpus_inventory': s.corpus, 'interpretations': array(s.interpretation, key=lambda v: v['interpretation_id'], ordered=True),
        'proposed_members': array(proposed_member, key=lambda v: s.member_key(v['member']), ordered=True),
        'catalogue': s.catalogue, 'expected_state': s.expected,
        'dependencies': array(s.dependency, key=lambda v: (v['kind'], v['revision']['uuid']), ordered=True),
        'unit_registry': s.artifact_ref, 'predicate_version': enum('1.0'), 'review': s.review, 'content_hash': hash_string,
    })
    verify_hash(draft)
    from .canonical import loads
    registry = loads(artifact_bytes(draft['unit_registry'], artifacts))
    units = validate_unit_registry(registry)
    require(registry['review']['finding'] == 'established', 'Unit registry is not established')
    target, parents = draft['target'], draft['parents']
    identity = target['identity']
    require(target['parent_snapshot_hash'] == digest(parents), 'Parent snapshot hash mismatch')
    for name in ('manufacturer', 'vehicle_model', 'generation'):
        require(identity[name + '_uuid'] == parents[name]['uuid'], 'Target parent UUID mismatch')
    generation = parents['generation']
    require(generation['start_year'] <= identity['model_year'] and (generation['end_year'] is None or identity['model_year'] <= generation['end_year']), 'Target year out of Generation')
    catalogue = draft['catalogue']
    require(catalogue['target_uuid'] == target['vehicle_definition_uuid'], 'Catalogue target mismatch')
    require(catalogue['corpus_hash'] == digest(draft['corpus_inventory']), 'Corpus inventory hash mismatch')
    records = {}
    for item in draft['proposed_members']:
        key = s.member_key(item['member'])
        record = item.get('payload') if item['state'] == 'new' else (existing_members or {}).get(key)
        require(record is not None and record_key(record) == key and record_ref(record) == item['member']['revision'], 'Missing exact existing/proposed member')
        records[key] = record
    offerings = validate_snapshot(catalogue, records, units, predecessor=predecessor, feature_states=feature_states)
    expected = draft['expected_state']
    if expected['state'] == 'absent':
        require(catalogue['revision_number'] == 1 and predecessor is None, 'Expected-absence lineage mismatch')
    else:
        require(predecessor is not None and expected['catalogue'] == {'uuid': predecessor['revision_uuid'], 'content_hash': predecessor['content_hash']} and expected['logical_uuid'] == predecessor['logical_uuid'] and expected['revision_number'] == predecessor['revision_number'], 'Expected predecessor differs')
    documents = {}
    for document in (*external_documents, *draft['evidence_documents']):
        s.document(document)
        key = (document['uuid'], document['content_hash'])
        require(key not in documents, 'Duplicate evidence document identity')
        documents[key] = document
        raw = artifact_bytes(document['raw_artifact'], artifacts)
        require(len(raw) == document['byte_size'], 'Retained document size mismatch')
    doc_hashes = {d['content_hash']: d for d in documents.values()}
    require(len(doc_hashes) == len(documents), 'Ambiguous document acquisition digest')
    assertions = {}
    for assertion in (*external_assertions, *draft['assertion_references']):
        s.evidence_assertion(assertion)
        key = assertion['reference']
        doc = doc_hashes.get(key['document_reference_hash'])
        require(doc is not None and doc['source_id'] == key['source_id'] and doc['raw_artifact']['content_hash'] == key['document_hash'], 'Evidence document binding mismatch')
        _legacy_assertion_binding(assertion, artifacts)
        reference = key | {'assertion_hash': assertion['content_hash']}
        refkey = canonical_bytes(reference)
        require(refkey not in assertions, 'Duplicate qualified assertion identity')
        assertions[refkey] = assertion
    def verify_evidence(value):
        if type(value) is dict:
            if set(value) == set(s.EVIDENCE_FIELDS):
                require(canonical_bytes(value) in assertions, 'Unresolved exact assertion reference')
                return
            for child in value.values():
                verify_evidence(child)
        elif type(value) is list:
            for child in value:
                verify_evidence(child)
    verify_evidence(draft)
    for record in records.values():
        verify_evidence(record)
        c = record['content']
        finding = c['review']['finding'] if record['kind'] == 'specification_assertion' else c['meta']['finding']
        links = c.get('evidence_links', c.get('qualified', {}).get('evidence_links', []))
        if finding == 'established':
            for link in links:
                if link['role'] != 'supports':
                    continue
                doc = doc_hashes[link['reference']['document_reference_hash']]
                scope = doc['source_scope']
                require(scope['market'] is None or scope['market'] == identity['market'], 'Established fact contradicts source market')
                require(scope['model_year_start'] is None or scope['model_year_start'] <= identity['model_year'], 'Established fact precedes source year scope')
                require(scope['model_year_end'] is None or scope['model_year_end'] >= identity['model_year'], 'Established fact exceeds source year scope')
        if c.get('manufacturer_uuid') is not None:
            require(c['manufacturer_uuid'] == identity['manufacturer_uuid'], 'Foreign manufacturer member')
        if record['kind'] == 'equipment_offering':
            p = c['policy']
            if p['brochure_document'] is not None:
                require((p['brochure_document']['uuid'], p['brochure_document']['content_hash']) in documents, 'Missing applicable brochure')
            if p['exception_authorization'] is not None:
                artifact_bytes(p['exception_authorization'], artifacts)
    interpretation_ids = {v['interpretation_id'] for v in draft['interpretations']}
    for reference in draft['corpus_inventory']['documents']:
        require((reference['uuid'], reference['content_hash']) in documents, 'Missing corpus document')
    for node in draft['corpus_inventory']['nodes']:
        require((node['document']['uuid'], node['document']['content_hash']) in documents, 'Missing inventory document')
        require(set(node['interpretation_ids']) <= interpretation_ids, 'Unknown inventory interpretation')
    for interpretation in draft['interpretations']:
        from .predicates import validate_predicate
        # Bound predicate references against the same exact validated snapshot.
        validate_predicate(interpretation['applicability']['predicate'], offerings, feature_states or {})
    deps = {(v['kind'], v['revision']['uuid']): v for v in draft['dependencies']}
    for key, dep in deps.items():
        if key in records:
            require(record_ref(records[key]) == dep['revision'], 'Dependency member hash mismatch')
        elif dep['kind'] in s.KINDS:
            require(False, 'Hidden nonmember catalogue dependency')
    for item in draft['proposed_members']:
        key = s.member_key(item['member'])
        record = records[key]
        if item['state'] == 'existing' and key[0] != 'specification_assertion':
            require(key in deps and deps[key]['expected_leaf'] is not None, 'Existing member requires pinned live dependency state')
        if item['state'] == 'new':
            c = record['content']
            pred = c.get('supersedes_assertion_uuid') if key[0] == 'specification_assertion' else c['meta']['supersedes']
            if pred is not None:
                pred_id = pred if type(pred) is str else pred['uuid']
                previous = (existing_members or {}).get((key[0], pred_id))
                require(previous is not None, 'Member successor requires exact predecessor record')
                s.member(previous)
                if key[0] != 'specification_assertion':
                    require(record_ref(previous) == pred and previous['content']['meta']['logical_uuid'] == c['meta']['logical_uuid'] and previous['content']['meta']['revision_number'] + 1 == c['meta']['revision_number'], 'Member predecessor lineage mismatch')
                    require(key in deps and deps[key]['expected_leaf'] == pred, 'Member successor missing expected leaf')
    for name in ('body', 'series'):
        binding = identity[name]
        if binding['status'] == 'established':
            for kind, reference in [(name + '_identity', binding['identity']), (name + '_binding', binding['evidence_binding'])]:
                dep = deps.get((kind, reference['uuid']))
                require(dep is not None and dep['revision'] == reference and dep['finding'] == 'established', 'Missing/stale assessed identity dependency')
    return records


def validate_manifest(manifest, **inputs):
    obj(manifest, {
        'artifact_type': enum('rigarchive.full_specifications_publication_manifest.v1'), 'schema_version': enum('1.0.0'),
        'operation_type': enum('specification_catalogue_publication'), 'created_at': utc_time,
        'draft': lambda v: validate_enrichment(v, **inputs), 'draft_hash': hash_string,
        'planned_outcome': enum('publish'), 'replay_policy': enum('exact_current_only'),
        'authorization_scope': text, 'manifest_hash': hash_string,
    })
    verify_hash(manifest, 'manifest_hash')
    require(manifest['draft_hash'] == manifest['draft']['content_hash'], 'Manifest draft hash mismatch')


@dataclass(frozen=True)
class PublicationState:
    """Explicit caller snapshot, not an ORM/latest-member resolver or permission."""
    target: dict
    parents: dict
    current_catalogue: dict | None
    dependencies: tuple
    successful_manifest_hashes: frozenset
    relevant_bindings_unchanged: bool


def publication_disposition(manifest, state, *, authorized_manifest_hash, **inputs):
    """Pure exact-current replay/staleness decision. Never writes or authorizes."""
    validate_manifest(manifest, **inputs)
    require(authorized_manifest_hash == manifest['manifest_hash'], 'Exact manifest authorization binding mismatch')
    d = manifest['draft']
    require(state.target == d['target'] and state.parents == d['parents'] and state.relevant_bindings_unchanged is True, 'Stale target/parent/binding state')
    require(list(state.dependencies) == d['dependencies'], 'Stale relevant dependency state')
    current, proposed = state.current_catalogue, d['catalogue']
    if current is not None:
        s.catalogue(current)
        if current['revision_uuid'] == proposed['revision_uuid']:
            require(current == proposed and current['finding'] != 'withdrawn' and manifest['manifest_hash'] in state.successful_manifest_hashes, 'Stale/withdrawn/unproven replay')
            return 'no_op_exact_match'
    expected = d['expected_state']
    if expected['state'] == 'absent':
        require(current is None, 'Stale expected catalogue absence')
    else:
        require(current is not None and {'uuid': current['revision_uuid'], 'content_hash': current['content_hash']} == expected['catalogue'], 'Stale expected catalogue leaf')
    require(proposed['revision_uuid'] not in {c['revision']['uuid'] for c in state.dependencies}, 'Revision identity already used')
    return 'publish'
