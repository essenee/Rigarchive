from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify

from core.models import BaseModel


class MeasurementDefinition(BaseModel):
    """
    Represents WHAT is being measured as a reusable concept across vehicle generations.

    Units belong exclusively to MeasurementResult instances.
    """

    class Category(models.TextChoices):
        CARGO = "cargo", "Cargo Area"

    name = models.CharField(max_length=100, unique=True)

    slug = models.SlugField(
        max_length=120,
        unique=True,
        editable=False,
        blank=True,
    )

    category = models.CharField(
        max_length=50,
        choices=Category.choices,
        default=Category.CARGO,
    )

    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class ApplicabilityFeature(BaseModel):
    """
    Represents a controlled measurement-relevant physical feature type (e.g. Sunroof).
    """

    name = models.CharField(max_length=100, unique=True)

    slug = models.SlugField(
        max_length=120,
        unique=True,
        editable=False,
        blank=True,
    )

    description = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class ApplicabilityState(BaseModel):
    """
    Represents an allowed physical state for an ApplicabilityFeature (e.g. Present / Absent).
    """

    feature = models.ForeignKey(
        ApplicabilityFeature,
        on_delete=models.PROTECT,
        related_name="states",
    )

    name = models.CharField(max_length=100)

    slug = models.SlugField(
        max_length=120,
        editable=False,
        blank=True,
    )

    class Meta:
        ordering = ("feature__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("feature", "name"),
                name="measurements_unique_state_name_per_feature",
            ),
            models.UniqueConstraint(
                fields=("feature", "slug"),
                name="measurements_unique_state_slug_per_feature",
            ),
        ]

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.feature.name}: {self.name}"


class MeasurementResult(BaseModel):
    """
    Represents an individual measured numeric value for a MeasurementDefinition
    within a reference.Generation context.
    """

    class Unit(models.TextChoices):
        INCHES = "in", "Inches"
        MILLIMETERS = "mm", "Millimeters"
        CENTIMETERS = "cm", "Centimeters"

    generation = models.ForeignKey(
        "reference.Generation",
        on_delete=models.PROTECT,
        related_name="measurement_results",
    )

    definition = models.ForeignKey(
        MeasurementDefinition,
        on_delete=models.PROTECT,
        related_name="results",
    )

    value = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    unit = models.CharField(
        max_length=20,
        choices=Unit.choices,
        default=Unit.INCHES,
    )

    notes = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("generation", "definition__name")

    @property
    def is_generation_wide(self) -> bool:
        if self.pk:
            return not self.conditions.exists()
        return True

    @property
    def applicability_summary(self) -> str:
        if self.pk and self.conditions.exists():
            conditions_list = [
                f"{cond.state.feature.name}: {cond.state.name}"
                for cond in self.conditions.select_related("state__feature")
            ]
            return " AND ".join(conditions_list)
        return "Generation-wide"

    def __str__(self) -> str:
        return f"{self.generation} — {self.definition.name}: {self.value} {self.unit}"


class MeasurementResultCondition(BaseModel):
    """
    Associates a MeasurementResult with a required ApplicabilityState.
    Multiple conditions on a single result are evaluated conjunctively (AND).
    """

    result = models.ForeignKey(
        MeasurementResult,
        on_delete=models.CASCADE,
        related_name="conditions",
    )

    state = models.ForeignKey(
        ApplicabilityState,
        on_delete=models.PROTECT,
        related_name="result_conditions",
    )

    class Meta:
        ordering = ("result", "state__feature__name")
        constraints = [
            models.UniqueConstraint(
                fields=("result", "state"),
                name="measurements_unique_condition_per_result",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.result_id and self.state_id:
            existing_feature_states = MeasurementResultCondition.objects.filter(
                result=self.result,
                state__feature=self.state.feature,
            )
            if self.pk:
                existing_feature_states = existing_feature_states.exclude(pk=self.pk)
            if existing_feature_states.exists():
                raise ValidationError(
                    f"Result already has a condition for feature '{self.state.feature.name}'. "
                    "A single MeasurementResult cannot contain multiple states of the same feature."
                )

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.result} Requires [{self.state}]"
