from django.urls import path

from . import reports_api

urlpatterns = [
    path("", reports_api.reports),
    path("catalogos/", reports_api.catalogs),
    path("<int:pk>/", reports_api.report_detail),
    path("<int:pk>/mecanicos/", reports_api.report_mechanics),
    path("<int:pk>/mecanicos/<int:assignment_id>/", reports_api.report_mechanic_detail),
    path("<int:pk>/evidencias/<int:evidence_id>/", reports_api.evidence_file),
]
