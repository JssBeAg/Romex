"""
Notifications of the logged-in user.

  GET  /api/notificaciones/             page of notifications (?unread=1, page, page_size)
  GET  /api/notificaciones/resumen/     {"unread": n}  (the menu asks this every minute)
  POST /api/notificaciones/leer/        mark as read: {"ids": [1, 2]} or {} for all
  POST /api/notificaciones/limpiar/     delete the ones already read
"""

import json

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from accounts.roles import MANAGER_ROLE
from common.listing import list_response

from .models import Notification
from .service import sync_preventive

SORTS = {"date": ("created_at",)}


def login_required_json(view):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "No has iniciado sesión"}, status=401)
        return view(request, *args, **kwargs)

    wrapper.__name__ = view.__name__
    return wrapper


def serialize(n):
    return {
        "id": n.pk,
        "kind": n.kind,
        "kind_label": n.get_kind_display(),
        "message": n.message,
        "link": n.link,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat(),
    }


def refresh(user):
    """Preventive alerts are derived, so they are generated when a manager looks."""
    if user.role_id and user.role.name == MANAGER_ROLE:
        sync_preventive()


@login_required_json
@require_GET
def notifications(request):
    refresh(request.user)
    queryset = Notification.objects.filter(user=request.user)
    if request.GET.get("unread") == "1":
        queryset = queryset.filter(is_read=False)
    kind = request.GET.get("kind", "")
    if kind in dict(Notification.KINDS):
        queryset = queryset.filter(kind=kind)
    unread = Notification.objects.filter(user=request.user, is_read=False).count()
    return list_response(
        request,
        queryset,
        key="notifications",
        serialize=serialize,
        sorts=SORTS,
        default="-date",
        extra={"unread": unread, "kinds": [{"id": k, "label": label} for k, label in Notification.KINDS]},
    )


@login_required_json
@require_GET
def summary(request):
    refresh(request.user)
    return JsonResponse({"unread": Notification.objects.filter(user=request.user, is_read=False).count()})


@login_required_json
@require_POST
def mark_read(request):
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    queryset = Notification.objects.filter(user=request.user, is_read=False)
    ids = data.get("ids")
    if ids is not None:
        if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
            return JsonResponse({"error": "Datos no válidos"}, status=400)
        queryset = queryset.filter(pk__in=ids)
    changed = queryset.update(is_read=True)
    return JsonResponse({"updated": changed})


@login_required_json
@require_POST
def clear_read(request):
    deleted, _ = Notification.objects.filter(user=request.user, is_read=True).delete()
    return JsonResponse({"deleted": deleted})
