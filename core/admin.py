from django.contrib import admin

from .models import HomepageVehiclePlatform


@admin.register(HomepageVehiclePlatform)
class HomepageVehiclePlatformAdmin(admin.ModelAdmin):
    list_display = ("vehicle_model", "display_order", "is_enabled", "image_generation")
    list_editable = ("display_order", "is_enabled")
    list_filter = ("is_enabled",)
    search_fields = ("vehicle_model__name", "vehicle_model__manufacturer__name")
    autocomplete_fields = ("vehicle_model",)
    readonly_fields = ("uuid", "created_at", "updated_at")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "image_generation":
            from reference.models import Generation
            model_id = request.POST.get("vehicle_model") if request.method == "POST" else None
            if not model_id and request.resolver_match:
                object_id = request.resolver_match.kwargs.get("object_id")
                if str(object_id).isdigit():
                    model_id = HomepageVehiclePlatform.objects.filter(pk=object_id).values_list("vehicle_model_id", flat=True).first()
            kwargs["queryset"] = Generation.objects.filter(vehicle_model_id=model_id) if str(model_id).isdigit() else Generation.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
