from django.shortcuts import render
from reference.services import get_homepage_context


def home(request):
    """Render the approved RigArchive homepage."""
    context = get_homepage_context(request)
    return render(request, "home.html", context)


def about(request):
    """Render the about view."""
    return render(request, "about.html")


def custom_404(request, exception):
    """Custom 404 handler returning HTTP 404 status code."""
    return render(request, "404.html", status=404)


def custom_500(request):
    """Custom 500 handler returning HTTP 500 status code."""
    return render(request, "500.html", status=500)
