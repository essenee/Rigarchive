from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Represents an authenticated RigArchive user.

    The model initially preserves Django's standard authentication behavior
    while providing a stable foundation for future contributor functionality.
    """

    display_name = models.CharField(max_length=150, blank=True)

    is_contributor = models.BooleanField(
        default=False,
        help_text="Designates whether this account may participate in contribution workflows.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.display_name or self.username