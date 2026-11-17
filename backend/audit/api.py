"""
Audit trail API (read only, managers only).

  GET /api/bitacora/            -> a page of lines, newest first. Filters (all optional):
                                   q (matrícula, name or record), user_id, action, table,
                                   record_id, date_from, date_to (YYYY-MM-DD), page, page_size
  GET /api/bitacora/catalogos/  -> options of the filters
There is no way to create, change or delete a line through the API. A manager does not see
the private activity of the administrators (see visibility.py).
"""

import datetime

from django.contrib.auth import get_user_model
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from accounts.permissions import manager_required
from common import pdf
from common.listing import filter_lines, order_by, wants_pdf

from .models import AuditLog
from .registry import table_labels
from .visibility import ADMIN_ONLY_TABLES, administrators, visible_to_manager

PAGE_SIZE = 25
MAX_PAGE_SIZE = 100
PDF_MAX_ROWS = 2000  # a PDF of the whole trail would be enormous: it keeps the newest lines

SORTS = {
    "timestamp": ("timestamp",),
    "user": ("user_enrollment_id",),
    "action": ("action",),
    "table": ("table_name",),
}


def parse_date(text):
    try:
        return datetime.date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def serialize_entry(entry, labels):
    return {
        "id": entry.pk,
        "timestamp": entry.timestamp.isoformat(),
        "user_id": entry.user_id,
        "enrollment_id": entry.user_enrollment_id,
        "user_name": entry.user_name,
        "role": entry.user_role,
        "action": entry.action,
        "action_label": entry.get_action_display(),
        "table": entry.table_name,
        "table_label": labels.get(entry.table_name, entry.table_name),
        "record_id": entry.record_id,
        "record": entry.record,
        "changes": [
            {"field": field, "old": values[0], "new": values[1]}
            for field, values in (entry.changes or {}).items()
        ],
        "ip_address": entry.ip_address,
    }


@require_GET
@manager_required
def entries(request):
    params = request.GET
    queryset = visible_to_manager(AuditLog.objects.all())

    text = params.get("q", "").strip()
    if text:
        queryset = queryset.filter(
            Q(user_enrollment_id__icontains=text)
            | Q(user_name__icontains=text)
            | Q(record__icontains=text)
        )
    if params.get("user_id", "").isdigit():
        queryset = queryset.filter(user_id=int(params["user_id"]))
    if params.get("action") in dict(AuditLog.ACTIONS):
        queryset = queryset.filter(action=params["action"])
    if params.get("table"):
        queryset = queryset.filter(table_name=params["table"])
    if params.get("record_id", "").isdigit():
        queryset = queryset.filter(record_id=int(params["record_id"]))
    date_from = parse_date(params.get("date_from"))
    if date_from:
        queryset = queryset.filter(timestamp__date__gte=date_from)
    date_to = parse_date(params.get("date_to"))
    if date_to:
        queryset = queryset.filter(timestamp__date__lte=date_to)

    queryset = order_by(queryset, request, SORTS, "-timestamp")
    labels = table_labels()

    if wants_pdf(request):
        shown = queryset[:PDF_MAX_ROWS]
        rows = []
        for entry in shown:
            item = serialize_entry(entry, labels)
            changes = "; ".join(
                f"{c['field']}: {'-' if c['old'] is None else c['old']} -> {'-' if c['new'] is None else c['new']}"
                for c in item["changes"]
            )
            rows.append(
                [
                    timezone.localtime(entry.timestamp).strftime("%d/%m/%Y %H:%M:%S"),
                    f"{item['user_name']} ({item['enrollment_id']})",
                    item["role"] or "-",
                    item["action_label"],
                    item["table_label"] or "-",
                    item["record"] or "-",
                    changes or "-",
                ]
            )
        note = [f"Se muestran las {PDF_MAX_ROWS} líneas más recientes"] if queryset.count() > PDF_MAX_ROWS else []
        return pdf.list_pdf(
            request.user,
            "Bitácora de auditoría",
            filter_lines(
                ("Búsqueda", text),
                ("Acción", dict(AuditLog.ACTIONS).get(params.get("action"), "")),
                ("Tabla", labels.get(params.get("table", ""), "")),
                ("Desde", params.get("date_from", "")),
                ("Hasta", params.get("date_to", "")),
            )
            + note,
            [("Fecha y hora", 1.7), ("Usuario", 2.2), ("Rol", 1.1), ("Acción", 1.8), ("Tabla", 1.6), ("Registro", 2.6), ("Cambios", 4.5)],
            rows,
        )

    try:
        size = min(max(int(params.get("page_size", PAGE_SIZE)), 1), MAX_PAGE_SIZE)
        number = max(int(params.get("page", 1)), 1)
    except ValueError:
        size, number = PAGE_SIZE, 1
    paginator = Paginator(queryset, size)
    try:
        page = paginator.page(number)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    return JsonResponse(
        {
            "entries": [serialize_entry(e, labels) for e in page.object_list],
            "total": paginator.count,
            "page": page.number,
            "pages": paginator.num_pages,
        }
    )


@require_GET
@manager_required
def catalogs(request):
    User = get_user_model()
    user_ids = visible_to_manager(AuditLog.objects.all()).exclude(user__isnull=True).values("user_id")
    # Administrators are never offered in the "user" filter
    users = (
        User.objects.filter(pk__in=user_ids)
        .exclude(pk__in=administrators().values("pk"))
        .order_by("enrollment_id")
    )
    return JsonResponse(
        {
            "actions": [{"id": value, "label": label} for value, label in AuditLog.ACTIONS],
            "tables": [
                {"id": table, "label": label}
                for table, label in sorted(table_labels().items(), key=lambda item: item[1])
                if table not in ADMIN_ONLY_TABLES
            ],
            "users": [
                {
                    "id": u.pk,
                    "label": f"{u.first_name} {u.paternal_surname} ({u.enrollment_id})",
                }
                for u in users
            ],
        }
    )
