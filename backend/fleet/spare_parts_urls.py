from django.urls import path

from . import spare_parts_api

urlpatterns = [
    path("", spare_parts_api.spare_parts),
    path("<int:pk>/", spare_parts_api.spare_part_detail),
    path("<int:pk>/movimientos/", spare_parts_api.spare_part_movements),
    path("<int:pk>/foto/", spare_parts_api.spare_part_photo),
]
