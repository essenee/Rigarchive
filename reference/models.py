import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from core.models import BaseModel


class Manufacturer(BaseModel):
    """
    Represents a vehicle manufacturer in the Reference Domain.

    A manufacturer is the highest level of the canonical vehicle
    hierarchy and owns one or more vehicle models.
    """

    name = models.CharField(max_length=100, unique=True)

    slug = models.SlugField(
        max_length=120,
        unique=True,
        editable=False,
        blank=True,
    )

    country_code = models.CharField(
        max_length=2,
        blank=True,
        help_text="Optional ISO 3166-1 alpha-2 country code.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Inactive manufacturers remain preserved but are not "
            "normally displayed."
        ),
    )

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse(
            "reference:manufacturer-detail",
            kwargs={"manufacturer_slug": self.slug},
        )


class VehicleModel(BaseModel):
    """
    Represents a named vehicle model produced by a manufacturer.

    Examples include Toyota 4Runner, Ford Transit, and Jeep Wrangler.
    """

    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.PROTECT,
        related_name="vehicle_models",
    )

    name = models.CharField(max_length=100)

    slug = models.SlugField(
        max_length=120,
        editable=False,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("manufacturer__name", "name")

        constraints = [
            models.UniqueConstraint(
                fields=("manufacturer", "name"),
                name="reference_unique_vehicle_model_name_per_manufacturer",
            ),
            models.UniqueConstraint(
                fields=("manufacturer", "slug"),
                name="reference_unique_vehicle_model_slug_per_manufacturer",
            ),
        ]

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.manufacturer.name} {self.name}"

    def get_absolute_url(self) -> str:
        return reverse(
            "reference:vehicle-model-detail",
            kwargs={
                "manufacturer_slug": self.manufacturer.slug,
                "vehicle_model_slug": self.slug,
            },
        )


class Generation(BaseModel):
    """
    Represents a recognized generation of a vehicle model.

    A generation groups vehicle definitions that share a meaningful
    manufacturer-defined or historically recognized product lifecycle.
    """

    vehicle_model = models.ForeignKey(
        VehicleModel,
        on_delete=models.PROTECT,
        related_name="generations",
    )

    name = models.CharField(
        max_length=100,
        help_text="Human-readable name, such as Fourth Generation.",
    )

    slug = models.SlugField(
        max_length=120,
        editable=False,
        blank=True,
    )

    generation_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Optional numeric generation sequence, such as 4.",
    )

    start_year = models.PositiveSmallIntegerField()

    end_year = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Leave blank when the generation is still in production.",
    )

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = (
            "vehicle_model__manufacturer__name",
            "vehicle_model__name",
            "start_year",
        )

        constraints = [
            models.UniqueConstraint(
                fields=("vehicle_model", "slug"),
                name="reference_unique_generation_slug_per_vehicle_model",
            ),
        ]

    def clean(self) -> None:
        super().clean()

        if self.end_year is not None and self.end_year < self.start_year:
            raise ValidationError(
                {
                    "end_year": (
                        "End year cannot be earlier than start year."
                    )
                }
            )

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        years = (
            f"{self.start_year}–{self.end_year}"
            if self.end_year is not None
            else f"{self.start_year}–present"
        )

        return f"{self.vehicle_model} — {self.name} ({years})"

    def get_absolute_url(self) -> str:
        return reverse(
            "reference:generation-detail",
            kwargs={
                "manufacturer_slug": self.vehicle_model.manufacturer.slug,
                "vehicle_model_slug": self.vehicle_model.slug,
                "generation_slug": self.slug,
            },
        )


class VehicleDefinition(BaseModel):
    """
    Represents a canonical vehicle configuration in the Reference Domain.

    A vehicle definition describes a recognized configuration rather than
    an individually owned physical vehicle.
    """

    class Market(models.TextChoices):
        UNITED_STATES = "US", "United States"
        CANADA = "CA", "Canada"
        OTHER = "OT", "Other"

    class Drivetrain(models.TextChoices):
        TWO_WHEEL_DRIVE = "2WD", "2WD"
        FOUR_WHEEL_DRIVE = "4WD", "4WD"
        ALL_WHEEL_DRIVE = "AWD", "AWD"
        UNKNOWN = "UNK", "Unknown"

    generation = models.ForeignKey(
        Generation,
        on_delete=models.PROTECT,
        related_name="vehicle_definitions",
    )

    model_year = models.PositiveSmallIntegerField()

    trim_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Manufacturer trim name, such as SR5, Sport Edition, "
            "or Limited."
        ),
    )

    engine_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Human-readable engine description. This remains free text "
            "until a shared engine-definition domain is justified."
        ),
    )

    drivetrain = models.CharField(
        max_length=3,
        choices=Drivetrain,
        default=Drivetrain.UNKNOWN,
    )

    market = models.CharField(
        max_length=2,
        choices=Market,
        default=Market.UNITED_STATES,
    )

    slug = models.SlugField(
        max_length=180,
        editable=False,
        blank=True,
    )

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = (
            "generation__vehicle_model__manufacturer__name",
            "generation__vehicle_model__name",
            "model_year",
            "trim_name",
            "engine_name",
            "drivetrain",
        )

        constraints = [
            models.UniqueConstraint(
                fields=("generation", "slug"),
                name=(
                    "reference_unique_vehicle_definition_slug_per_generation"
                ),
            ),
        ]

    def clean(self) -> None:
        super().clean()

        if not self.generation_id:
            return

        if self.model_year < self.generation.start_year:
            raise ValidationError(
                {
                    "model_year": (
                        "Model year cannot be earlier than the "
                        "generation start year."
                    )
                }
            )

        if (
            self.generation.end_year is not None
            and self.model_year > self.generation.end_year
        ):
            raise ValidationError(
                {
                    "model_year": (
                        "Model year cannot be later than the "
                        "generation end year."
                    )
                }
            )

    def build_slug(self) -> str:
        """
        Build the initial URL slug from canonical configuration fields.

        The slug is generated only for a record that does not already have
        one. Subsequent edits therefore do not silently change its URL.
        """

        parts = [
            str(self.model_year),
            self.trim_name,
            self.engine_name,
            self.drivetrain,
            self.market,
        ]

        source = "-".join(
            str(part).strip()
            for part in parts
            if str(part).strip()
        )

        return slugify(source)

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = self.build_slug()

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        details = [
            str(self.model_year),
            str(self.generation.vehicle_model),
            self.trim_name,
            self.engine_name,
            self.get_drivetrain_display(),
        ]

        return " ".join(detail for detail in details if detail)

    def get_absolute_url(self) -> str:
        return reverse(
            "reference:vehicle-definition-detail",
            kwargs={
                "manufacturer_slug": (
                    self.generation.vehicle_model.manufacturer.slug
                ),
                "vehicle_model_slug": self.generation.vehicle_model.slug,
                "generation_slug": self.generation.slug,
                "vehicle_definition_slug": self.slug,
            },
        )


class ImmutableCorrespondenceQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Correspondence revisions are append-only.")

    def delete(self):
        raise ValidationError("Correspondence revisions cannot be deleted.")

    def bulk_create(self, *args, **kwargs):
        raise ValidationError("Publish revisions individually through the reviewed workflow.")

    def bulk_update(self, *args, **kwargs):
        raise ValidationError("Correspondence revisions are append-only.")


class GenerationCorrespondenceRevision(BaseModel):
    """One immutable reviewed finding; uuid identifies a revision, correspondence_uuid its chain."""

    correspondence_uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    revision_number = models.PositiveIntegerField(default=1)
    supersedes = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="successor",
    )
    vehicle_model = models.ForeignKey(VehicleModel, on_delete=models.PROTECT)
    generation = models.ForeignKey(Generation, null=True, blank=True, on_delete=models.PROTECT)
    source_id = models.CharField(max_length=100)
    source_namespace = models.CharField(max_length=100)
    identity_type = models.CharField(max_length=50)
    native_identifier = models.CharField(max_length=255)
    market = models.CharField(max_length=2, choices=VehicleDefinition.Market)
    start_year = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField()
    restrictions = models.JSONField(default=dict, blank=True)
    evidence = models.JSONField(default=list)
    finding = models.CharField(max_length=20, choices=[
        ("established", "Established"), ("ambiguous", "Ambiguous"),
        ("rejected", "Rejected"), ("withdrawn", "Withdrawn"),
    ])
    reviewer = models.CharField(max_length=150)
    reviewed_at = models.DateTimeField()
    review_notes = models.TextField()
    content_hash = models.CharField(max_length=71, editable=False)

    objects = ImmutableCorrespondenceQuerySet.as_manager()

    class Meta:
        ordering = ("correspondence_uuid", "revision_number")
        base_manager_name = "objects"
        constraints = [
            models.UniqueConstraint(fields=("correspondence_uuid", "revision_number"),
                                    name="reference_correspondence_revision_unique"),
            models.CheckConstraint(condition=models.Q(revision_number__gte=1),
                                   name="reference_correspondence_revision_positive"),
            models.CheckConstraint(condition=models.Q(end_year__gte=models.F("start_year")),
                                   name="reference_correspondence_year_order"),
        ]

    def clean(self):
        super().clean()
        from reference.ingestion.generation_correspondence import validate_review_payload
        validate_review_payload(self.review_payload())
        if self.generation_id and self.generation.vehicle_model_id != self.vehicle_model_id:
            raise ValidationError("Generation belongs to another model.")
        if self.finding == "established":
            if not self.generation_id or not self.generation.is_active or not self.vehicle_model.is_active:
                raise ValidationError("Established correspondence requires active parents.")
            if not self.vehicle_model.manufacturer.is_active:
                raise ValidationError("Manufacturer is inactive.")
            if self.start_year < self.generation.start_year or (
                self.generation.end_year is not None and self.end_year > self.generation.end_year
            ):
                raise ValidationError("Correspondence is outside the Generation range.")
        if self.supersedes_id:
            previous = self.supersedes
            if previous.correspondence_uuid != self.correspondence_uuid or self.revision_number != previous.revision_number + 1:
                raise ValidationError("Invalid correspondence successor.")
            for name in ("vehicle_model_id", "source_id", "source_namespace", "identity_type", "native_identifier", "market", "start_year", "end_year"):
                if getattr(previous, name) != getattr(self, name):
                    raise ValidationError("A successor cannot change correspondence identity/scope.")
        elif self.revision_number != 1 or type(self).objects.filter(correspondence_uuid=self.correspondence_uuid).exclude(pk=self.pk).exists():
            raise ValidationError("A revision chain must start at revision 1.")

    def review_payload(self):
        return {
            "review_version": "1.0", "revision_uuid": str(self.uuid),
            "correspondence_uuid": str(self.correspondence_uuid), "revision_number": self.revision_number,
            "supersedes_uuid": str(self.supersedes.uuid) if self.supersedes_id else None,
            "vehicle_model_uuid": str(self.vehicle_model.uuid),
            "generation_uuid": str(self.generation.uuid) if self.generation_id else None,
            "source_id": self.source_id, "source_namespace": self.source_namespace,
            "identity_type": self.identity_type, "native_identifier": self.native_identifier,
            "market": self.market, "start_year": self.start_year, "end_year": self.end_year,
            "restrictions": self.restrictions, "evidence": self.evidence, "finding": self.finding,
            "reviewer": self.reviewer, "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "review_notes": self.review_notes,
        }

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Correspondence revisions are append-only.")
        from reference.ingestion.generation_correspondence import digest
        self.full_clean(exclude=["content_hash"])
        expected = digest(self.review_payload())
        if self.content_hash and self.content_hash != expected:
            raise ValidationError("Correspondence content hash mismatch.")
        self.content_hash = expected
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Correspondence revisions cannot be deleted.")


class ImportExecutionReceipt(BaseModel):
    """
    Durable execution audit record detailing an authorized canonical promotion attempt.

    Captures reviewed plan provenance, evidence anchors, target configuration snapshot,
    actual domain execution outcome, and canonical result identity snapshots.
    """

    executed_at = models.DateTimeField(auto_now_add=True)
    execution_channel = models.CharField(max_length=50, default="cli")
    operator_label = models.CharField(max_length=150)
    operation_type = models.CharField(max_length=40, default="vehicle_definition_import", choices=[
        ("vehicle_definition_import", "VehicleDefinition import"),
        ("correspondence_publication", "Correspondence publication"),
    ])
    correspondence_revision = models.ForeignKey(
        GenerationCorrespondenceRevision, null=True, blank=True, on_delete=models.SET_NULL,
    )
    resolution_snapshot_json = models.JSONField(default=dict, blank=True)

    # Reviewed Plan & Manifest Provenance
    manifest_hash = models.CharField(max_length=71)
    candidate_reference = models.CharField(max_length=150)
    planned_action = models.CharField(max_length=30)
    create_basis = models.CharField(max_length=30, blank=True)
    adjudication_hash = models.CharField(
        max_length=71,
        blank=True,
        default="",
        help_text="SHA-256 digest of verified human adjudication artifact.",
    )


    # Primary Evidence Anchors
    source_id = models.CharField(max_length=100)
    raw_artifact_hash = models.CharField(max_length=71)
    raw_artifact_reference = models.CharField(max_length=255)
    source_identity_type = models.CharField(max_length=50, default="record_id")
    native_identifier = models.CharField(max_length=100)

    # Target Configuration Snapshot
    resolved_generation_id = models.IntegerField(null=True, blank=True)
    target_slug = models.CharField(max_length=180)
    target_model_year = models.PositiveSmallIntegerField(null=True, blank=True)
    target_trim_name = models.CharField(max_length=100, blank=True)
    target_engine_name = models.CharField(max_length=100, blank=True)
    target_drivetrain = models.CharField(max_length=3, blank=True)
    target_market = models.CharField(max_length=2, blank=True)
    target_fields_json = models.JSONField(default=dict)

    # Actual Domain Execution Outcome
    execution_outcome = models.CharField(max_length=30)
    messages_json = models.JSONField(default=list)

    # Canonical Result Identity (ForeignKeys + Immutable Snapshots)
    created_vehicle_definition = models.ForeignKey(
        VehicleDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="creation_receipts",
    )
    existing_vehicle_definition = models.ForeignKey(
        VehicleDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matched_receipts",
    )
    created_vehicle_definition_pk_snapshot = models.IntegerField(null=True, blank=True)
    created_vehicle_definition_uuid_snapshot = models.CharField(max_length=36, blank=True)
    created_vehicle_definition_slug_snapshot = models.CharField(max_length=180, blank=True)
    existing_vehicle_definition_pk_snapshot = models.IntegerField(null=True, blank=True)
    existing_vehicle_definition_uuid_snapshot = models.CharField(max_length=36, blank=True)
    existing_vehicle_definition_slug_snapshot = models.CharField(max_length=180, blank=True)

    class Meta:
        ordering = ("-executed_at",)

    def __str__(self) -> str:
        return (
            f"ImportExecutionReceipt {self.uuid} ({self.execution_outcome} - "
            f"{self.target_slug})"
        )


class CanonicalRecordCorrection(BaseModel):
    """
    Durable audit record detailing the correction and supersession of an invalid or obsolete
    canonical VehicleDefinition record by a corrected replacement VehicleDefinition record.

    Captures foreign key references to both superseded and replacement records, immutable identity
    snapshots, correction reason classification, operator label, and linkage to execution receipts.
    """

    class CorrectionReason(models.TextChoices):
        NORMALIZATION_RULE_CORRECTION = (
            "NORMALIZATION_RULE_CORRECTION",
            "Normalization Rule Correction",
        )
        SOURCE_EVIDENCE_CORRECTION = (
            "SOURCE_EVIDENCE_CORRECTION",
            "Source Evidence Correction",
        )
        ADJUDICATED_SPECIFICATION_CORRECTION = (
            "ADJUDICATED_SPECIFICATION_CORRECTION",
            "Adjudicated Specification Correction",
        )
        OTHER = "OTHER", "Other"

    superseded_vehicle_definition = models.ForeignKey(
        VehicleDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_by_corrections",
        help_text="The historical canonical VehicleDefinition being superseded (is_active=False).",
    )

    replacement_vehicle_definition = models.ForeignKey(
        VehicleDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replacement_corrections",
        help_text="The active replacement canonical VehicleDefinition.",
    )

    # Immutable Audit Snapshots
    superseded_vehicle_definition_pk_snapshot = models.IntegerField(
        null=True, blank=True
    )
    superseded_vehicle_definition_uuid_snapshot = models.CharField(
        max_length=36, blank=True
    )
    superseded_vehicle_definition_slug_snapshot = models.CharField(
        max_length=180, blank=True
    )

    replacement_vehicle_definition_pk_snapshot = models.IntegerField(
        null=True, blank=True
    )
    replacement_vehicle_definition_uuid_snapshot = models.CharField(
        max_length=36, blank=True
    )
    replacement_vehicle_definition_slug_snapshot = models.CharField(
        max_length=180, blank=True
    )

    correction_reason = models.CharField(
        max_length=100,
        default=CorrectionReason.NORMALIZATION_RULE_CORRECTION,
    )
    operator_label = models.CharField(max_length=150, default="cli")
    notes = models.TextField(blank=True)

    execution_receipt = models.ForeignKey(
        ImportExecutionReceipt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="correction_audit_records",
        help_text="The execution receipt associated with the replacement promotion.",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return (
            f"CanonicalRecordCorrection {self.uuid}: "
            f"{self.superseded_vehicle_definition_slug_snapshot} -> "
            f"{self.replacement_vehicle_definition_slug_snapshot}"
        )
