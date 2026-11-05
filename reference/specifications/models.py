"""Append-only persistence for approved W2 specification contracts (B2)."""
from contextlib import contextmanager
from contextvars import ContextVar
from django.core.exceptions import ValidationError
from django.db import models
from core.models import BaseModel
from reference.models import VehicleDefinition, Manufacturer
from . import schemas as s
from .canonical import ContractError
from .values import validate_assertion, validate_unit_registry, validate_value_definition

_writing = ContextVar('specification_publication_write', default=False)


@contextmanager
def publication_writes():
    token = _writing.set(True)
    try:
        yield
    finally:
        _writing.reset(token)


class ImmutableQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError('Specification records are append-only.')

    def delete(self):
        raise ValidationError('Specification history cannot be deleted.')

    def bulk_create(self, *args, **kwargs):
        raise ValidationError('Use the reviewed publication workflow.')

    def bulk_update(self, *args, **kwargs):
        raise ValidationError('Specification records are append-only.')


class ImmutableRecord(BaseModel):
    objects = ImmutableQuerySet.as_manager()

    class Meta:
        abstract = True
        base_manager_name = 'objects'

    def save(self, *args, **kwargs):
        if not self._state.adding or not _writing.get():
            raise ValidationError('Use the reviewed append-only publication workflow.')
        if args or kwargs.get('force_update') or kwargs.get('update_fields') is not None:
            raise ValidationError('Specification writes are insert-only.')
        self.full_clean()
        kwargs['force_insert'] = True
        return super().save(**kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Specification history cannot be deleted.')


class PayloadRecord(ImmutableRecord):
    content = models.JSONField()
    content_hash = models.CharField(max_length=71, unique=True)

    class Meta(ImmutableRecord.Meta):
        abstract = True

    def validate_payload(self, validator):
        try:
            validator(self.content)
        except (ContractError, KeyError, TypeError) as exc:
            raise ValidationError(str(exc)) from exc
        if self.content_hash != self.content['content_hash']:
            raise ValidationError('Stored content hash differs from reviewed payload.')


class SpecificationUnitRegistry(PayloadRecord):
    """An exact immutable B1 unit-registry artifact, never a latest-unit lookup."""
    artifact_reference = models.TextField()
    artifact_hash = models.CharField(max_length=71)

    def clean(self):
        super().clean()
        self.validate_payload(validate_unit_registry)
        try:
            s.artifact_ref({"reference": self.artifact_reference, "content_hash": self.artifact_hash})
        except ContractError as exc:
            raise ValidationError(str(exc)) from exc


class EvidenceDocument(PayloadRecord):
    source_id = models.CharField(max_length=100)
    raw_artifact_hash = models.CharField(max_length=71)

    def clean(self):
        super().clean()
        self.validate_payload(s.document)
        if str(self.uuid) != self.content['uuid'] or self.source_id != self.content['source_id'] or self.raw_artifact_hash != self.content['raw_artifact']['content_hash']:
            raise ValidationError('Evidence document identity mismatch.')


class EvidenceAssertionReference(PayloadRecord):
    document = models.ForeignKey(EvidenceDocument, on_delete=models.PROTECT)
    extractor_id = models.CharField(max_length=150)
    extractor_version = models.CharField(max_length=100)
    extraction_mode = models.CharField(max_length=100)
    assertion_set_id = models.CharField(max_length=255)
    local_assertion_id = models.CharField(max_length=255)

    class Meta(PayloadRecord.Meta):
        constraints = [models.UniqueConstraint(fields=('document', 'extractor_id', 'extractor_version', 'extraction_mode', 'assertion_set_id', 'local_assertion_id'), name='reference_spec_evidence_identity')]

    def clean(self):
        super().clean()
        self.validate_payload(s.evidence_assertion)
        r = self.content['reference']
        if str(self.uuid) != self.content['uuid'] or any(getattr(self, k) != r[k] for k in ('extractor_id', 'extractor_version', 'extraction_mode', 'assertion_set_id', 'local_assertion_id')):
            raise ValidationError('Evidence assertion identity mismatch.')
        if self.document_id and (r['document_reference_hash'] != self.document.content_hash or r['document_hash'] != self.document.raw_artifact_hash or r['source_id'] != self.document.source_id):
            raise ValidationError('Evidence document relationship mismatch.')


class SpecificationDefinition(ImmutableRecord):
    key = models.CharField(max_length=128, unique=True)

    def clean(self):
        super().clean()
        try:
            s.token(self.key)
        except ContractError as exc:
            raise ValidationError(str(exc)) from exc


class SpecificationDefinitionRevision(PayloadRecord):
    definition = models.ForeignKey(SpecificationDefinition, on_delete=models.PROTECT, related_name='revisions')
    revision_number = models.PositiveIntegerField()
    supersedes = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='successor')
    finding = models.CharField(max_length=20)

    class Meta(PayloadRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=('definition', 'revision_number'), name='reference_spec_definition_revision'),
            models.CheckConstraint(condition=models.Q(revision_number__gte=1), name='reference_spec_definition_positive'),
            models.CheckConstraint(condition=(models.Q(revision_number=1, supersedes__isnull=True) | models.Q(revision_number__gt=1, supersedes__isnull=False)), name='reference_spec_definition_predecessor'),
        ]

    def clean(self):
        super().clean()
        self.validate_payload(lambda v: s.member({'kind': 'definition', 'content': v}))
        meta = self.content['meta']
        if str(self.uuid) != meta['revision_uuid'] or str(self.definition.uuid) != meta['logical_uuid'] or self.definition.key != self.content['key'] or self.revision_number != meta['revision_number'] or self.finding != meta['finding']:
            raise ValidationError('Definition revision identity mismatch.')
        _validate_predecessor(self, meta['supersedes'], 'definition_id')


class SpecificationDefinitionDependency(ImmutableRecord):
    definition = models.ForeignKey(SpecificationDefinitionRevision, on_delete=models.PROTECT, related_name='qualifier_dependencies')
    categorical_definition = models.ForeignKey(SpecificationDefinitionRevision, on_delete=models.PROTECT, related_name='qualifier_dependents')
    qualifier_key = models.CharField(max_length=128)

    class Meta(ImmutableRecord.Meta):
        constraints = [models.UniqueConstraint(fields=('definition', 'qualifier_key'), name='reference_spec_qualifier_binding')]

    def clean(self):
        super().clean()
        rules = {r['key']: r for r in self.definition.content['qualifier_rules']}
        r = rules.get(self.qualifier_key)
        if r is None or r['categorical_definition'] != _ref(self.categorical_definition) or self.categorical_definition.content['value_kind'] != 'category':
            raise ValidationError('Categorical qualifier relationship mismatch.')


class SpecificationAssertion(PayloadRecord):
    definition_revision = models.ForeignKey(SpecificationDefinitionRevision, on_delete=models.PROTECT, related_name='assertions')
    unit_registry = models.ForeignKey(SpecificationUnitRegistry, on_delete=models.PROTECT)
    supersedes = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='successor')

    @property
    def value(self):
        return self.content['value']

    def clean(self):
        super().clean()
        self.validate_payload(validate_assertion)
        c = self.content
        if str(self.uuid) != c['assertion_uuid'] or c['definition_revision_uuid'] != str(self.definition_revision.uuid) or c['definition_revision_hash'] != self.definition_revision.content_hash or c['supersedes_assertion_uuid'] != (str(self.supersedes.uuid) if self.supersedes_id else None):
            raise ValidationError('Specification assertion relationship mismatch.')
        if self.supersedes_id and self.supersedes_id == self.pk:
            raise ValidationError('Assertion cannot supersede itself.')
        try:
            units = validate_unit_registry(self.unit_registry.content)
            validate_value_definition(c['value'], self.definition_revision.content, units)
        except ContractError as exc:
            raise ValidationError(str(exc)) from exc


class SpecificationCatalogue(ImmutableRecord):
    vehicle_definition = models.OneToOneField(VehicleDefinition, on_delete=models.PROTECT, related_name='specification_catalogue')


class SpecificationCatalogueRevision(PayloadRecord):
    catalogue = models.ForeignKey(SpecificationCatalogue, on_delete=models.PROTECT, related_name='revisions')
    revision_number = models.PositiveIntegerField()
    supersedes = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='successor')
    unit_registry = models.ForeignKey(SpecificationUnitRegistry, on_delete=models.PROTECT)
    finding = models.CharField(max_length=20)
    manifest = models.JSONField()

    class Meta(PayloadRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=('catalogue', 'revision_number'), name='reference_spec_catalogue_revision'),
            models.CheckConstraint(condition=models.Q(revision_number__gte=1), name='reference_spec_catalogue_positive'),
            models.CheckConstraint(condition=(models.Q(revision_number=1, supersedes__isnull=True) | models.Q(revision_number__gt=1, supersedes__isnull=False)), name='reference_spec_catalogue_predecessor'),
        ]

    def clean(self):
        super().clean()
        self.validate_payload(s.catalogue)
        c = self.content
        if str(self.uuid) != c['revision_uuid'] or str(self.catalogue.uuid) != c['logical_uuid'] or str(self.catalogue.vehicle_definition.uuid) != c['target_uuid'] or self.revision_number != c['revision_number'] or self.finding != c['finding']:
            raise ValidationError('Catalogue revision identity mismatch.')
        _validate_predecessor(self, c['supersedes'], 'catalogue_id')
        from .canonical import verify_hash
        try:
            verify_hash(self.manifest, 'manifest_hash')
            if self.manifest['draft']['catalogue'] != c:
                raise ValidationError('Catalogue differs from authorized manifest.')
        except (ContractError, KeyError) as exc:
            raise ValidationError(str(exc)) from exc


MEMBERSHIP_TARGETS = {
    'definition_revision': 'definition', 'assertion': 'specification_assertion',
    'transmission_description_revision': 'transmission_description',
    'transmission_offering_revision': 'transmission_offering',
    'equipment_item_revision': 'equipment_item',
    'equipment_offering_revision': 'equipment_offering',
    'compatibility_rule_revision': 'compatibility_rule',
}
EVIDENCE_OWNERS = (
    'definition_revision', 'assertion', 'catalogue_revision',
    'transmission_description_revision', 'transmission_offering_revision',
    'equipment_item_revision', 'equipment_offering_revision', 'compatibility_rule_revision',
)


def _exclusive_target(fields):
    condition = models.Q()
    for field in fields:
        condition |= models.Q(**{name + '__isnull': name != field for name in fields})
    return condition


class SpecificationCatalogueMembership(ImmutableRecord):
    catalogue_revision = models.ForeignKey(SpecificationCatalogueRevision, on_delete=models.PROTECT, related_name='memberships')
    definition_revision = models.ForeignKey(SpecificationDefinitionRevision, null=True, blank=True, on_delete=models.PROTECT)
    assertion = models.ForeignKey(SpecificationAssertion, null=True, blank=True, on_delete=models.PROTECT)

    transmission_description_revision = models.ForeignKey('TransmissionDescriptionRevision', null=True, blank=True, on_delete=models.PROTECT)
    transmission_offering_revision = models.ForeignKey('TransmissionOfferingRevision', null=True, blank=True, on_delete=models.PROTECT)
    equipment_item_revision = models.ForeignKey('EquipmentItemRevision', null=True, blank=True, on_delete=models.PROTECT)
    equipment_offering_revision = models.ForeignKey('EquipmentOfferingRevision', null=True, blank=True, on_delete=models.PROTECT)
    compatibility_rule_revision = models.ForeignKey('CompatibilityRuleRevision', null=True, blank=True, on_delete=models.PROTECT)

    class Meta(ImmutableRecord.Meta):
        constraints = [
            models.CheckConstraint(condition=_exclusive_target(MEMBERSHIP_TARGETS), name='reference_spec_membership_one_target'),
            models.UniqueConstraint(fields=('catalogue_revision', 'definition_revision'), name='reference_spec_member_definition'),
            models.UniqueConstraint(fields=('catalogue_revision', 'assertion'), name='reference_spec_member_assertion'),
            models.UniqueConstraint(fields=('catalogue_revision', 'transmission_description_revision'), name='reference_spec_member_transmission_desc'),
            models.UniqueConstraint(fields=('catalogue_revision', 'transmission_offering_revision'), name='reference_spec_member_transmission_offer'),
            models.UniqueConstraint(fields=('catalogue_revision', 'equipment_item_revision'), name='reference_spec_member_equipment_item'),
            models.UniqueConstraint(fields=('catalogue_revision', 'equipment_offering_revision'), name='reference_spec_member_equipment_offer'),
            models.UniqueConstraint(fields=('catalogue_revision', 'compatibility_rule_revision'), name='reference_spec_member_compat_rule'),
        ]

    def clean(self):
        super().clean()
        targets = [(kind, getattr(self, field)) for field, kind in MEMBERSHIP_TARGETS.items() if getattr(self, field + '_id')]
        if len(targets) != 1:
            raise ValidationError('Membership requires exactly one revision.')
        kind, record = targets[0]
        if record is None or {'kind': kind, 'revision': _ref(record)} not in self.catalogue_revision.content['members']:
            raise ValidationError('Membership is not an exact snapshot member.')


class SpecificationCatalogueCoverage(ImmutableRecord):
    catalogue_revision = models.ForeignKey(SpecificationCatalogueRevision, on_delete=models.PROTECT, related_name='coverage_records')
    area = models.CharField(max_length=30, choices=[(v, v) for v in ('technical_specifications', 'transmission_offerings', 'equipment_offerings', 'compatibility')])
    content = models.JSONField()

    class Meta(ImmutableRecord.Meta):
        constraints = [models.UniqueConstraint(fields=('catalogue_revision', 'area'), name='reference_spec_coverage_area')]

    def clean(self):
        super().clean()
        try:
            s.coverage_record(self.content)
        except ContractError as exc:
            raise ValidationError(str(exc)) from exc
        if self.catalogue_revision.content['coverage'].get(self.area) != self.content:
            raise ValidationError('Coverage differs from exact snapshot.')


class SpecificationEvidenceLink(ImmutableRecord):
    evidence = models.ForeignKey(EvidenceAssertionReference, on_delete=models.PROTECT)
    definition_revision = models.ForeignKey(SpecificationDefinitionRevision, null=True, blank=True, on_delete=models.PROTECT)
    assertion = models.ForeignKey(SpecificationAssertion, null=True, blank=True, on_delete=models.PROTECT)
    catalogue_revision = models.ForeignKey(SpecificationCatalogueRevision, null=True, blank=True, on_delete=models.PROTECT)
    transmission_description_revision = models.ForeignKey('TransmissionDescriptionRevision', null=True, blank=True, on_delete=models.PROTECT)
    transmission_offering_revision = models.ForeignKey('TransmissionOfferingRevision', null=True, blank=True, on_delete=models.PROTECT)
    equipment_item_revision = models.ForeignKey('EquipmentItemRevision', null=True, blank=True, on_delete=models.PROTECT)
    equipment_offering_revision = models.ForeignKey('EquipmentOfferingRevision', null=True, blank=True, on_delete=models.PROTECT)
    compatibility_rule_revision = models.ForeignKey('CompatibilityRuleRevision', null=True, blank=True, on_delete=models.PROTECT)
    position = models.PositiveIntegerField()
    role = models.CharField(max_length=15, choices=[(v, v) for v in ('supports', 'contradicts', 'qualifies', 'excludes')])

    class Meta(ImmutableRecord.Meta):
        constraints = [
            models.CheckConstraint(condition=_exclusive_target(EVIDENCE_OWNERS), name='reference_spec_evidence_one_owner'),
            *[models.UniqueConstraint(fields=(owner, 'position'), name=f'reference_spec_link_{tag}') for owner, tag in [
                ('definition_revision', 'definition'), ('assertion', 'assertion'), ('catalogue_revision', 'catalogue'),
                ('transmission_description_revision', 'transmission_desc'), ('transmission_offering_revision', 'transmission_offer'),
                ('equipment_item_revision', 'equipment_item'), ('equipment_offering_revision', 'equipment_offer'),
                ('compatibility_rule_revision', 'compat_rule'),
            ]],
        ]

    def clean(self):
        super().clean()
        if self.definition_revision_id:
            expected = [{'role': 'supports', 'reference': r} for r in self.definition_revision.content['evidence_refs']]
        elif self.assertion_id:
            expected = self.assertion.content['evidence_links']
        elif self.catalogue_revision_id:
            expected = [{'role': 'supports', 'reference': r} for r in self.catalogue_revision.content['evidence_refs']]
        elif self.transmission_description_revision_id:
            expected = self.transmission_description_revision.content['qualified']['evidence_links']
        elif self.transmission_offering_revision_id:
            expected = self.transmission_offering_revision.content['qualified']['evidence_links']
        elif self.equipment_item_revision_id:
            expected = self.equipment_item_revision.content['qualified']['evidence_links']
        elif self.equipment_offering_revision_id:
            expected = self.equipment_offering_revision.content['qualified']['evidence_links']
        elif self.compatibility_rule_revision_id:
            expected = self.compatibility_rule_revision.content['qualified']['evidence_links']
        else:
            raise ValidationError('Evidence link requires an owner.')
        reference = self.evidence.content['reference'] | {'assertion_hash': self.evidence.content_hash}
        if self.position >= len(expected) or expected[self.position] != {'role': self.role, 'reference': reference}:
            raise ValidationError('Evidence link differs from exact reviewed order/role.')


class SpecificationPublicationReceipt(ImmutableRecord):
    executed_at = models.DateTimeField(auto_now_add=True)
    operation_type = models.CharField(max_length=40, default='specification_catalogue_publication', editable=False)
    operator_label = models.CharField(max_length=150)
    manifest_hash = models.CharField(max_length=71)
    manifest_text = models.TextField()
    outcome = models.CharField(max_length=30, choices=[(v, v) for v in ('published', 'no_op_exact_match', 'aborted_stale_plan', 'rejected')])
    catalogue_revision = models.ForeignKey(SpecificationCatalogueRevision, null=True, blank=True, on_delete=models.PROTECT)
    messages = models.JSONField(default=list, blank=True)

    def clean(self):
        super().clean()
        from .canonical import hash_string
        try:
            hash_string(self.manifest_hash)
        except ContractError as exc:
            raise ValidationError(str(exc)) from exc
        if self.operation_type != 'specification_catalogue_publication' or not self.operator_label.strip():
            raise ValidationError('Truthful operation/operator attribution required.')
        from .canonical import loads, verify_hash
        try:
            manifest = loads(self.manifest_text)
            verify_hash(manifest, 'manifest_hash')
            if manifest['manifest_hash'] != self.manifest_hash:
                raise ValidationError('Receipt manifest hash mismatch.')
        except (ContractError, KeyError) as exc:
            raise ValidationError(str(exc)) from exc
        if self.outcome in ('published', 'no_op_exact_match'):
            if not self.catalogue_revision_id or manifest['draft']['catalogue'] != self.catalogue_revision.content or manifest['manifest_hash'] != self.catalogue_revision.manifest['manifest_hash']:
                raise ValidationError('Success requires its exact catalogue revision and authorization.')


def _ref(record):
    return {'uuid': str(record.uuid), 'content_hash': record.content_hash}


def _validate_predecessor(record, reference, parent_field):
    if reference != (_ref(record.supersedes) if record.supersedes_id else None):
        raise ValidationError('Predecessor hash/identity mismatch.')
    if record.supersedes_id and (getattr(record, parent_field) != getattr(record.supersedes, parent_field) or record.revision_number != record.supersedes.revision_number + 1):
        raise ValidationError('Predecessor belongs to another revision chain.')


class TransmissionDescription(ImmutableRecord):
    """Reviewed hardware identity; codes/type/speed equality never merges roots."""
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT)
    namespace = models.TextField()
    source_native_identity = models.TextField()

    def clean(self):
        super().clean()
        if not self.namespace or not self.source_native_identity:
            raise ValidationError('Transmission requires its reviewed source identity.')


class TransmissionDescriptionRevision(PayloadRecord):
    description = models.ForeignKey(TransmissionDescription, on_delete=models.PROTECT, related_name='revisions')
    revision_number = models.PositiveIntegerField()
    supersedes = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='successor')
    finding = models.CharField(max_length=20)
    designation = models.TextField()
    code = models.TextField(null=True, blank=True)
    transmission_type = models.CharField(max_length=128, null=True, blank=True)
    forward_speeds = models.PositiveIntegerField(null=True, blank=True)

    class Meta(PayloadRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=('description', 'revision_number'), name='reference_transmission_desc_revision'),
            models.CheckConstraint(condition=models.Q(revision_number__gte=1), name='reference_transmission_desc_positive'),
            models.CheckConstraint(condition=(models.Q(revision_number=1, supersedes__isnull=True) | models.Q(revision_number__gt=1, supersedes__isnull=False)), name='reference_transmission_desc_predecessor'),
        ]

    def clean(self):
        super().clean()
        self.validate_payload(lambda v: s.member({'kind': 'transmission_description', 'content': v}))
        c, root = self.content, self.description
        meta = c['meta']
        if (str(self.uuid) != meta['revision_uuid'] or str(root.uuid) != meta['logical_uuid'] or
                str(root.manufacturer.uuid) != c['manufacturer_uuid'] or root.namespace != c['namespace'] or
                root.source_native_identity != c['source_native_identity'] or self.revision_number != meta['revision_number'] or
                self.finding != meta['finding'] or self.designation != c['designation'] or self.code != c['code'] or
                self.transmission_type != c['type'] or self.forward_speeds != c['forward_speeds']):
            raise ValidationError('Transmission description differs from reviewed identity/content.')
        _validate_predecessor(self, meta['supersedes'], 'description_id')


class TransmissionEngineeringAssertion(ImmutableRecord):
    description_revision = models.ForeignKey(TransmissionDescriptionRevision, on_delete=models.PROTECT, related_name='engineering_links')
    assertion = models.ForeignKey(SpecificationAssertion, on_delete=models.PROTECT)
    position = models.PositiveIntegerField()

    class Meta(ImmutableRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=('description_revision', 'position'), name='reference_transmission_engineering_position'),
            models.UniqueConstraint(fields=('description_revision', 'assertion'), name='reference_transmission_engineering_assertion'),
        ]

    def clean(self):
        super().clean()
        refs = self.description_revision.content['engineering_assertions']
        if self.position >= len(refs) or refs[self.position] != _ref(self.assertion):
            raise ValidationError('Transmission engineering evidence differs from reviewed revision.')


class TransmissionOffering(ImmutableRecord):
    """Logical availability chain under one exact canonical baseline."""
    vehicle_definition = models.ForeignKey(VehicleDefinition, on_delete=models.PROTECT, related_name='transmission_offerings')
    description = models.ForeignKey(TransmissionDescription, on_delete=models.PROTECT)


class TransmissionOfferingRevision(PayloadRecord):
    offering = models.ForeignKey(TransmissionOffering, on_delete=models.PROTECT, related_name='revisions')
    description_revision = models.ForeignKey(TransmissionDescriptionRevision, on_delete=models.PROTECT)
    revision_number = models.PositiveIntegerField()
    supersedes = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='successor')
    finding = models.CharField(max_length=20)
    availability = models.CharField(max_length=12, choices=[(v, v) for v in ('standard', 'optional', 'unavailable', 'unknown')])

    class Meta(PayloadRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=('offering', 'revision_number'), name='reference_transmission_offer_revision'),
            models.CheckConstraint(condition=models.Q(revision_number__gte=1), name='reference_transmission_offer_positive'),
            models.CheckConstraint(condition=(models.Q(revision_number=1, supersedes__isnull=True) | models.Q(revision_number__gt=1, supersedes__isnull=False)), name='reference_transmission_offer_predecessor'),
        ]

    @property
    def vehicle_definition(self):
        return self.offering.vehicle_definition

    def clean(self):
        super().clean()
        self.validate_payload(lambda v: s.member({'kind': 'transmission_offering', 'content': v}))
        c, root = self.content, self.offering
        meta = c['meta']
        if (str(self.uuid) != meta['revision_uuid'] or str(root.uuid) != meta['logical_uuid'] or
                str(root.vehicle_definition.uuid) != c['target_uuid'] or
                root.description_id != self.description_revision.description_id or
                _ref(self.description_revision) != c['description'] or self.revision_number != meta['revision_number'] or
                self.finding != meta['finding'] or self.availability != c['availability']):
            raise ValidationError('Transmission offering differs from exact baseline/description revision.')
        if self.description_revision.description.manufacturer_id != root.vehicle_definition.generation.vehicle_model.manufacturer_id:
            raise ValidationError('Transmission belongs to another manufacturer.')
        _validate_predecessor(self, meta['supersedes'], 'offering_id')


class EquipmentItem(ImmutableRecord):
    """Reviewed hardware/package/accessory identity; codes/name equality never merges roots."""
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT)
    namespace = models.TextField()
    source_native_identity = models.TextField()

    def clean(self):
        super().clean()
        if not self.namespace or not self.source_native_identity:
            raise ValidationError('Equipment requires its reviewed source identity.')


class EquipmentItemRevision(PayloadRecord):
    item = models.ForeignKey(EquipmentItem, on_delete=models.PROTECT, related_name='revisions')
    revision_number = models.PositiveIntegerField()
    supersedes = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='successor')
    finding = models.CharField(max_length=20)
    name = models.TextField()
    code = models.TextField(null=True, blank=True)
    kind = models.CharField(max_length=30, choices=[(v, v) for v in ('equipment_item', 'factory_package', 'factory_option', 'accessory')])
    installation_channel = models.CharField(max_length=30, choices=[(v, v) for v in ('factory', 'manufacturer_accessory', 'unresolved')])

    class Meta(PayloadRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=('item', 'revision_number'), name='reference_equipment_item_revision'),
            models.CheckConstraint(condition=models.Q(revision_number__gte=1), name='reference_equipment_item_positive'),
            models.CheckConstraint(condition=(models.Q(revision_number=1, supersedes__isnull=True) | models.Q(revision_number__gt=1, supersedes__isnull=False)), name='reference_equipment_item_predecessor'),
        ]

    def clean(self):
        super().clean()
        self.validate_payload(lambda v: s.member({'kind': 'equipment_item', 'content': v}))
        c, root = self.content, self.item
        meta = c['meta']
        if (str(self.uuid) != meta['revision_uuid'] or str(root.uuid) != meta['logical_uuid'] or
                str(root.manufacturer.uuid) != c['manufacturer_uuid'] or root.namespace != c['namespace'] or
                root.source_native_identity != c['source_native_identity'] or self.revision_number != meta['revision_number'] or
                self.finding != meta['finding'] or self.name != c['name'] or self.code != c['code'] or
                self.kind != c['kind'] or self.installation_channel != c['installation_channel']):
            raise ValidationError('Equipment item differs from reviewed identity/content.')
        _validate_predecessor(self, meta['supersedes'], 'item_id')


class EquipmentOffering(ImmutableRecord):
    """Logical equipment offering chain under one exact canonical baseline."""
    vehicle_definition = models.ForeignKey(VehicleDefinition, on_delete=models.PROTECT, related_name='equipment_offerings')
    item = models.ForeignKey(EquipmentItem, on_delete=models.PROTECT)


class EquipmentOfferingRevision(PayloadRecord):
    offering = models.ForeignKey(EquipmentOffering, on_delete=models.PROTECT, related_name='revisions')
    item_revision = models.ForeignKey(EquipmentItemRevision, on_delete=models.PROTECT)
    revision_number = models.PositiveIntegerField()
    supersedes = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='successor')
    finding = models.CharField(max_length=20)
    assignment = models.CharField(max_length=30, choices=[(v, v) for v in ('standard', 'optional', 'unavailable', 'unknown', 'accessory_catalogue_only')])

    class Meta(PayloadRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=('offering', 'revision_number'), name='reference_equipment_offer_revision'),
            models.CheckConstraint(condition=models.Q(revision_number__gte=1), name='reference_equipment_offer_positive'),
            models.CheckConstraint(condition=(models.Q(revision_number=1, supersedes__isnull=True) | models.Q(revision_number__gt=1, supersedes__isnull=False)), name='reference_equipment_offer_predecessor'),
        ]

    @property
    def vehicle_definition(self):
        return self.offering.vehicle_definition

    def clean(self):
        super().clean()
        self.validate_payload(lambda v: s.member({'kind': 'equipment_offering', 'content': v}))
        c, root = self.content, self.offering
        meta = c['meta']
        if (str(self.uuid) != meta['revision_uuid'] or str(root.uuid) != meta['logical_uuid'] or
                str(root.vehicle_definition.uuid) != c['target_uuid'] or
                root.item_id != self.item_revision.item_id or
                _ref(self.item_revision) != c['item'] or self.revision_number != meta['revision_number'] or
                self.finding != meta['finding'] or self.assignment != c['assignment']):
            raise ValidationError('Equipment offering differs from exact baseline/item revision.')
        if self.item_revision.item.manufacturer_id != root.vehicle_definition.generation.vehicle_model.manufacturer_id:
            raise ValidationError('Equipment belongs to another manufacturer.')
        _validate_predecessor(self, meta['supersedes'], 'offering_id')


class CompatibilityRule(ImmutableRecord):
    """Logical compatibility rule under one exact canonical baseline."""
    vehicle_definition = models.ForeignKey(VehicleDefinition, on_delete=models.PROTECT, related_name='compatibility_rules')


class CompatibilityRuleRevision(PayloadRecord):
    rule = models.ForeignKey(CompatibilityRule, on_delete=models.PROTECT, related_name='revisions')
    revision_number = models.PositiveIntegerField()
    supersedes = models.OneToOneField('self', null=True, blank=True, on_delete=models.PROTECT, related_name='successor')
    finding = models.CharField(max_length=20)
    rule_kind = models.CharField(max_length=30, choices=[(v, v) for v in ('requires_all', 'requires_any', 'excludes', 'includes', 'replaces', 'cardinality', 'supports_combination')])

    class Meta(PayloadRecord.Meta):
        constraints = [
            models.UniqueConstraint(fields=('rule', 'revision_number'), name='reference_compat_rule_revision'),
            models.CheckConstraint(condition=models.Q(revision_number__gte=1), name='reference_compat_rule_positive'),
            models.CheckConstraint(condition=(models.Q(revision_number=1, supersedes__isnull=True) | models.Q(revision_number__gt=1, supersedes__isnull=False)), name='reference_compat_rule_predecessor'),
        ]

    @property
    def vehicle_definition(self):
        return self.rule.vehicle_definition

    def clean(self):
        super().clean()
        self.validate_payload(lambda v: s.member({'kind': 'compatibility_rule', 'content': v}))
        c, root = self.content, self.rule
        meta = c['meta']
        if (str(self.uuid) != meta['revision_uuid'] or str(root.uuid) != meta['logical_uuid'] or
                str(root.vehicle_definition.uuid) != c['target_uuid'] or
                self.revision_number != meta['revision_number'] or self.finding != meta['finding'] or
                self.rule_kind != c['rule']['kind']):
            raise ValidationError('Compatibility rule differs from exact baseline/rule content.')
        _validate_predecessor(self, meta['supersedes'], 'rule_id')
