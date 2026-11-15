import uuid

from django.db import models
from django.core.exceptions import ValidationError


class UUIDModel(models.Model):
    """
    Abstract model mixin providing a universally unique identifier (UUID).

    Provides a stable external identifier separate from internal integer primary keys.
    """

    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    """
    Abstract model mixin providing creation and modification timestamps.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimestampedModel):
    """
    Abstract base model combining UUID identity and timestamp tracking.
    """

    class Meta:
        abstract = True


class HomepageVehiclePlatform(BaseModel):
    """Homepage presentation selection, independent of canonical model identity."""

    vehicle_model = models.OneToOneField(
        "reference.VehicleModel", on_delete=models.PROTECT,
        related_name="homepage_platform",
    )
    display_order = models.PositiveIntegerField(default=0)
    is_enabled = models.BooleanField(default=True)
    image_generation = models.ForeignKey(
        "reference.Generation", on_delete=models.PROTECT, null=True, blank=True,
        related_name="homepage_image_selections",
        help_text="Image only: select a generation of this vehicle model. The card still links to the model.",
    )

    class Meta:
        ordering = ("display_order", "pk")

    def clean(self):
        super().clean()
        if self.image_generation_id and self.vehicle_model_id:
            if self.image_generation.vehicle_model_id != self.vehicle_model_id:
                raise ValidationError({"image_generation": "Image generation must belong to the selected vehicle model."})

    def save(self, *args, **kwargs):
        effective = self
        fields = kwargs.get("update_fields")
        if fields is not None:
            fields = frozenset(fields)
            kwargs["update_fields"] = fields
            if self.pk:
                effective = type(self).objects.using(kwargs.get("using") or self._state.db).get(pk=self.pk)
                for field in self._meta.concrete_fields:
                    if field.name in fields or field.attname in fields:
                        setattr(effective, field.attname, getattr(self, field.attname))
        effective.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.vehicle_model)
