from django.urls import path

from . import diagnoses_api

urlpatterns = [
    path("", diagnoses_api.diagnoses),
    path("catalogos/", diagnoses_api.catalogs),
    path("<int:pk>/", diagnoses_api.diagnosis_detail),
]
