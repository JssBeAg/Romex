from django.urls import path

from . import workers_api

urlpatterns = [
    path("", workers_api.workers),
    path("catalogos/", workers_api.catalogs),
    path("<int:pk>/", workers_api.worker_detail),
    path("<int:pk>/foto/", workers_api.worker_photo),
]
