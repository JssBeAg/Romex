from django.urls import path

from . import api

urlpatterns = [
    path("estados/", api.states),
    path("municipios/", api.municipalities),
]
