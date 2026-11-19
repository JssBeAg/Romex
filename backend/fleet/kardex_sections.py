"""
The kardex of a unit, one section per subject (read only, managers only).

Each section is a list of its own, with the behaviour of every other list (see common/listing.py):
search (q), date range (date_from/date_to), its own filters, order, pagination and PDF.

    GET /api/kardex/<id>/mantenimientos/   ?tipo=preventivo|correctivo &terminada=si|no
    GET /api/kardex/<id>/fallas/           ?estatus=<status id>
    GET /api/kardex/<id>/checklists/       ?resultado=ok|fallas
    GET /api/kardex/<id>/refacciones/
    GET /api/kardex/<id>/operadores/       ?rol=operador|mecanico   (operators and mechanics)
    GET /api/kardex/<id>/cambios/          ?usuario=<user id>       (changes to the unit's data)
    GET /api/kardex/<id>/linea-de-tiempo/  ?tipo=<event type>      (everything, by date)

Every row carries its data in separate fields (no text put together for display). Nothing is
stored: it is all read from the tables that exist and, for the changes, from the audit trail.
"""

from dataclasses import dataclass
from typing import Callable

from django.db.models import Count, Max, Prefetch, Q, Sum
from django.http import JsonResponse, QueryDict
from django.utils import timezone
from django.views.decorators.http import require_GET

from accounts.permissions import manager_required
from audit.models import AuditLog
from audit.visibility import visible_to_manager
from common.listing import (
    date_range,
    dates_line,
    filter_lines,
    list_response,
    order_by,
    order_rows,
    parse_date,
    rows_response,
)

from .assignments import operator_label
from .folios import folio_code
from .maintenances_api import CORRECTIVE, PREVENTIVE
from .models import (
    Checklist,
    FaultReport,
    FaultReportStatus,
    Maintenance,
    MaintenanceSparePart,
    ReportMechanic,
    Unit,
    UnitOperator,
)


def yes_no(value):
    return "Sí" if value else "No"


def show_value(value):
    """A value of the audit trail as a person reads it."""
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return yes_no(value)
    return str(value)


def search_text(request):
    return request.GET.get("q", "").strip()


def contains(text, *values):
    """Whether the search text is in any of the values (case does not matter)."""
    text = text.lower()
    return any(text in str(value or "").lower() for value in values)


# -- maintenances ------------------------------------------------------------------------------
def maintenances_queryset(unit, request):
    queryset = (
        Maintenance.objects.filter(unit=unit)
        .select_related(
            "service_type", "registered_by", "plan", "diagnosis__diagnosed_by", "diagnosis__fault_report__reported_by"
        )
        .prefetch_related(
            "operators",
            Prefetch("part_usages", queryset=MaintenanceSparePart.objects.select_related("spare_part")),
        )
    )
    queryset = date_range(queryset, request)
    kind = request.GET.get("tipo", "")
    if kind == "preventivo":
        queryset = queryset.filter(service_type__name=PREVENTIVE)
    elif kind == "correctivo":
        queryset = queryset.filter(service_type__name=CORRECTIVE)
    finished = request.GET.get("terminada", "")
    if finished in ("si", "no"):
        # Only a corrective maintenance finishes a repair
        queryset = queryset.filter(service_type__name=CORRECTIVE, repair_completed=finished == "si")
    text = search_text(request)
    if text:
        queryset = queryset.filter(
            Q(observations__icontains=text)
            | Q(diagnosis__detailed_cause__icontains=text)
            | Q(diagnosis__fault_report__description__icontains=text)
            | Q(part_usages__spare_part__name__icontains=text)
            | Q(operators__first_name__icontains=text)
            | Q(operators__paternal_surname__icontains=text)
            | Q(operators__enrollment_id__icontains=text)
        ).distinct()
    return queryset


def serialize_maintenance(m):
    diagnosis = m.diagnosis
    report = diagnosis.fault_report if diagnosis else None
    corrective = m.service_type.name == CORRECTIVE
    return {
        "id": m.pk,
        "folio": folio_code(m.registered_by, m.folio),
        "date": m.date.isoformat(),
        "service_type": m.service_type.name,
        "plan": m.plan.name if m.plan_id else None,
        "mileage": m.service_mileage,
        "cost": str(m.total_cost),
        "people": [operator_label(o) for o in m.operators.all()],
        "parts": [
            {"label": str(u.spare_part), "quantity": u.quantity}
            for u in sorted(m.part_usages.all(), key=lambda u: str(u.spare_part))
        ],
        # Only a corrective maintenance says whether the repair was finished
        "repair_completed": m.repair_completed if corrective else None,
        "report": {"id": report.pk, "label": f"Reporte {folio_code(report.reported_by, report.folio)}"} if report else None,
        "diagnosis": {"id": diagnosis.pk, "label": f"Diagnóstico {folio_code(diagnosis.diagnosed_by, diagnosis.folio)}"}
        if diagnosis
        else None,
        "failure": report.description if report else None,
        "cause": diagnosis.detailed_cause if diagnosis else None,
        "observations": m.observations,
    }


def maintenance_filters(request):
    return filter_lines(
        ("Búsqueda", search_text(request)),
        ("Tipo de servicio", {"preventivo": PREVENTIVE, "correctivo": CORRECTIVE}.get(request.GET.get("tipo", ""), "")),
        ("Reparación terminada", {"si": "Sí", "no": "No"}.get(request.GET.get("terminada", ""), "")),
        dates_line(request),
    )


def parts_text(row):
    return ", ".join(f"{p['label']} × {p['quantity']}" for p in row["parts"]) or "Sin refacciones"


MAINTENANCE_COLUMNS = [
    ("Fecha", 1.1, lambda r: r["date"]),
    ("Servicio", 1.1, lambda r: r["service_type"]),
    ("Km", 0.8, lambda r: r["mileage"]),
    ("Costo (MXN)", 1, lambda r: r["cost"]),
    ("Responsables", 2, lambda r: ", ".join(r["people"]) or "-"),
    ("Refacciones", 2.2, parts_text),
    ("Reparación terminada", 1.1, lambda r: "-" if r["repair_completed"] is None else yes_no(r["repair_completed"])),
    ("Reporte / diagnóstico", 1.6, lambda r: " / ".join(x["label"] for x in (r["report"], r["diagnosis"]) if x) or "-"),
    ("Causa", 2, lambda r: r["cause"] or "-"),
    ("Observaciones", 2.4, lambda r: r["observations"] or "-"),
]


# -- fault reports -----------------------------------------------------------------------------
def faults_queryset(unit, request):
    queryset = (
        FaultReport.objects.filter(unit=unit)
        .select_related("status", "reported_by", "diagnosis__severity", "diagnosis__diagnosed_by")
        .prefetch_related(
            Prefetch(
                "mechanic_assignments",
                queryset=ReportMechanic.objects.filter(end_date__isnull=True).select_related("mechanic"),
                to_attr="current_mechanics",
            )
        )
    )
    queryset = date_range(queryset, request)
    status = request.GET.get("estatus", "").strip()
    if status.isdigit():
        queryset = queryset.filter(status_id=int(status))
    text = search_text(request)
    if text:
        queryset = queryset.filter(
            Q(description__icontains=text)
            | Q(location__icontains=text)
            | Q(diagnosis__detailed_cause__icontains=text)
        )
    return queryset


def serialize_fault(r):
    diagnosis = getattr(r, "diagnosis", None)
    return {
        "id": r.pk,
        "folio": folio_code(r.reported_by, r.folio),
        "date": r.date.isoformat(),
        "reported_by": operator_label(r.reported_by),
        "location": r.location,
        "description": r.description,
        "status": r.status.name,
        "mechanics": [operator_label(a.mechanic) for a in r.current_mechanics],
        "diagnosis": (
            {
                "id": diagnosis.pk,
                "folio": folio_code(diagnosis.diagnosed_by, diagnosis.folio),
                "date": diagnosis.date.isoformat(),
                "cause": diagnosis.detailed_cause,
                "severity": diagnosis.severity.name,
                "requires_repair": diagnosis.requires_repair,
                "unit_operable": diagnosis.unit_operable,
            }
            if diagnosis
            else None
        ),
    }


def fault_filters(request):
    status = request.GET.get("estatus", "").strip()
    name = FaultReportStatus.objects.filter(pk=status).values_list("name", flat=True).first() if status.isdigit() else ""
    return filter_lines(("Búsqueda", search_text(request)), ("Estatus", name), dates_line(request))


def diagnosis_value(key, show=str):
    return lambda r: show(r["diagnosis"][key]) if r["diagnosis"] else "-"


FAULT_COLUMNS = [
    ("Fecha", 1.1, lambda r: r["date"]),
    ("Folio", 1, lambda r: r["folio"]),
    ("Ubicación", 1.6, lambda r: r["location"]),
    ("Descripción", 3, lambda r: r["description"]),
    ("Estatus", 1.3, lambda r: r["status"]),
    ("Causa (diagnóstico)", 2.6, diagnosis_value("cause")),
    ("Gravedad", 1, diagnosis_value("severity")),
    ("¿Puede operar?", 1, diagnosis_value("unit_operable", yes_no)),
]


# -- checklists --------------------------------------------------------------------------------
CHECK_ITEMS = [("lights_ok", "Luces"), ("fluids_ok", "Fluidos"), ("no_cracks", "Sin grietas")]
ALL_OK = Q(lights_ok=True, fluids_ok=True, no_cracks=True)


def checklists_queryset(unit, request):
    queryset = date_range(Checklist.objects.filter(unit=unit).select_related("completed_by"), request)
    result = request.GET.get("resultado", "")
    if result == "ok":
        queryset = queryset.filter(ALL_OK)
    elif result == "fallas":
        queryset = queryset.exclude(ALL_OK)
    text = search_text(request)
    if text:
        queryset = queryset.filter(
            Q(trip_description__icontains=text)
            | Q(completed_by__first_name__icontains=text)
            | Q(completed_by__paternal_surname__icontains=text)
            | Q(completed_by__enrollment_id__icontains=text)
        )
    return queryset


def serialize_checklist(c):
    failed = [label for name, label in CHECK_ITEMS if not getattr(c, name)]
    return {
        "id": c.pk,
        "folio": folio_code(c.completed_by, c.folio),
        "date": c.date.isoformat(),
        "operator": operator_label(c.completed_by),
        "mileage": c.recorded_mileage,
        "tire_pressure": str(c.tire_pressure),
        "tire_tread_depth": str(c.tire_tread_depth),
        "ok": not failed,
        "failed_items": failed,  # what did not pass ([] = all good)
        "trip_description": c.trip_description,
    }


def checklist_result(row):
    return "Todo bien" if row["ok"] else "Con fallas: " + ", ".join(row["failed_items"])


CHECKLIST_COLUMNS = [
    ("Fecha", 1, lambda r: r["date"]),
    ("Folio", 1, lambda r: r["folio"]),
    ("Operador", 2, lambda r: r["operator"]),
    ("Km", 0.8, lambda r: r["mileage"]),
    ("Resultado", 2, checklist_result),
    ("Viaje", 3, lambda r: r["trip_description"]),
]


def checklist_filters(request):
    return filter_lines(
        ("Búsqueda", search_text(request)),
        ("Resultado", {"ok": "Todo bien", "fallas": "Con fallas"}.get(request.GET.get("resultado", ""), "")),
        dates_line(request),
    )


# -- parts changed (added up) ------------------------------------------------------------------
def parts_rows(unit, request):
    usages = date_range(MaintenanceSparePart.objects.filter(maintenance__unit=unit), request, "maintenance__date")
    text = search_text(request)
    if text:
        usages = usages.filter(spare_part__name__icontains=text)
    rows = (
        usages.values("spare_part_id", "spare_part__name")
        .annotate(pieces=Sum("quantity"), times=Count("maintenance", distinct=True), last=Max("maintenance__date"))
        .order_by("-last", "spare_part__name")
    )
    return [
        {"id": r["spare_part_id"], "label": r["spare_part__name"], "pieces": r["pieces"], "times": r["times"], "last_date": r["last"].isoformat()}
        for r in rows
    ]


PART_COLUMNS = [
    ("Refacción", 4, lambda r: r["label"]),
    ("Piezas", 1, lambda r: r["pieces"]),
    ("Veces", 1, lambda r: r["times"]),
    ("Último cambio", 1.6, lambda r: r["last_date"]),
]


# -- operators and mechanics -------------------------------------------------------------------
def people_rows(unit, request):
    role = request.GET.get("rol", "")
    rows = []
    if role in ("", "operador"):
        for a in UnitOperator.objects.filter(unit=unit).select_related("operator"):
            rows.append(
                {
                    "id": f"operador-{a.pk}",
                    "role": "Operador",
                    "person": operator_label(a.operator),
                    "start_date": a.start_date.isoformat(),
                    "end_date": a.end_date.isoformat() if a.end_date else None,
                    "report": None,
                }
            )
    if role in ("", "mecanico"):
        for a in ReportMechanic.objects.filter(fault_report__unit=unit).select_related("mechanic", "fault_report__reported_by"):
            report = a.fault_report
            rows.append(
                {
                    "id": f"mecanico-{a.pk}",
                    "role": "Mecánico",
                    "person": operator_label(a.mechanic),
                    "start_date": a.start_date.isoformat(),
                    "end_date": a.end_date.isoformat() if a.end_date else None,
                    "report": {"id": report.pk, "label": f"Reporte {folio_code(report.reported_by, report.folio)}"},
                }
            )
    # The period overlaps the range asked for
    start, end = parse_date(request.GET.get("date_from", "")), parse_date(request.GET.get("date_to", ""))
    if start:
        rows = [r for r in rows if r["end_date"] is None or r["end_date"] >= start.isoformat()]
    if end:
        rows = [r for r in rows if r["start_date"] <= end.isoformat()]
    text = search_text(request)
    if text:
        rows = [r for r in rows if contains(text, r["person"])]
    return rows


PEOPLE_COLUMNS = [
    ("Rol", 1, lambda r: r["role"]),
    ("Persona", 3, lambda r: r["person"]),
    ("Desde", 1.2, lambda r: r["start_date"]),
    ("Hasta", 1.2, lambda r: r["end_date"] or "Actual"),
    ("Reporte", 1.6, lambda r: r["report"]["label"] if r["report"] else "-"),
]


def people_filters(request):
    return filter_lines(
        ("Búsqueda", search_text(request)),
        ("Rol", {"operador": "Operadores", "mecanico": "Mecánicos"}.get(request.GET.get("rol", ""), "")),
        dates_line(request),
    )


# -- changes to the data of the unit -----------------------------------------------------------
def change_lines(unit):
    """The audit lines that changed the unit itself, as the manager may see them."""
    return visible_to_manager(
        AuditLog.objects.filter(table_name=Unit._meta.db_table, record_id=unit.pk, action=AuditLog.UPDATE)
    ).order_by("-timestamp", "-id")


def who_did(line):
    name = line.user_name or "Sistema"
    return f"{name} ({line.user_enrollment_id})" if line.user_enrollment_id else name


def change_rows(unit, request):
    """One row per field changed: plates and operators have their own sections, not repeated here."""
    lines = change_lines(unit)
    user = request.GET.get("usuario", "").strip()
    if user.isdigit():
        lines = lines.filter(user_id=int(user))
    start, end = parse_date(request.GET.get("date_from", "")), parse_date(request.GET.get("date_to", ""))
    text = search_text(request)
    rows = []
    for line in lines:
        moment = timezone.localtime(line.timestamp)
        if (start and moment.date() < start) or (end and moment.date() > end):
            continue
        for index, (name, values) in enumerate((line.changes or {}).items()):
            if not (isinstance(values, list) and len(values) == 2):
                continue
            row = {
                "id": f"{line.pk}-{index}",
                "moment": moment.strftime("%Y-%m-%d %H:%M"),
                "date": moment.date().isoformat(),
                "field": name,
                "old": show_value(values[0]),
                "new": show_value(values[1]),
                "user": who_did(line),
            }
            if text and not contains(text, row["field"], row["old"], row["new"], row["user"]):
                continue
            rows.append(row)
    return rows


def change_users(unit):
    """Who changed the unit's data: the options of the user filter."""
    seen = {}
    for line in change_lines(unit).exclude(user_id=None):
        seen.setdefault(line.user_id, who_did(line))
    return [{"id": pk, "label": label} for pk, label in sorted(seen.items(), key=lambda item: item[1])]


CHANGE_COLUMNS = [
    ("Fecha y hora", 1.4, lambda r: r["moment"]),
    ("Campo", 1.6, lambda r: r["field"]),
    ("Antes", 2, lambda r: r["old"]),
    ("Después", 2, lambda r: r["new"]),
    ("Quién", 2.4, lambda r: r["user"]),
]


def change_filters(request, unit):
    user = request.GET.get("usuario", "").strip()
    label = next((u["label"] for u in change_users(unit) if str(u["id"]) == user), "")
    return filter_lines(("Búsqueda", search_text(request)), ("Usuario", label), dates_line(request))


# -- sections ----------------------------------------------------------------------------------
@dataclass
class Section:
    title: str
    key: str  # where the rows are in the JSON answer
    columns: list
    filters: Callable  # (request, unit) -> lines that describe the filters in the PDF
    default: str  # default order
    sorts: dict  # column -> ORM fields (queryset sections) or row -> key (row sections)
    queryset: Callable | None = None  # (unit, request) -> filtered queryset, paged by the database
    serialize: Callable | None = None
    rows: Callable | None = None  # (unit, request) -> serialized rows, for lists put together in memory
    extra: Callable | None = None  # (unit) -> options of the filters
    landscape: bool = True
    empty: str = "Sin registros."


SECTIONS = {
    "mantenimientos": Section(
        title="Mantenimientos",
        key="maintenances",
        columns=MAINTENANCE_COLUMNS,
        filters=lambda request, unit: maintenance_filters(request),
        default="-date",
        sorts={"date": ("date",), "mileage": ("service_mileage",), "cost": ("total_cost",)},
        queryset=maintenances_queryset,
        serialize=serialize_maintenance,
        empty="Sin mantenimientos.",
    ),
    "fallas": Section(
        title="Fallas",
        key="faults",
        columns=FAULT_COLUMNS,
        filters=lambda request, unit: fault_filters(request),
        default="-date",
        sorts={"date": ("date",), "status": ("status__order",)},
        queryset=faults_queryset,
        serialize=serialize_fault,
        extra=lambda unit: {
            "statuses": [{"id": s.pk, "label": s.name} for s in FaultReportStatus.objects.order_by("order", "pk")]
        },
        empty="Sin reportes de falla.",
    ),
    "checklists": Section(
        title="Checklists",
        key="checklists",
        columns=CHECKLIST_COLUMNS,
        filters=lambda request, unit: checklist_filters(request),
        default="-date",
        sorts={"date": ("date",), "mileage": ("recorded_mileage",)},
        queryset=checklists_queryset,
        serialize=serialize_checklist,
        empty="Sin checklists.",
    ),
    "refacciones": Section(
        title="Refacciones cambiadas",
        key="parts",
        columns=PART_COLUMNS,
        filters=lambda request, unit: filter_lines(("Búsqueda", search_text(request)), dates_line(request)),
        default="-last_date",
        sorts={
            "last_date": lambda r: r["last_date"],
            "part": lambda r: r["label"].lower(),
            "pieces": lambda r: r["pieces"],
            "times": lambda r: r["times"],
        },
        rows=parts_rows,
        landscape=False,
        empty="A esta unidad todavía no se le ha cambiado ninguna refacción.",
    ),
    "operadores": Section(
        title="Operadores y mecánicos",
        key="people",
        columns=PEOPLE_COLUMNS,
        filters=lambda request, unit: people_filters(request),
        default="-start_date",
        sorts={
            "start_date": lambda r: r["start_date"],
            "end_date": lambda r: r["end_date"] or "9999-12-31",  # the current ones are the latest
            "person": lambda r: r["person"].lower(),
        },
        rows=people_rows,
        landscape=False,
        empty="Nadie ha tenido ni atendido esta unidad.",
    ),
    "cambios": Section(
        title="Cambios de datos",
        key="changes",
        columns=CHANGE_COLUMNS,
        filters=lambda request, unit: change_filters(request, unit),
        default="-moment",
        sorts={"moment": lambda r: r["moment"], "field": lambda r: r["field"].lower()},
        rows=change_rows,
        extra=lambda unit: {"users": change_users(unit)},
        empty="Los datos de la unidad no se han modificado.",
    ),
}


def section_rows(section, unit, request):
    """All the rows of a section, ordered (for the PDFs)."""
    if section.queryset is not None:
        queryset = order_by(section.queryset(unit, request), request, section.sorts, section.default)
        return [section.serialize(obj) for obj in queryset]
    return order_rows(section.rows(unit, request), request, section.sorts, section.default)


class NoFilters:
    """A stand-in request with no parameters: the whole section, in its default order."""

    GET = QueryDict("")


def full_section_tables(unit):
    """Every section, unfiltered, as tables of the complete PDF of the kardex."""
    tables = []
    for section in SECTIONS.values():
        rows = section_rows(section, unit, NoFilters())
        tables.append(
            {
                "heading": section.title,
                "columns": [(header, weight) for header, weight, _ in section.columns],
                "rows": [[getter(row) for _, _, getter in section.columns] for row in rows],
                "empty": section.empty,
            }
        )
    return tables


def section_view(name):
    section = SECTIONS[name]

    @manager_required
    @require_GET
    def view(request, pk):
        unit = Unit.objects.filter(pk=pk).first()
        if unit is None:
            return JsonResponse({"error": "La unidad no existe"}, status=404)
        export = {
            "title": f"Kardex de la unidad {unit.economic_number}: {section.title.lower()}",
            "filters": section.filters(request, unit),
            "columns": section.columns,
            "landscape": section.landscape,
        }
        extra = section.extra(unit) if section.extra else None
        if section.queryset is not None:
            return list_response(
                request,
                section.queryset(unit, request),
                key=section.key,
                serialize=section.serialize,
                sorts=section.sorts,
                default=section.default,
                export=export,
                extra=extra,
            )
        return rows_response(
            request,
            section.rows(unit, request),
            key=section.key,
            sorts=section.sorts,
            default=section.default,
            export=export,
            extra=extra,
        )

    view.__doc__ = f"The kardex section «{section.title}» of one unit: filters, order, pages and PDF."
    view.__name__ = f"kardex_{name.replace('-', '_')}"
    return view


maintenances = section_view("mantenimientos")
faults = section_view("fallas")
checklists = section_view("checklists")
parts = section_view("refacciones")
people = section_view("operadores")
changes = section_view("cambios")
