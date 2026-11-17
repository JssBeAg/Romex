"""
Dashboard of indicators for the manager.

  GET /api/dashboard/?months=6   (3, 6 or 12 months; the default is 6)
  GET /api/dashboard/?months=6&format=pdf

Everything is calculated from the records (nothing is stored), so it always agrees with the
lists. "Period" means the last N calendar months including the current one.
"""

import datetime
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from accounts.models import User
from accounts.permissions import manager_required
from common import pdf


from .inventory import with_stock
from .models import (
    FaultReport,
    FaultReportStatus,
    Maintenance,
    MaintenanceSparePart,
    ReportMechanic,
    ReportStatusChange,
    Unit,
)
from .preventive import due_rows, summary
from .report_status import CLOSED_STATUSES

MONTH_NAMES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
PERIODS = (3, 6, 12)
TOP = 5


def month_starts(count, today):
    """First day of each of the last `count` months, oldest first."""
    year, month = today.year, today.month
    months = []
    for _ in range(count):
        months.append(datetime.date(year, month, 1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(months))


def month_label(day):
    return f"{MONTH_NAMES[day.month - 1]} {str(day.year)[2:]}"


def by_month(rows, months, field, value="n"):
    """Rows like {"m": date, "n": 3} -> one number per month (zero when there is no row)."""
    found = {row["m"].date() if isinstance(row["m"], datetime.datetime) else row["m"]: row[value] for row in rows}
    return [found.get(m, 0) for m in months]


def money(value):
    return str((value or Decimal("0")).quantize(Decimal("0.01")))


def resolution_days(start):
    """Average days between the date of a report and the moment it was closed, in the period."""
    closed = ReportStatusChange.objects.filter(
        status__name__in=CLOSED_STATUSES, changed_at__date__gte=start
    ).select_related("fault_report")
    first_close = {}
    for change in closed.order_by("changed_at"):
        first_close.setdefault(change.fault_report_id, change)
    days = [
        max(0, (timezone.localtime(c.changed_at).date() - c.fault_report.date).days)
        for c in first_close.values()
    ]
    return round(sum(days) / len(days), 1) if days else None


def build(months_count):
    today = timezone.localdate()
    months = month_starts(months_count, today)
    start = months[0]

    reports = FaultReport.objects.filter(date__gte=start)
    maintenances = Maintenance.objects.filter(date__gte=start)
    open_reports = FaultReport.objects.exclude(status__name__in=CLOSED_STATUSES)

    # Open reports with nobody assigned right now
    assigned_ids = ReportMechanic.objects.filter(end_date__isnull=True).values("fault_report_id")
    unassigned = open_reports.exclude(pk__in=assigned_ids).count()

    rows = due_rows()
    preventive = summary(rows)

    cost = maintenances.aggregate(total=Sum("total_cost"), n=Count("id"))
    low_parts = [p for p in with_stock().filter(is_active=True, min_stock__gt=0) if p.stock <= p.min_stock]

    per_status = {
        row["status__name"]: row["n"]
        for row in FaultReport.objects.values("status__name").annotate(n=Count("id"))
    }
    statuses = [
        {"label": s.name, "count": per_status.get(s.name, 0), "closed": s.name in CLOSED_STATUSES}
        for s in FaultReportStatus.objects.order_by("order", "pk")
    ]

    month_filter = lambda qs: qs.annotate(m=TruncMonth("date")).values("m").annotate(n=Count("id")).order_by("m")
    cost_by_month = (
        maintenances.annotate(m=TruncMonth("date")).values("m").annotate(total=Sum("total_cost")).order_by("m")
    )
    prev_by_month = month_filter(maintenances.filter(service_type__name="Preventivo"))
    corr_by_month = month_filter(maintenances.filter(service_type__name="Correctivo"))

    top_cost = (
        maintenances.values("unit__economic_number")
        .annotate(total=Sum("total_cost"), n=Count("id"))
        .order_by("-total", "unit__economic_number")[:TOP]
    )
    top_reports = (
        reports.values("unit__economic_number").annotate(n=Count("id")).order_by("-n", "unit__economic_number")[:TOP]
    )
    top_parts = (
        MaintenanceSparePart.objects.filter(maintenance__date__gte=start)
        .values("spare_part__name")
        .annotate(n=Sum("quantity"))
        .order_by("-n", "spare_part__name")[:TOP]
    )
    workload = (
        ReportMechanic.objects.filter(end_date__isnull=True)
        .exclude(fault_report__status__name__in=CLOSED_STATUSES)
        .values("mechanic__first_name", "mechanic__paternal_surname", "mechanic__enrollment_id")
        .annotate(n=Count("id"))
        .order_by("-n", "mechanic__enrollment_id")
    )

    return {
        "months": months_count,
        "period": {"from": start.isoformat(), "to": today.isoformat()},
        "cards": {
            "open_reports": open_reports.count(),
            "unassigned_reports": unassigned,
            "reports_in_period": reports.count(),
            "avg_resolution_days": resolution_days(start),
            "maintenances_in_period": cost["n"],
            "cost_in_period": money(cost["total"]),
            "avg_cost": money((cost["total"] or Decimal("0")) / cost["n"]) if cost["n"] else "0.00",
            "active_units": Unit.objects.filter(is_active=True).count(),
            "inactive_units": Unit.objects.filter(is_active=False).count(),
            "low_stock_parts": len(low_parts),
            "preventive_overdue": preventive["overdue"],
            "preventive_upcoming": preventive["upcoming"],
            "active_workers": User.objects.filter(is_active=True, is_superuser=False).count(),
        },
        "monthly": {
            "labels": [month_label(m) for m in months],
            "reports": by_month(month_filter(reports), months, "date"),
            "preventive": by_month(prev_by_month, months, "date"),
            "corrective": by_month(corr_by_month, months, "date"),
            "cost": [float(v) for v in by_month(cost_by_month, months, "date", "total")],
        },
        "report_statuses": statuses,
        "top_units_by_cost": [
            {"unit": r["unit__economic_number"], "total": money(r["total"]), "count": r["n"]} for r in top_cost
        ],
        "top_units_by_reports": [{"unit": r["unit__economic_number"], "count": r["n"]} for r in top_reports],
        "top_parts": [{"part": r["spare_part__name"], "pieces": r["n"]} for r in top_parts],
        "mechanic_workload": [
            {
                "mechanic": f"{r['mechanic__first_name']} {r['mechanic__paternal_surname']} ({r['mechanic__enrollment_id']})",
                "open_reports": r["n"],
            }
            for r in workload
        ],
        "low_stock": [
            {"id": p.pk, "name": p.name, "stock": p.stock, "min_stock": p.min_stock}
            for p in sorted(low_parts, key=lambda p: p.stock)[:TOP]
        ],
    }


def to_pdf(user, data):
    c = data["cards"]
    period = f"{data['period']['from']} al {data['period']['to']} (últimos {data['months']} meses)"
    sections = [
        {
            "heading": "Indicadores",
            "pairs": [
                ("Reportes abiertos", c["open_reports"]),
                ("Abiertos sin mecánico", c["unassigned_reports"]),
                ("Reportes en el periodo", c["reports_in_period"]),
                ("Días promedio para cerrar", c["avg_resolution_days"] if c["avg_resolution_days"] is not None else "-"),
                ("Mantenimientos en el periodo", c["maintenances_in_period"]),
                ("Costo en el periodo (MXN)", c["cost_in_period"]),
                ("Costo promedio (MXN)", c["avg_cost"]),
                ("Unidades activas / inactivas", f"{c['active_units']} / {c['inactive_units']}"),
                ("Refacciones con stock bajo", c["low_stock_parts"]),
                ("Preventivo vencido / próximo", f"{c['preventive_overdue']} / {c['preventive_upcoming']}"),
            ],
        },
        {
            "heading": "Por mes",
            "columns": [("Mes", 1), ("Reportes", 1), ("Preventivos", 1), ("Correctivos", 1), ("Costo (MXN)", 1.4)],
            "rows": [
                [data["monthly"]["labels"][i], data["monthly"]["reports"][i], data["monthly"]["preventive"][i],
                 data["monthly"]["corrective"][i], f"{data['monthly']['cost'][i]:.2f}"]
                for i in range(len(data["monthly"]["labels"]))
            ],
        },
        {
            "heading": "Reportes por estatus (hoy)",
            "columns": [("Estatus", 3), ("Reportes", 1)],
            "rows": [[s["label"], s["count"]] for s in data["report_statuses"]],
        },
        {
            "heading": "Unidades con más costo de mantenimiento",
            "columns": [("Unidad", 2), ("Mantenimientos", 1), ("Costo (MXN)", 1.4)],
            "rows": [[r["unit"], r["count"], r["total"]] for r in data["top_units_by_cost"]],
        },
        {
            "heading": "Unidades con más reportes",
            "columns": [("Unidad", 2), ("Reportes", 1)],
            "rows": [[r["unit"], r["count"]] for r in data["top_units_by_reports"]],
        },
        {
            "heading": "Refacciones más usadas",
            "columns": [("Refacción", 3), ("Piezas", 1)],
            "rows": [[r["part"], r["pieces"]] for r in data["top_parts"]],
        },
        {
            "heading": "Carga de mecánicos (reportes abiertos asignados)",
            "columns": [("Mecánico", 3), ("Reportes", 1)],
            "rows": [[r["mechanic"], r["open_reports"]] for r in data["mechanic_workload"]],
        },
    ]
    return pdf.sheet_pdf(user, "Dashboard e indicadores", f"Periodo: {period}", sections)


@manager_required
@require_GET
def dashboard(request):
    try:
        months = int(request.GET.get("months", 6))
    except ValueError:
        months = 6
    if months not in PERIODS:
        months = 6
    data = build(months)
    if request.GET.get("format") == "pdf":
        return to_pdf(request.user, data)
    return JsonResponse(data)
