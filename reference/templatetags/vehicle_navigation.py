from django import template

from reference.services import discover_manufacturers

register = template.Library()


@register.inclusion_tag("reference/partials/vehicle_quick_selector.html")
def vehicle_quick_selector():
    """Use the selector's active-model policy, without image/Generation queries."""
    return {"quick_manufacturers": discover_manufacturers()}
