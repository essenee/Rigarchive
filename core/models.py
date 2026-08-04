import uuid

from django.db import models


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
