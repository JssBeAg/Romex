"""
Kardex of a unit: its history in one place (read only, managers only).

It is not stored anywhere: every time it is asked for, it is computed from the tables that
already exist (plates, operators, fault reports, their mechanics, diagnoses, maintenances and checklists)
and from the audit trail, for the corrections made to the data of the unit itself.
"""
from decimal import Decimal

from django.db.models import Count, Max, Prefetch, Q, Sum
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from accounts.permissions import manager_required
from audit.models import AuditLog
from common.listing import wants_pdf

from .checklists_api import checklist_title
from .diagnoses_api import diagnosis_title
from .maintenances_api import CORRECTIVE, PREVENTIVE, maintenance_title
from . import sheets
from .models import (
    Checklist,
    FaultDiagnosis,
    FaultReport,
    Maintenance,
    MaintenanceSparePart,
    Unit,
    ReportMechanic,
    UnitLicensePlate,
    UnitOperator,
)
from .preventive import due_rows
from .report_status import CLOSED_STATUSES
from .reports_api import report_title
from .units_api import operator_label, serialize_unit, units_queryset


def yes_no(value):
    return "sí" if value else "no"


def show_value(value):
    """A value of the audit trail as a person reads it."""
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return yes_no(value)
    return str(value)


def maintenance_detail(m):
    """What was done to the unit in a maintenance: type, km, cost, the fault, who, which parts."""
    lines = [f"{m.service_type.name}. {m.service_mileage} km. Costo: ${m.total_cost}."]
    if m.diagnosis_id:
        lines.append(f"Falla: {m.diagnosis.fault_report.description}")
        lines.append(f"Causa: {m.diagnosis.detailed_cause}")
        lines.append(f"Reparación terminada: {yes_no(m.repair_completed)}.")
    people = ", ".join(operator_label(o) for o in m.operators.all())
    if people:
        lines.append(f"Realizado por: {people}.")
    parts = ", ".join(
        f"{u.spare_part} × {u.quantity}" for u in sorted(m.part_usages.all(), key=lambda u: str(u.spare_part))
    )
    lines.append(f"Refacciones cambiadas: {parts}." if parts else "Sin refacciones.")
    if m.observations:
        lines.append(f"Observaciones: {m.observations}")
    return "\n".join(lines)


def parts_used(unit):
    """The parts changed on the unit, added up: pieces, times and the last date, newest first."""
    rows = (
        MaintenanceSparePart.objects.filter(maintenance__unit=unit)
        .values("spare_part_id", "spare_part__name")
        .annotate(pieces=Sum("quantity"), times=Count("maintenance", distinct=True), last=Max("maintenance__date"))
        .order_by("-last", "spare_part__name")
    )
    return [
        {
            "id": r["spare_part_id"],
            "label": r["spare_part__name"],
            "pieces": r["pieces"],
            "times": r["times"],
            "last_date": r["last"].isoformat(),
        }
        for r in rows
    ]


def unit_change_events(unit):
    """
    The times the data of the unit itself was corrected or changed (economic number, model,
    mileage, active or not...), from the audit trail: what it said before, what it says now,
    who did it and when. Plates and operators are not repeated here: they have their own events.
    """
    lines = AuditLog.objects.filter(
        table_name=Unit._meta.db_table, record_id=unit.pk, action=AuditLog.UPDATE
    ).order_by("-timestamp", "-id")  # newest first: on the same day the later change comes first
    events = []
    for line in lines:
        pairs = [
            (field, values)
            for field, values in (line.changes or {}).items()
            if isinstance(values, list) and len(values) == 2
        ]
        if not pairs:
            continue
        moment = timezone.localtime(line.timestamp)
        who = line.user_name or "Sistema"
        if line.user_enrollment_id:
            who = f"{who} ({line.user_enrollment_id})"
        events.append(
            {
                "type": "change",
                "date": moment.date(),
                "title": f"Datos de la unidad modificados por {who}",
                "detail": f"{moment:%H:%M}. "
                + "; ".join(f"{field}: {show_value(old)} → {show_value(new)}" for field, (old, new) in pairs)
                + ".",
                "link": None,
            }
        )
    return events


def build_events(unit):
    """Everything important that happened to the unit, as plain dicts (unsorted)."""
    events = unit_change_events(unit)

    for a in UnitLicensePlate.objects.select_related("license_plate").filter(unit=unit):
        label = f"{a.license_plate.identifier} ({a.license_plate.state})"
        events.append(
            {"type": "plate", "date": a.start_date, "title": f"Placa asignada: {label}", "detail": "", "link": None}
        )
        if a.end_date:
            events.append(
                {"type": "plate", "date": a.end_date, "title": f"Placa retirada: {label}", "detail": "", "link": None}
            )

    for a in UnitOperator.objects.select_related("operator").filter(unit=unit):
        label = operator_label(a.operator)
        events.append(
            {"type": "operator", "date": a.start_date, "title": f"Operador asignado: {label}", "detail": "", "link": None}
        )
        if a.end_date:
            events.append(
                {"type": "operator", "date": a.end_date, "title": f"Operador retirado: {label}", "detail": "", "link": None}
            )

    assignments = ReportMechanic.objects.select_related(
        "mechanic", "fault_report__unit", "fault_report__reported_by"
    ).filter(fault_report__unit=unit)
    for a in assignments:
        label = operator_label(a.mechanic)
        detail = report_title(a.fault_report)
        link = f"/reportes/{a.fault_report_id}"
        events.append(
            {"type": "mechanic", "date": a.start_date, "title": f"Mecánico asignado: {label}", "detail": detail, "link": link}
        )
        if a.end_date:
            events.append(
                {"type": "mechanic", "date": a.end_date, "title": f"Mecánico retirado: {label}", "detail": detail, "link": link}
            )

    reports = FaultReport.objects.select_related("unit", "reported_by", "status").filter(unit=unit)
    for r in reports:
        events.append(
            {
                "type": "report",
                "date": r.date,
                "title": report_title(r),
                "detail": f"{r.location}. Estatus: {r.status.name}.\nDescripción: {r.description}",
                "link": f"/reportes/{r.pk}",
            }
        )

    diagnoses = FaultDiagnosis.objects.select_related(
        "fault_report__unit", "diagnosed_by", "severity"
    ).filter(fault_report__unit=unit)
    for d in diagnoses:
        events.append(
            {
                "type": "diagnosis",
                "date": d.date,
                "title": diagnosis_title(d),
                "detail": (
                    f"Severidad: {d.severity.name}. Requiere reparación: {yes_no(d.requires_repair)}. "
                    f"Unidad operable: {yes_no(d.unit_operable)}.\nCausa: {d.detailed_cause}"
                ),
                "link": f"/diagnosticos/{d.pk}",
            }
        )

    maintenances = (
        Maintenance.objects.select_related(
            "unit", "registered_by", "service_type", "diagnosis__fault_report"
        )
        .prefetch_related(
            "operators",
            Prefetch("part_usages", queryset=MaintenanceSparePart.objects.select_related("spare_part")),
        )
        .filter(unit=unit)
    )
    for m in maintenances:
        events.append(
            {
                "type": "maintenance",
                "date": m.date,
                "title": maintenance_title(m),
                "detail": maintenance_detail(m),
                "link": f"/mantenimientos/{m.pk}",
            }
        )

    for c in Checklist.objects.select_related("unit", "completed_by").filter(unit=unit):
        events.append(
            {
                "type": "checklist",
                "date": c.date,
                "title": checklist_title(c),
                "detail": (
                    f"{c.recorded_mileage} km. Luces: {yes_no(c.lights_ok)}. "
                    f"Fluidos: {yes_no(c.fluids_ok)}. Sin grietas: {yes_no(c.no_cracks)}."
                ),
                "link": f"/checklists/{c.pk}",
            }
        )
    return events


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
    unit = units_queryset().filter(pk=pk).first()
    if unit is None:
        return JsonResponse({"error": "La unidad no existe"}, status=404)
    # Newest first; on the same day the later step of the process comes first
    # (maintenance, diagnosis, mechanic assigned, report), then checklists, plates and operators
    rank = {
        "plate": 0,
        "operator": 0,
        "change": 0,
        "checklist": 1,
        "report": 2,
        "mechanic": 3,
        "diagnosis": 4,
        "maintenance": 5,
    }
    events = sorted(build_events(unit), key=lambda e: (e["date"], rank[e["type"]]), reverse=True)
    for event in events:
        event["date"] = event["date"].isoformat()
    data = {
        "unit": serialize_unit(unit),
        "summary": build_summary(unit),
        # Where the unit stands for each preventive plan, most urgent first
        "preventive": due_rows(unit_ids=[unit.pk]),
        # The physical side: the parts changed on the unit, added up
        "parts_used": parts_used(unit),
        "events": events,
    }
    if wants_pdf(request):
        return sheets.kardex_sheet(request.user, data)
    return JsonResponse(data)
