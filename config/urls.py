from config import views
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

handler404 = "config.views.custom_404"
handler500 = "config.views.custom_500"

urlpatterns = [
    path(
        "",
        TemplateView.as_view(template_name="home.html"),
        name="home",
    ),
    path(
        "about/",
        views.about,
        name="about",
    ),
    path("admin/", admin.site.urls),
    path(
        "vehicles/",
        include("reference.urls"),
    ),
]