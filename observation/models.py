from django.conf import settings
from django.db import models

from core.models import BaseModel


class Observation(BaseModel):
    """
    Represents a recorded statement about a vehicle configuration in the Observation Domain.

    Captures information entering the archive together with capture context and provenance,
    without modifying canonical reference data.
    """

    vehicle_definition = models.ForeignKey(
        "reference.VehicleDefinition",
        on_delete=models.PROTECT,
        related_name="observations",
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="observations",
    )

    title = models.CharField(max_length=255)
    description = models.TextField()

    observed_on = models.DateField(
        null=True,
        blank=True,
        help_text="Optional date when the real-world observation occurred.",
    )

    source_notes = models.TextField(
        blank=True,
        help_text="Optional notes describing capture context, methodology, or source attribution.",
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title
