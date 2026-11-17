import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from reference.powertrain import ASPIRATION, FUEL, ELECTRIFICATION, FIELDS, TAXONOMIES, engine_label
from django.db import models, transaction
from django.db.models.functions import Coalesce
from django.db.models.functions import Upper, Trim, Lower, Length
from reference.body_identity import TOKEN
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


def normalize_engine_code(value):
    """Trim and uppercase the complete ASCII code, preserving separators/suffixes.

    EA888-CJXC and EA888-CHHB are distinct identities, never family aliases.
    """
    if not isinstance(value, str) or not value.isascii():
        raise ValidationError("Engine code must be an ASCII manufacturer code.")
    value = value.strip().upper()
    import re
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,99}", value):
        raise ValidationError("Use a nonempty manufacturer engine code (letters, digits, dot, dash or underscore).")
    return value


def normalize_internal_variant_key(value):
    """Normalize only an explicitly reviewed discriminator, never derive one."""
    import re
    if not isinstance(value, str) or not value.isascii():
        raise ValidationError("Internal variant key must be an ASCII string.")
    value = value.strip().lower()
    if not re.fullmatch(r"[a-z0-9_-]{0,100}", value):
        raise ValidationError("Use at most 100 lowercase letters, digits, hyphens or underscores.")
    return value


class EngineCodeCharacters(models.Func):
    """Keep both uses of the code expression paired with their SQL parameters."""

    def as_sql(self, compiler, connection, **extra_context):
        sql, params = super().as_sql(compiler, connection, **extra_context)
        return sql, (*params, *params)

    @property
    def identity(self):
        # Migration comparison must retain the original expression identity too.
        _, args, kwargs = self.deconstruct()
        return models.Func(*args, **kwargs).identity

    def deconstruct(self):
        # This is the same database expression as the applied 0012 migration.
        # Only compilation of bound values (used by full_clean) is corrected.
        _, args, kwargs = super().deconstruct()
        return "django.db.models.Func", args, kwargs


class EngineQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Maintain Engine records through validated individual saves.")

    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Author Engine records through validated individual saves.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Maintain Engine records through validated individual saves.")


class Engine(BaseModel):
    """Human-maintained manufacturer/code/variant identity, reused across models and years."""
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT, related_name="engines")
    engine_code = models.CharField(max_length=100)
    internal_variant_key = models.CharField(
        max_length=100, blank=True, null=False, default="",
        help_text="Reviewed internal discriminator; empty means no explicit discriminator is established.",
    )
    name = models.CharField(max_length=100)
    engine_displacement_liters = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    engine_cylinders = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)],
    )
    engine_aspiration = models.CharField(max_length=24, null=True, blank=True, choices=list(ASPIRATION.items()))
    fuel_type = models.CharField(max_length=24, null=True, blank=True, choices=list(FUEL.items()))
    electrification_type = models.CharField(
        max_length=24, null=True, blank=True,
        choices=[(key, labels[0]) for key, labels in ELECTRIFICATION.items()],
    )

    objects = EngineQuerySet.as_manager()

    class Meta:
        ordering = ("manufacturer__name", "engine_code")
        constraints = [
            models.UniqueConstraint(models.F("manufacturer"), Upper(Trim("engine_code")), Lower(Trim("internal_variant_key")), name="reference_unique_engine_manufacturer_code_variant"),
            models.CheckConstraint(condition=models.Func("internal_variant_key", template="(%(expressions)s NOT GLOB '*[^a-z0-9_-]*')", output_field=models.BooleanField()) & models.Func("internal_variant_key", template="(INSTR(%(expressions)s, CHAR(0)) = 0)", output_field=models.BooleanField()) & models.lookups.LessThanOrEqual(Length("internal_variant_key"), 100), name="reference_engine_variant_normalized"),
            models.CheckConstraint(condition=models.Q(engine_code=Upper(Trim("engine_code"))) & EngineCodeCharacters("engine_code", template="(%(expressions)s GLOB '[A-Z0-9]*' AND %(expressions)s NOT GLOB '*[^A-Z0-9._-]*')", output_field=models.BooleanField()), name="reference_engine_code_normalized"),
            models.CheckConstraint(condition=~models.Q(name=""), name="reference_engine_name_nonempty"),
            models.CheckConstraint(condition=models.Q(engine_displacement_liters__isnull=True) | models.Q(engine_displacement_liters__gt=0), name="reference_engine_displacement_positive"),
            models.CheckConstraint(condition=models.Q(engine_cylinders__isnull=True) | models.Q(engine_cylinders__gt=0), name="reference_engine_cylinders_positive"),
            *[models.CheckConstraint(condition=models.Q(**{key + "__isnull": True}) | models.Q(**{key + "__in": list(values)}), name="reference_engine_" + key) for key, values in TAXONOMIES.items()],
        ]

    def clean_fields(self, exclude=None):
        self.engine_code = normalize_engine_code(self.engine_code)
        self.internal_variant_key = normalize_internal_variant_key(self.internal_variant_key)
        for key in FIELDS:
            if isinstance(getattr(self, key), bool):
                raise ValidationError({key: "Boolean is not a powertrain value."})
            if getattr(self, key) == "":
                setattr(self, key, None)
        return super().clean_fields(exclude=exclude)

    def clean(self):
        super().clean()
        from reference.powertrain import record_powertrain, validate_powertrain
        validate_powertrain(record_powertrain(self))
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValidationError({"name": "Engine name must not be blank."})
        if self.pk:
            old = type(self).objects.using(self._state.db).filter(pk=self.pk).first()
            if old and (old.manufacturer_id != self.manufacturer_id or old.engine_code != self.engine_code or old.uuid != self.uuid or old.internal_variant_key != self.internal_variant_key):
                raise ValidationError("Engine manufacturer, code and internal variant key are immutable; create a distinct record for a different identity.")

    def save(self, *args, **kwargs):
        if kwargs.get("update_fields") is not None:
            raise ValidationError("Save the complete Engine record for identity validation.")
        with transaction.atomic(using=kwargs.get("using") or self._state.db):
            if self.pk:
                type(self).objects.using(kwargs.get("using") or self._state.db).select_for_update().get(pk=self.pk)
            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.manufacturer} {self.engine_code} — {self.name}"


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


BODY_ATTRIBUTES = (
    "body_style", "wheelbase_designation", "body_length_designation",
    "roof_height_designation", "door_configuration", "side_door_arrangement",
    "body_code", "body_code_namespace",
)


class FactoryBodyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Correct body configurations with instance.save(), which validates scope and identity.")

    def bulk_update(self, objs, fields, batch_size=None):
        raise ValidationError("Correct body configurations individually with instance.save().")

    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Create body configurations individually with instance.save().")


class FactoryBodyConfiguration(BaseModel):
    """Generation-scoped sparse designations; null means unspecified."""

    generation = models.ForeignKey(
        Generation, on_delete=models.PROTECT, related_name="factory_body_configurations",
    )
    body_style = models.CharField(max_length=128, null=True, blank=True,
        validators=[RegexValidator(r"\A" + TOKEN.pattern + r"\Z", "Use a reviewed canonical designation token.")])
    wheelbase_designation = models.CharField(max_length=128, null=True, blank=True,
        validators=[RegexValidator(r"\A" + TOKEN.pattern + r"\Z", "Use a reviewed canonical designation token.")])
    body_length_designation = models.CharField(max_length=128, null=True, blank=True,
        validators=[RegexValidator(r"\A" + TOKEN.pattern + r"\Z", "Use a reviewed canonical designation token.")])
    roof_height_designation = models.CharField(max_length=128, null=True, blank=True,
        validators=[RegexValidator(r"\A" + TOKEN.pattern + r"\Z", "Use a reviewed canonical designation token.")])
    door_configuration = models.CharField(max_length=128, null=True, blank=True,
        validators=[RegexValidator(r"\A" + TOKEN.pattern + r"\Z", "Use a reviewed canonical designation token.")])
    side_door_arrangement = models.CharField(max_length=128, null=True, blank=True,
        validators=[RegexValidator(r"\A" + TOKEN.pattern + r"\Z", "Use a reviewed canonical designation token.")])
    body_code = models.CharField(max_length=128, null=True, blank=True,
        validators=[RegexValidator(r"\A" + TOKEN.pattern + r"\Z", "Use a reviewed canonical designation token.")])
    body_code_namespace = models.CharField(max_length=128, null=True, blank=True,
        validators=[RegexValidator(r"\A" + TOKEN.pattern + r"\Z", "Use a reviewed canonical designation token.")])

    objects = FactoryBodyQuerySet.as_manager()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(body_code__isnull=True, body_code_namespace__isnull=True)
                | models.Q(body_code__isnull=False, body_code_namespace__isnull=False),
                name="reference_body_code_pair",
            ),
            models.CheckConstraint(
                condition=(models.Q(body_style__isnull=False)
                    | models.Q(wheelbase_designation__isnull=False)
                    | models.Q(body_length_designation__isnull=False)
                    | models.Q(roof_height_designation__isnull=False)
                    | models.Q(door_configuration__isnull=False)
                    | models.Q(side_door_arrangement__isnull=False)
                    | models.Q(body_code__isnull=False)),
                name="reference_body_has_dimension",
            ),
            *[models.CheckConstraint(
                condition=models.Q(**{field + "__isnull": True}) | ~models.Q(**{field: ""}),
                name="reference_body_nonempty_" + field,
            ) for field in BODY_ATTRIBUTES],
            models.UniqueConstraint(
                models.F("generation"),
                *[Coalesce(field, models.Value("")) for field in BODY_ATTRIBUTES],
                name="reference_body_exact_tuple",
            ),
        ]

    def clean_fields(self, exclude=None):
        for field in BODY_ATTRIBUTES:
            if field in (exclude or ()):
                continue
            value = getattr(self, field)
            if isinstance(value, str) and not value.strip():
                setattr(self, field, None)
            elif value is not None and type(value) is not str:
                raise ValidationError({field: "Expected a canonical designation token, not a measurement."})
        super().clean_fields(exclude=exclude)

    def clean(self):
        super().clean()
        if self.pk and self.vehicle_definitions.exclude(generation_id=self.generation_id).exists():
            raise ValidationError({"generation": "Generation must match every referencing VehicleDefinition."})

    def save(self, *args, **kwargs):
        # Partial attribute saves can validate a tuple different from the persisted tuple.
        if kwargs.get("update_fields") is not None:
            raise ValidationError("Save the complete body configuration for identity validation.")
        with transaction.atomic(using=kwargs.get("using") or self._state.db):
            if self.pk:
                type(self).objects.select_for_update().get(pk=self.pk)
            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        attributes = ", ".join(f"{field}: {getattr(self, field)}" for field in BODY_ATTRIBUTES if getattr(self, field))
        return f"{self.generation} — {attributes}"


class VehicleDefinitionQuerySet(models.QuerySet):
    def publicly_visible(self):
        """Opt-in public boundary; archival/default queries remain unfiltered."""
        return self.filter(
            is_public=True, is_active=True, generation__is_active=True,
            generation__vehicle_model__is_active=True,
            generation__vehicle_model__manufacturer__is_active=True,
        )

    def update(self, **kwargs):
        if "slug" in kwargs:
            raise ValidationError("Correct stored slugs through authorized individual Admin saves.")
        if {"engine", "engine_id"} & kwargs.keys():
            raise ValidationError("Assign Engines through individual validated saves.")
        if (set(FIELDS) | {"generation", "generation_id"}) & kwargs.keys() and self.filter(engine__isnull=False).exists():
            raise ValidationError("Maintain engine-associated vehicle snapshots through individual saves.")
        if {"factory_body_configuration", "factory_body_configuration_id"} & kwargs.keys():
            raise ValidationError("Assign body configurations with instance.save() for scope validation.")
        if {"generation", "generation_id"} & kwargs.keys() and self.filter(factory_body_configuration__isnull=False).exists():
            raise ValidationError("Change generation on body-associated vehicles individually with instance.save().")
        return super().update(**kwargs)

    def bulk_create(self, objs, **kwargs):
        objs = list(objs)
        if kwargs.get("update_fields") is not None:
            kwargs["update_fields"] = tuple(kwargs["update_fields"])
        if kwargs.get("update_conflicts") and "slug" in (kwargs.get("update_fields") or ()):
            raise ValidationError("Bulk conflict updates cannot correct stored slugs.")
        if any(obj.engine_id is not None for obj in objs):
            raise ValidationError("Create engine-associated vehicles through individual validated saves.")
        if kwargs.get("update_conflicts") and (set(FIELDS) | {"engine", "engine_id", "generation", "generation_id"}) & set(kwargs.get("update_fields") or ()):
            raise ValidationError("Engine/generation conflict updates require individual saves.")
        # An incoming null body does not describe the existing conflict target's body.
        if kwargs.get("update_conflicts") and {
            "generation", "generation_id", "factory_body_configuration",
            "factory_body_configuration_id",
        } & set(kwargs.get("update_fields") or ()):
            raise ValidationError("Correct generation/body associations individually with instance.save().")
        if any(obj.factory_body_configuration_id is not None for obj in objs):
            raise ValidationError("Create body-associated vehicles individually with instance.save().")
        return super().bulk_create(objs, **kwargs)


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

    factory_body_configuration = models.ForeignKey(
        FactoryBodyConfiguration, on_delete=models.PROTECT, null=True, blank=True,
        related_name="vehicle_definitions",
    )
    engine = models.ForeignKey(Engine, on_delete=models.PROTECT, null=True, blank=True, related_name="vehicle_definitions")
    objects = VehicleDefinitionQuerySet.as_manager()

    model_year = models.PositiveSmallIntegerField()

    base_msrp = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=(
            "Original manufacturer base price in the configuration's market and model year. "
            "For US vehicles, USD excluding destination/delivery, taxes, registration, "
            "dealer adjustments and optional equipment. Leave unknown prices blank."
        ),
    )

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
            "Human-readable compatibility snapshot; registered Engine properties "
            "are authoritative for new engine-associated construction."
        ),
    )

    engine_displacement_liters = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    engine_cylinders = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)],
    )
    engine_aspiration = models.CharField(max_length=24, null=True, blank=True, choices=list(ASPIRATION.items()))
    fuel_type = models.CharField(max_length=24, null=True, blank=True, choices=list(FUEL.items()))
    electrification_type = models.CharField(
        max_length=24, null=True, blank=True,
        choices=[(key, labels[0]) for key, labels in ELECTRIFICATION.items()],
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
    is_public = models.BooleanField(
        "Visible on public site", default=True,
        help_text="Hide from public selection and Specs without deactivating or deleting this canonical record.",
    )

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
            models.CheckConstraint(condition=models.Q(engine_displacement_liters__isnull=True) | models.Q(engine_displacement_liters__gt=0), name="reference_powertrain_displacement_positive"),
            models.CheckConstraint(
                condition=models.Q(base_msrp__isnull=True) | models.Q(base_msrp__gte=0),
                name="reference_vehicle_base_msrp_nonnegative",
            ),
            models.CheckConstraint(condition=models.Q(engine_cylinders__isnull=True) | models.Q(engine_cylinders__gt=0), name="reference_powertrain_cylinders_positive"),
            *[models.CheckConstraint(condition=models.Q(**{key + "__isnull": True}) | models.Q(**{key + "__in": list(values)}), name="reference_powertrain_" + key) for key, values in TAXONOMIES.items()],
            models.UniqueConstraint(
                fields=("generation", "slug"),
                name=(
                    "reference_unique_vehicle_definition_slug_per_generation"
                ),
            ),
        ]

    def clean_fields(self, exclude=None):
        for key in FIELDS:
            if key not in (exclude or ()) and isinstance(getattr(self, key), bool):
                raise ValidationError({key: "Boolean is not a powertrain value."})
            if getattr(self, key) == "":
                setattr(self, key, None)
        return super().clean_fields(exclude=exclude)

    def clean(self) -> None:
        super().clean()
        for key in FIELDS:
            value = getattr(self, key)
            if value == "":
                setattr(self, key, None)
            elif isinstance(value, bool):
                raise ValidationError({key: "Boolean is not a powertrain value."})

        self._validate_body_scope()
        self._validate_registry_engine()

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

        base = slugify(source)
        if all(getattr(self, key) is not None for key in FIELDS):
            from reference.powertrain import qualified_slug, record_powertrain
            return qualified_slug(base, record_powertrain(self), self.engine_name)
        return base

    def _validate_body_scope(self, generation_id=None, body_id=None):
        generation_id = self.generation_id if generation_id is None else generation_id
        body_id = self.factory_body_configuration_id if body_id is None else body_id
        if body_id is not None and not FactoryBodyConfiguration.objects.filter(
            pk=body_id, generation_id=generation_id,
        ).exists():
            raise ValidationError({"factory_body_configuration": "Body configuration must belong to the vehicle's Generation."})

    def _validate_registry_engine(self, stored=None):
        """Complete unknowns on explicit association; never overwrite known facts."""
        synchronized = set()
        if self.engine_id is None:
            return synchronized
        from reference.powertrain import record_powertrain, validate_powertrain
        try:
            registry = self.engine
        except Engine.DoesNotExist as exc:
            raise ValidationError({"engine": "ENGINE_NOT_REGISTERED: Engine record is unavailable."}) from exc
        if self.generation_id and registry.manufacturer_id != self.generation.vehicle_model.manufacturer_id:
            raise ValidationError({"engine": "Engine manufacturer must match the vehicle manufacturer."})
        if stored is None and self.pk:
            stored = type(self).objects.using(self._state.db).get(pk=self.pk)
        changed = stored is None or stored.engine_id != self.engine_id or any(
            getattr(stored, key) != getattr(self, key) for key in FIELDS)
        if not changed:
            return synchronized
        new_association = stored is None or stored.engine_id != self.engine_id
        values = record_powertrain(registry)
        validate_powertrain(values, complete=True)
        incoming_values = record_powertrain(self)
        validate_powertrain(incoming_values)
        for key in FIELDS:
            incoming = incoming_values[key]
            if (incoming is None and new_association
                    and (stored is None or getattr(stored, key) in (None, ""))):
                setattr(self, key, getattr(registry, key))
                synchronized.add(key)
            elif incoming != values[key]:
                raise ValidationError({key: ValidationError(
                    f"Vehicle snapshot differs from registered Engine. {key}: vehicle {incoming!r}, "
                    f"registered {registry.engine_code} {values[key]!r}. Known values are not overwritten.",
                    code="ENGINE_REGISTRY_CONFLICT",
                )})
        if not self.engine_name and new_association:
            self.engine_name = (stored.engine_name if stored is not None and stored.engine_name else registry.name)
            synchronized.add("engine_name")
        return synchronized

    def save(self, *args, slug_correction_actor=None, **kwargs) -> None:
        using = kwargs.get("using") or self._state.db
        with transaction.atomic(using=using):
            if kwargs.get("update_fields") is not None:
                kwargs["update_fields"] = frozenset(kwargs["update_fields"])
            if self.pk:
                previous = type(self).objects.using(using).select_for_update().filter(pk=self.pk).first()
                saving_slug = kwargs.get("update_fields") is None or "slug" in kwargs["update_fields"]
                if previous is not None and saving_slug and previous.slug != self.slug:
                    if not (slug_correction_actor and slug_correction_actor.is_active
                            and slug_correction_actor.is_staff
                            and slug_correction_actor.has_perm("reference.change_vehicledefinition")):
                        raise ValidationError({"slug": "Stored slug corrections require an authorized administrator."})
                    self._meta.get_field("slug").clean(self.slug, self)
                    if not self.slug:
                        raise ValidationError({"slug": "A corrected slug cannot be empty."})
                    if type(self).objects.using(using).filter(generation_id=self.generation_id, slug=self.slug).exclude(pk=self.pk).exists():
                        raise ValidationError({"slug": "This generation already has that slug."})
            generation_id, body_id = self.generation_id, self.factory_body_configuration_id
            fields = kwargs.get("update_fields")
            if fields is not None:
                fields = frozenset(fields)
                kwargs["update_fields"] = fields
            if fields is not None and self.pk:
                stored = type(self).objects.using(using).get(pk=self.pk)
                if not {"generation", "generation_id"} & fields:
                    generation_id = stored.generation_id
                if not {"factory_body_configuration", "factory_body_configuration_id"} & fields:
                    body_id = stored.factory_body_configuration_id
            if body_id is not None:
                body = FactoryBodyConfiguration.objects.using(using).select_for_update().filter(pk=body_id).first()
                if body is None or body.generation_id != generation_id:
                    raise ValidationError({"factory_body_configuration": "Body configuration must belong to the vehicle's Generation."})
            # Validate the effective saved snapshot, not omitted dirty instance fields.
            effective = self
            if fields is not None and self.pk:
                effective = stored
                for field in self._meta.concrete_fields:
                    if field.name in fields or field.attname in fields:
                        setattr(effective, field.attname, getattr(self, field.attname))
            if effective.engine_id is not None:
                try:
                    effective.engine = Engine.objects.using(using).select_for_update().get(pk=effective.engine_id)
                except Engine.DoesNotExist as exc:
                    raise ValidationError({"engine": "ENGINE_NOT_REGISTERED: Engine record is unavailable."}) from exc
                synchronized = effective._validate_registry_engine()
                if fields is not None and synchronized:
                    for key in synchronized:
                        setattr(self, key, getattr(effective, key))
                    kwargs["update_fields"] = fields | synchronized
            if not self.slug:
                self.slug = self.build_slug()
            super().save(*args, **kwargs)

    @property
    def engine_description(self):
        return engine_label(self) if self.engine_name else ""

    def __str__(self) -> str:
        model = self.generation.vehicle_model
        body_designation = ""
        if (self.model_year in (2024, 2025, 2026) and self.generation.slug == "jl"
                and model.slug == "wrangler" and model.manufacturer.slug == "jeep"
                and self.factory_body_configuration_id is not None):
            body_designation = {"two-door": "2-Door", "four-door": "4-Door"}.get(
                self.factory_body_configuration.door_configuration, "",
            )
        details = [
            str(self.model_year),
            str(model),
            self.trim_name,
            body_designation,
            self.engine_description,
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

# B2 models live in the specification boundary; importing registers them with
# the existing Reference application without changing baseline model semantics.
from reference.specifications.models import (  # noqa: E402,F401
    SpecificationUnitRegistry, EvidenceDocument, EvidenceAssertionReference,
    SpecificationDefinition, SpecificationDefinitionRevision,
    SpecificationDefinitionDependency, SpecificationAssertion,
    SpecificationCatalogue, SpecificationCatalogueRevision,
    SpecificationCatalogueMembership, SpecificationCatalogueCoverage,
    SpecificationEvidenceLink, SpecificationPublicationReceipt,
    TransmissionDescription, TransmissionDescriptionRevision, TransmissionEngineeringAssertion,
    TransmissionOffering, TransmissionOfferingRevision,
    EquipmentItem, EquipmentItemRevision, EquipmentOffering, EquipmentOfferingRevision,
    CompatibilityRule, CompatibilityRuleRevision,
)
