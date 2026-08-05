from django.shortcuts import render


def about(request):
    """Render the About page explaining project mission and data philosophy."""
    return render(request, "about.html")


def custom_404(request, exception=None):
    """Render a resilient custom 404 error page."""
    return render(request, "404.html", status=404)


def custom_500(request):
    """Render a resilient custom 500 error page."""
    return render(request, "500.html", status=500)
