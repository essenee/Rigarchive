"""Synthetic W2 contract fixtures only; no production vehicle/source assertions."""
import copy

from reference.specifications.canonical import canonical_bytes, content_hash, digest
from reference.specifications.artifacts import byte_hash
from reference.specifications.catalogue import record_ref, record_key


def uid(n):
    return f'00000000-0000-0000-0000-{n:012d}'


def seal(value, field='content_hash'):
    value[field] = content_hash(value, field)
    return value


def review(finding='established'):
    return dict(finding=finding, reviewer='synthetic test fixture; not production review', reviewed_at='2026-11-04T18:00:00+00:00', notes='synthetic')


def meta(n):
    return dict(logical_uuid=uid(n + 1000), revision_uuid=uid(n), revision_number=1, supersedes=None, finding='established', review=review())


def effective():
    return dict(status='established', production_start=None, production_end=None, order_start=None, order_end=None, notes='synthetic scope')


def location():
    return dict(page=1, section=None, table=None, row=None, column=None, paragraph=None, bounding_box=None, description='synthetic page')


def fixture():
    raw = b'SYNTHETIC manufacturer evidence: 123.40 mm; not a real publication'
    rawref = dict(reference='fixture/source.bin', content_hash=byte_hash(raw))
    document = seal(dict(uuid=uid(10), source_id='synthetic', raw_artifact=rawref, source_locator='https://example.invalid/synthetic', acquired_at='2026-11-04T18:00:00+00:00', acquisition_method='synthetic_fixture', media_type='application/octet-stream', byte_size=len(raw), publisher='synthetic', publication_kind='brochure', revision_status='established', publication_revision='synthetic1', publication_date=None, original_filename=None, native_publication_id=None, source_scope=dict(market='US', model_year_start=2018, model_year_end=2018, effective=effective(), notes='synthetic')))
    source = dict(envelope=dict(artifact_type='rigarchive.source_assertion_set.v1', schema_version='1.1.0'), provenance=dict(source_id='synthetic', native_record_id='set', extraction_provenance=dict(raw_artifact_hash=rawref['content_hash'], raw_artifact_reference=rawref['reference'], extractor_id='fixture', extractor_version='1', extraction_mode='synthetic_fixture')), source_assertions=[dict(assertion_id='a', attribute_key='dimension', raw_value='123.40')])
    source_bytes = canonical_bytes(source)
    source_ref = dict(reference='fixture/assertions.json', content_hash=byte_hash(source_bytes))
    assertion = seal(dict(uuid=uid(11), reference=dict(source_id='synthetic', document_hash=rawref['content_hash'], document_reference_hash=document['content_hash'], extractor_id='fixture', extractor_version='1', extraction_mode='synthetic_fixture', assertion_set_id='set', local_assertion_id='a'), attribute_key='dimension', original_value_text='123.40', location=location(), retained_assertion_artifact=source_ref))
    ev = assertion['reference'] | {'assertion_hash': assertion['content_hash']}
    registry = seal(dict(registry_version='synthetic1', units=[dict(token='mm', dimensional_family='length', name='millimetres', reference_unit=None, factor_numerator='1', factor_denominator='1', offset='0')], review=review()))
    registry_bytes = canonical_bytes(registry)
    registry_ref = dict(reference='fixture/units.json', content_hash=byte_hash(registry_bytes))
    definition = dict(kind='definition', content=seal(dict(meta=meta(20), key='dimensions.synthetic', name='synthetic dimension', category='dimensions', description='synthetic only', value_kind='quantity', dimensional_family='length', categorical_terms=[], qualifier_rules=[], component_rule='none', method_semantics='synthetic', sequence_rule=None, evidence_refs=[ev])))
    spec = dict(kind='specification_assertion', content=seal(dict(artifact_type='rigarchive.specification_assertion.v1', schema_version='1.0.0', assertion_uuid=uid(21), definition_revision_uuid=uid(20), definition_revision_hash=definition['content']['content_hash'], value=dict(status='reported', kind='quantity', amount='123.4', unit='mm'), original=dict(label='synthetic', value='123.40', unit='mm'), qualifiers=[], method=dict(status='unknown', reason='not established'), component=None, applicability=dict(language_version='1.0', predicate={'op': 'true'}), evidence_links=[dict(role='supports', reference=ev)], normalization=dict(method='parsed', rule_id='synthetic', rule_version='1', conversion=None, notes='original text retained'), reconciliation='single_source', review=review(), supersedes_assertion_uuid=None)))
    parents = dict(manufacturer=dict(uuid=uid(1), pk=1, name='Synthetic', is_active=True), vehicle_model=dict(uuid=uid(2), pk=2, manufacturer_uuid=uid(1), name='Synthetic', is_active=True), generation=dict(uuid=uid(3), pk=3, vehicle_model_uuid=uid(2), start_year=2000, end_year=None, is_active=True))
    target = dict(vehicle_definition_uuid=uid(4), vehicle_definition_pk=4, identity=dict(manufacturer_uuid=uid(1), vehicle_model_uuid=uid(2), generation_uuid=uid(3), model_year=2018, trim_name='Synthetic', engine_name='Synthetic', drivetrain='4WD', market='US', body={'status': 'legacy_unassessed'}, series={'status': 'legacy_unassessed'}), slug='synthetic-2018', parent_snapshot_hash=digest(parents))
    coverage = {k: dict(state='partial', declared_scope='synthetic only', universe=['synthetic'], evidence_refs=[ev], gaps=['other source content unextracted'], exclusions=[], review=review('unresolved')) for k in ['technical_specifications', 'transmission_offerings', 'equipment_offerings', 'compatibility']}
    docref = dict(uuid=document['uuid'], content_hash=document['content_hash'])
    corpus = dict(documents=[docref], expected_missing_sources=[], nodes=[dict(node_id='page1', parent_id=None, document=docref, location=location(), disposition='retained_pending_representation', assertion_refs=[ev], interpretation_ids=[], reason='partial extraction; synthetic')], review=review('unresolved'))
    catalogue = seal(dict(logical_uuid=uid(100), revision_uuid=uid(101), revision_number=1, supersedes=None, target_uuid=uid(4), finding='established', members=[], coverage=copy.deepcopy(coverage), corpus_hash=digest(corpus), evidence_refs=[ev], effective=effective(), review=review(), removals=[]))
    draft = dict(artifact_type='rigarchive.full_specifications_enrichment.v1', schema_version='1.0.0', draft_reference='synthetic-draft', target=target, parents=parents, evidence_documents=[document], assertion_references=[assertion], corpus_inventory=corpus, interpretations=[], proposed_members=[], catalogue=catalogue, expected_state={'state': 'absent'}, dependencies=[], unit_registry=registry_ref, predicate_version='1.0', review=review())
    records = [definition, spec]
    update_members(draft, records)
    artifacts = {rawref['reference']: raw, source_ref['reference']: source_bytes, registry_ref['reference']: registry_bytes}
    return draft, artifacts, records


def update_members(draft, records):
    refs = [dict(kind=r['kind'], revision=record_ref(r)) for r in sorted(records, key=record_key)]
    draft['catalogue']['members'] = refs
    draft['proposed_members'] = [dict(state='new', member=m, payload=copy.deepcopy(r)) for m, r in zip(refs, sorted(records, key=record_key))]
    seal(draft['catalogue']);seal(draft)


def manifest(draft):
    return seal(dict(artifact_type='rigarchive.full_specifications_publication_manifest.v1', schema_version='1.0.0', operation_type='specification_catalogue_publication', created_at='2026-11-04T18:00:00+00:00', draft=draft, draft_hash=draft['content_hash'], planned_outcome='publish', replay_policy='exact_current_only', authorization_scope='synthetic fixture, no actual authorization'), 'manifest_hash')


def qualified(ev):
    return dict(applicability=dict(language_version='1.0', predicate={'op': 'true'}), effective=effective(), evidence_links=[dict(role='supports', reference=ev)])


def transmission(draft, n=30):
    ev = draft['catalogue']['evidence_refs'][0]
    desc = dict(kind='transmission_description', content=seal(dict(meta=meta(n), manufacturer_uuid=uid(1), namespace='synthetic', source_native_identity=f'tx{n}', code=None, designation=f'synthetic transmission {n}', type_status='established', type='automatic', speed_count_status='established', forward_speeds=6, engineering_assertions=[], qualified=qualified(ev))))
    offer = dict(kind='transmission_offering', content=seal(dict(meta=meta(n + 1), target_uuid=uid(4), description=record_ref(desc), availability='optional', qualified=qualified(ev))))
    return [desc, offer]


def equipment(draft, n=40, kind='factory_option'):
    ev = draft['catalogue']['evidence_refs'][0]
    item = dict(kind='equipment_item', content=seal(dict(meta=meta(n), manufacturer_uuid=uid(1), namespace='synthetic', source_native_identity=f'option{n}', code=None, name=f'synthetic option {n}', description='synthetic', kind=kind, installation_channel='manufacturer_accessory' if kind == 'accessory' else 'factory', contents=[], qualified=qualified(ev))))
    offer = dict(kind='equipment_offering', content=seal(dict(meta=meta(n + 1), target_uuid=uid(4), item=record_ref(item), assignment='accessory_catalogue_only' if kind == 'accessory' else 'optional', policy=dict(brochure_document=dict(uuid=draft['evidence_documents'][0]['uuid'], content_hash=draft['evidence_documents'][0]['content_hash']), brochure_listed=True, manufacturer_identifies_package=False, exception_authorization=None, evidence_refs=[ev], finding='eligible', reason='synthetic brochure'), qualified=qualified(ev))))
    return [item, offer]


def rule(draft, body, n=60):
    return dict(kind='compatibility_rule', content=seal(dict(meta=meta(n), target_uuid=uid(4), rule=body, qualified=qualified(draft['catalogue']['evidence_refs'][0]))))


def operand(record):
    return dict(kind=record['kind'], revision=record_ref(record))
