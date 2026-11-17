from django.urls import path

from . import kardex_api

urlpatterns = [
    path("<int:pk>/", kardex_api.kardex),
]
