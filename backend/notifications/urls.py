from django.urls import path

from . import api

urlpatterns = [
    path("", api.notifications),
    path("resumen/", api.summary),
    path("leer/", api.mark_read),
    path("limpiar/", api.clear_read),
]
