from django.urls import path

from . import kardex_api, kardex_sections

urlpatterns = [
    path("<int:pk>/", kardex_api.kardex),
    path("<int:pk>/linea-de-tiempo/", kardex_api.timeline),
    path("<int:pk>/mantenimientos/", kardex_sections.maintenances),
    path("<int:pk>/fallas/", kardex_sections.faults),
    path("<int:pk>/checklists/", kardex_sections.checklists),
    path("<int:pk>/refacciones/", kardex_sections.parts),
    path("<int:pk>/operadores/", kardex_sections.people),
    path("<int:pk>/cambios/", kardex_sections.changes),
]
