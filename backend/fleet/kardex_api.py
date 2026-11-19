"""
Kardex of a unit (read only, managers only): the header and the general timeline. Each subject
(maintenances, faults, checklists, parts, people, changes) is a list of its own: see
fleet/kardex_sections.py.

Nothing is stored: every time it is asked for, it is computed from the tables that already exist
(plates, operators, fault reports, their mechanics, diagnoses, maintenances and checklists) and
from the audit trail, for the corrections made to the data of the unit itself.

    GET /api/kardex/<id>/                  header: unit, summary, preventive plans
    GET /api/kardex/<id>/?format=pdf       the complete kardex, one table per section
    GET /api/kardex/<id>/linea-de-tiempo/  everything by date ?tipo=<event type>
"""
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from accounts.permissions import manager_required
from common.listing import dates_line, filter_lines, parse_date, rows_response, wants_pdf

from . import sheets
from .checklists_api import checklist_title
from .diagnoses_api import diagnosis_title
from .kardex_sections import NoFilters, change_rows, contains, full_section_tables, search_text, yes_no
from .maintenances_api import CORRECTIVE, PREVENTIVE, maintenance_title
from .models import (
    Checklist,
    FaultDiagnosis,
    FaultReport,
    Maintenance,
    ReportMechanic,
    UnitLicensePlate,
    UnitOperator,
)
from .preventive import due_rows
from .report_status import CLOSED_STATUSES
from .reports_api import report_title
from .units_api import operator_label, serialize_unit, units_queryset

EVENT_TYPES = {
    "plate": "Placa",
    "operator": "Operador",
    "mechanic": "Mecánico",
    "report": "Reporte",
    "diagnosis": "Diagnóstico",
    "maintenance": "Mantenimiento",
    "checklist": "Checklist",
    "change": "Cambio de datos",
}

# Newest first; on the same day the later step of the process comes first
# (maintenance, diagnosis, mechanic assigned, report), then checklists, plates and operators
RANK = {"plate": 0, "operator": 0, "change": 0, "checklist": 1, "report": 2, "mechanic": 3, "diagnosis": 4, "maintenance": 5}


def event(kind, date, title, detail="", link=None, seq=0):
    return {"type": kind, "date": date.isoformat(), "title": title, "detail": detail, "link": link, "seq": seq}


def build_events(unit):
    """Everything important that happened to the unit, one line each (unsorted)."""
    events = []
    # Changes to the unit's data: one event per save, the fields changed on one line
    by_save = {}
    for row in change_rows(unit, NoFilters()):
        by_save.setdefault(row["id"].split("-")[0], []).append(row)
    for rows in by_save.values():
        first = rows[0]
        events.append(
            event(
                "change",
                parse_date(first["date"]),
                f"Datos de la unidad modificados por {first['user']}",
                f"{first['moment'][11:]}. " + "; ".join(f"{r['field']}: {r['old']} → {r['new']}" for r in rows) + ".",
            )
        )

    for a in UnitLicensePlate.objects.select_related("license_plate").filter(unit=unit):
        label = f"{a.license_plate.identifier} ({a.license_plate.state})"
        events.append(event("plate", a.start_date, f"Placa asignada: {label}"))
        if a.end_date:
            events.append(event("plate", a.end_date, f"Placa retirada: {label}"))

    # Oldest first, so that within a day the one who leaves sorts below the one who arrives
    assignments = UnitOperator.objects.select_related("operator").filter(unit=unit).order_by("start_date", "id")
    for index, a in enumerate(assignments):
        label = operator_label(a.operator)
        period = f"Desde {a.start_date.isoformat()}" + (f" hasta {a.end_date.isoformat()}." if a.end_date else " (actual).")
        events.append(event("operator", a.start_date, f"Asignada a {label}", period, seq=2 * index))
        if a.end_date:
            events.append(event("operator", a.end_date, f"Operador {label} dejó la unidad", period, seq=2 * index + 1))

    mechanics = ReportMechanic.objects.select_related("mechanic", "fault_report__unit", "fault_report__reported_by")
    for a in mechanics.filter(fault_report__unit=unit):
        label = operator_label(a.mechanic)
        detail, link = report_title(a.fault_report), f"/reportes/{a.fault_report_id}"
        events.append(event("mechanic", a.start_date, f"Mecánico asignado: {label}", detail, link))
        if a.end_date:
            events.append(event("mechanic", a.end_date, f"Mecánico retirado: {label}", detail, link))

    for r in FaultReport.objects.select_related("unit", "reported_by", "status").filter(unit=unit):
        events.append(event("report", r.date, report_title(r), f"{r.location}. Estatus: {r.status.name}.", f"/reportes/{r.pk}"))

    diagnoses = FaultDiagnosis.objects.select_related("fault_report__unit", "diagnosed_by", "severity")
    for d in diagnoses.filter(fault_report__unit=unit):
        events.append(
            event(
                "diagnosis",
                d.date,
                diagnosis_title(d),
                f"Gravedad: {d.severity.name}. Requiere reparación: {yes_no(d.requires_repair)}. "
                f"Puede operar: {yes_no(d.unit_operable)}.",
                f"/diagnosticos/{d.pk}",
            )
        )

    for m in Maintenance.objects.select_related("unit", "registered_by", "service_type").filter(unit=unit):
        events.append(
            event(
                "maintenance",
                m.date,
                maintenance_title(m),
                f"{m.service_type.name}. {m.service_mileage} km. Costo: ${m.total_cost}.",
                f"/mantenimientos/{m.pk}",
            )
        )

    for c in Checklist.objects.select_related("unit", "completed_by").filter(unit=unit):
        events.append(
            event(
                "checklist",
                c.date,
                checklist_title(c),
                f"{c.recorded_mileage} km. Luces: {yes_no(c.lights_ok)}. Fluidos: {yes_no(c.fluids_ok)}. "
                f"Sin grietas: {yes_no(c.no_cracks)}.",
                f"/checklists/{c.pk}",
            )
        )
    return events


def timeline_rows(unit, request):
    """The events of the unit with the filters of the request: type, dates, search."""
    rows = build_events(unit)
    kind = request.GET.get("tipo", "")
    if kind in EVENT_TYPES:
        rows = [r for r in rows if r["type"] == kind]
    start, end = parse_date(request.GET.get("date_from", "")), parse_date(request.GET.get("date_to", ""))
    if start:
        rows = [r for r in rows if r["date"] >= start.isoformat()]
    if end:
        rows = [r for r in rows if r["date"] <= end.isoformat()]
    text = search_text(request)
    if text:
        rows = [r for r in rows if contains(text, r["title"], r["detail"])]
    for r in rows:
        r["type_label"] = EVENT_TYPES[r["type"]]
    return rows


def timeline_key(row):
    # "seq" breaks ties inside a day (an operator who leaves and the next one who arrives)
    return (row["date"], RANK[row["type"]], row["seq"])


def build_summary(unit):
    maintenances = Maintenance.objects.filter(unit=unit)
    totals = maintenances.aggregate(
        count=Count("id"),
        preventive=Count("id", filter=Q(service_type__name=PREVENTIVE)),
        corrective=Count("id", filter=Q(service_type__name=CORRECTIVE)),
        cost=Sum("total_cost"),
    )
    last_maintenance = maintenances.order_by("-date", "-id").first()
    last_checklist = Checklist.objects.filter(unit=unit).order_by("-date", "-id").first()
    reports = FaultReport.objects.filter(unit=unit)
    return {
        "reports": reports.count(),
        "pending_reports": reports.exclude(status__name__in=CLOSED_STATUSES).count(),
        "diagnoses": FaultDiagnosis.objects.filter(fault_report__unit=unit).count(),
        "maintenances": totals["count"],
        "preventive_maintenances": totals["preventive"],
        "corrective_maintenances": totals["corrective"],
        "total_maintenance_cost": str(totals["cost"] or Decimal("0")),
        "last_maintenance": (
            {"date": last_maintenance.date.isoformat(), "mileage": last_maintenance.service_mileage}
            if last_maintenance
            else None
        ),
        "checklists": Checklist.objects.filter(unit=unit).count(),
        "last_checklist": (
            {"date": last_checklist.date.isoformat(), "mileage": last_checklist.recorded_mileage}
            if last_checklist
            else None
        ),
    }


@manager_required
@require_GET
def kardex(request, pk):
    """Header of the kardex of a unit (data, summary, preventive plans); with format=pdf, the whole kardex."""
    unit = units_queryset().filter(pk=pk).first()
    if unit is None:
        return JsonResponse({"error": "La unidad no existe"}, status=404)
    data = {
        "unit": serialize_unit(unit),
        "summary": build_summary(unit),
        # Where the unit stands for each preventive plan, most urgent first
        "preventive": due_rows(unit_ids=[unit.pk]),
    }
    if wants_pdf(request):
        return sheets.kardex_sheet(request.user, data, full_section_tables(unit))
    return JsonResponse(data)


@manager_required
@require_GET
def timeline(request, pk):
    """General timeline of the kardex of a unit: every event by date, filtered by type."""
    unit = units_queryset().filter(pk=pk).first()
    if unit is None:
        return JsonResponse({"error": "La unidad no existe"}, status=404)
    return rows_response(
        request,
        timeline_rows(unit, request),
        key="events",
        sorts={"date": timeline_key},
        default="-date",
        export={
            "title": f"Kardex de la unidad {unit.economic_number}: línea de tiempo",
            "filters": filter_lines(
                ("Búsqueda", search_text(request)),
                ("Tipo", EVENT_TYPES.get(request.GET.get("tipo", ""), "")),
                dates_line(request),
            ),
            "columns": [
                ("Fecha", 1.1, lambda r: r["date"]),
                ("Tipo", 1.3, lambda r: r["type_label"]),
                ("Evento", 4, lambda r: r["title"]),
                ("Detalle", 4, lambda r: r["detail"] or "-"),
            ],
        },
        extra={"types": [{"id": key, "label": label} for key, label in EVENT_TYPES.items()]},
    )
