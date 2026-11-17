from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from fleet import dashboard_api

admin.site.site_header = "Administración"
admin.site.site_title = "ROMEX"
admin.site.index_title = "Panel de administración"
# The backend has no public site, so hide the "View site" link
admin.site.site_url = None


def health(request):
    """Simple endpoint to verify the API is up."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/", include("accounts.urls")),
    path("api/ubicaciones/", include("locations.urls")),
    path("api/trabajadores/", include("accounts.workers_urls")),
    path("api/unidades/", include("fleet.units_urls")),
    path("api/reportes-fallas/", include("fleet.reports_urls")),
    path("api/diagnosticos/", include("fleet.diagnoses_urls")),
    path("api/mantenimientos/", include("fleet.maintenances_urls")),
    path("api/checklists/", include("fleet.checklists_urls")),
    path("api/kardex/", include("fleet.kardex_urls")),
    path("api/refacciones/", include("fleet.spare_parts_urls")),
    path("api/preventivo/", include("fleet.preventive_urls")),
    path("api/bitacora/", include("audit.urls")),
    path("api/dashboard/", dashboard_api.dashboard),
    path("api/notificaciones/", include("notifications.urls")),
]
