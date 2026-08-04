
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class RigArchiveUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "RigArchive",
            {
                "fields": (
                    "display_name",
                    "is_contributor",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "RigArchive",
            {
                "fields": (
                    "display_name",
                    "is_contributor",
                )
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at")

    list_display = (
        "username",
        "email",
        "display_name",
        "is_contributor",
        "is_staff",
        "is_active",
    )

    list_filter = (
        "is_contributor",
        "is_staff",
        "is_superuser",
        "is_active",
    )

    search_fields = (
        "username",
        "email",
        "display_name",
    )