import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.urls import reverse


class Manufacturer(models.Model):
    """
    Represents a vehicle manufacturer in the Reference Domain.

    A manufacturer is the highest level of the canonical vehicle
    hierarchy and owns one or more vehicle models.
    """

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

class VehicleModel(models.Model):
    """
    Represents a named vehicle model produced by a manufacturer.

    Examples include Toyota 4Runner, Ford Transit, and Jeep Wrangler.
    """

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

class Generation(models.Model):
    """
    Represents a recognized generation of a vehicle model.

    A generation groups vehicle definitions that share a meaningful
    manufacturer-defined or historically recognized product lifecycle.
    """

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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

class VehicleDefinition(models.Model):
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
        TWO_WHEEL_DRIVE = "2WD", "Two-wheel drive"
        FOUR_WHEEL_DRIVE = "4WD", "Four-wheel drive"
        ALL_WHEEL_DRIVE = "AWD", "All-wheel drive"
        UNKNOWN = "UNK", "Unknown"

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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