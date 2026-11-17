from django.urls import path

from . import units_api

urlpatterns = [
    path("", units_api.units),
    path("catalogos/", units_api.catalogs),
    path("<int:pk>/", units_api.unit_detail),
]
