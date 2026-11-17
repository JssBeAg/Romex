from django.urls import path

from . import preventive_api

urlpatterns = [
    path("vencimientos/", preventive_api.due),
    path("planes/", preventive_api.plans),
    path("planes/<int:pk>/", preventive_api.plan_detail),
    path("catalogos/", preventive_api.catalogs),
]
