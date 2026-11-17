from django.urls import path

from . import checklists_api

urlpatterns = [
    path("", checklists_api.checklists),
    path("catalogos/", checklists_api.catalogs),
    path("<int:pk>/", checklists_api.checklist_detail),
]
