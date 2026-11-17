from django.urls import path

from . import maintenances_api

urlpatterns = [
    path("", maintenances_api.maintenances),
    path("catalogos/", maintenances_api.catalogs),
    path("<int:pk>/", maintenances_api.maintenance_detail),
]
