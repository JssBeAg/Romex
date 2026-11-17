"""
JSON API for fault diagnoses.

  - Managers can see every diagnosis (read only).
  - Mechanics can see, create, edit and delete the diagnoses of the fault reports assigned to
    them (the manager assigns them), and diagnose only those reports.
  - Everybody else has no access.
The author of a diagnosis is always the logged-in mechanic; it is never taken from the request.
"""
import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, ProtectedError, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from accounts.permissions import roles_required, validation_only
from common.listing import date_range, dates_line, filter_lines, list_response, wants_pdf
from accounts.roles import MANAGER_ROLE, MECHANIC_ROLE

from . import sheets
from .assignments import reports_of
from .folios import next_folio
from .models import FaultDiagnosis, FaultReport, Severity
from .report_status import refresh_report_status
from .reports_api import add_error, is_mechanic, parse_body, record_title, report_title, unit_label

view_roles = roles_required(MANAGER_ROLE, MECHANIC_ROLE)


DIAGNOSIS_SORTS = {
    "date": ("date",),
    "unit": ("fault_report__unit__economic_number",),
    "severity": ("severity_id",),
    "diagnosed_by": ("diagnosed_by__first_name", "diagnosed_by__paternal_surname"),
}


def diagnoses_queryset(user):
    """Diagnoses the user can see: all of them, or only those of their assigned reports for mechanics."""
    queryset = (
        FaultDiagnosis.objects.select_related(
            "fault_report__unit__unit_model__brand", "fault_report__status", "fault_report__reported_by", "diagnosed_by", "severity"
        )
        .annotate(maintenances_count=Count("maintenances"))
        .order_by("-date", "-id")
    )
    if is_mechanic(user):
        queryset = queryset.filter(fault_report__in=reports_of(user).values("pk"))
    return queryset


def report_label(report):
    return f"{report_title(report)} - {report.location}"


def diagnosis_title(diagnosis):
    return record_title(
        "Diagnóstico", diagnosis.diagnosed_by, diagnosis.folio, diagnosis.date, diagnosis.fault_report.unit
    )


def serialize_diagnosis(diagnosis, user):
    author = diagnosis.diagnosed_by
    report = diagnosis.fault_report
    return {
        "id": diagnosis.pk,
        "title": diagnosis_title(diagnosis),
        "date": diagnosis.date.isoformat(),
        "detailed_cause": diagnosis.detailed_cause,
        "requires_repair": diagnosis.requires_repair,
        "unit_operable": diagnosis.unit_operable,
        "severity": {"id": diagnosis.severity_id, "label": diagnosis.severity.name},
        "fault_report": {
            "id": report.pk,
            "title": report_title(report),
            "label": report_label(report),
            "description": report.description,
        },
        "unit": {"id": report.unit_id, "label": unit_label(report.unit)},
        "diagnosed_by": {"id": author.pk, "label": f"{author.get_full_name()} ({author.enrollment_id})"},
        "maintenances_count": diagnosis.maintenances_count,
        # A mechanic only sees the diagnoses of the reports assigned to them, so those can be changed
        "can_modify": is_mechanic(user),
    }


def validate_diagnosis(data, diagnosis):
    """Validate the data of a diagnosis. Returns (errors, diagnosis). Nothing is saved here."""
    errors = {}
    creating = diagnosis.pk is None

    if creating:
        report = None
        try:
            report = FaultReport.objects.filter(pk=int(data.get("fault_report_id"))).first()
        except (TypeError, ValueError):
            pass
        if report is None:
            add_error(errors, "fault_report_id", "Elige una opción válida.")
        elif not reports_of(diagnosis.diagnosed_by).filter(pk=report.pk).exists():
            add_error(errors, "fault_report_id", "Ese reporte no está asignado a ti.")
        elif FaultDiagnosis.objects.filter(fault_report=report).exists():
            add_error(errors, "fault_report_id", "Ese reporte ya tiene un diagnóstico.")
        else:
            diagnosis.fault_report = report

    severity = None
    try:
        severity = Severity.objects.filter(pk=int(data.get("severity_id"))).first()
    except (TypeError, ValueError):
        pass
    if severity is None:
        add_error(errors, "severity_id", "Elige una opción válida.")
    diagnosis.severity = severity

    try:
        date = datetime.date.fromisoformat(str(data.get("date", "")))
        if date > datetime.date.today():
            add_error(errors, "date", "La fecha no puede ser futura.")
    except ValueError:
        date = None
        add_error(errors, "date", "Ingresa una fecha válida.")
    diagnosis.date = date

    diagnosis.detailed_cause = str(data.get("detailed_cause", "")).strip()
    if not diagnosis.detailed_cause:
        add_error(errors, "detailed_cause", "Este campo es obligatorio.")

    # Both yes/no answers must be given explicitly
    for field in ("requires_repair", "unit_operable"):
        value = data.get(field)
        if not isinstance(value, bool):
            add_error(errors, field, "Elige una opción.")
        setattr(diagnosis, field, value if isinstance(value, bool) else None)

    if not errors:
        try:
            diagnosis.full_clean(exclude=["diagnosed_by", "folio"])
        except ValidationError as exc:
            errors.update({field: list(messages) for field, messages in exc.message_dict.items()})
    return errors, diagnosis


@view_roles
@require_http_methods(["GET", "POST"])
def diagnoses(request):
    if request.method == "GET":
        queryset = diagnoses_queryset(request.user)
        search = request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(fault_report__unit__economic_number__icontains=search)
                | Q(fault_report__unit__plate_assignments__license_plate__identifier__icontains=search)
                | Q(detailed_cause__icontains=search)
            ).distinct()
        severity_id = request.GET.get("severity_id", "").strip()
        if severity_id.isdigit():
            queryset = queryset.filter(severity_id=int(severity_id))
        unit_id = request.GET.get("unit_id", "").strip()
        if unit_id.isdigit():
            queryset = queryset.filter(fault_report__unit_id=int(unit_id))
        queryset = date_range(queryset, request)
        severity_name = Severity.objects.filter(pk=severity_id).values_list("name", flat=True).first() if severity_id.isdigit() else ""
        return list_response(
            request,
            queryset,
            key="diagnoses",
            serialize=lambda d: serialize_diagnosis(d, request.user),
            sorts=DIAGNOSIS_SORTS,
            default="-date",
            export={
                "title": "Diagnósticos",
                "filters": filter_lines(("Búsqueda", search), ("Gravedad", severity_name), dates_line(request)),
                "columns": [
                    ("Diagnóstico", 3, lambda d: d["title"]),
                    ("Fecha", 1.2, lambda d: d["date"]),
                    ("Unidad", 2.2, lambda d: d["unit"]["label"]),
                    ("Causa", 3.5, lambda d: d["detailed_cause"]),
                    ("Gravedad", 1.2, lambda d: d["severity"]["label"]),
                    ("Requiere reparación", 1.3, lambda d: d["requires_repair"]),
                    ("Unidad operable", 1.2, lambda d: d["unit_operable"]),
                    ("Mecánico", 2.2, lambda d: d["diagnosed_by"]["label"]),
                ],
            },
        )

    if not is_mechanic(request.user):
        return JsonResponse({"error": "Solo los mecánicos pueden registrar diagnósticos."}, status=403)
    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)

    errors, diagnosis = validate_diagnosis(data, FaultDiagnosis(diagnosed_by=request.user))
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    with transaction.atomic():
        diagnosis.folio = next_folio(FaultDiagnosis, "diagnosed_by", request.user)
        diagnosis.save()
        refresh_report_status(diagnosis.fault_report, request.user)
    return JsonResponse(
        {"diagnosis": serialize_diagnosis(diagnoses_queryset(request.user).get(pk=diagnosis.pk), request.user)},
        status=201,
    )


@view_roles
@require_http_methods(["GET", "PUT", "DELETE"])
def diagnosis_detail(request, pk):
    diagnosis = diagnoses_queryset(request.user).filter(pk=pk).first()
    if diagnosis is None:
        return JsonResponse({"error": "El diagnóstico no existe"}, status=404)

    if request.method == "GET":
        data = serialize_diagnosis(diagnosis, request.user)
        if wants_pdf(request):
            return sheets.diagnosis_sheet(request.user, data)
        return JsonResponse({"diagnosis": data})

    if not is_mechanic(request.user):
        return JsonResponse({"error": "Solo los mecánicos pueden modificar diagnósticos."}, status=403)

    if request.method == "DELETE":
        try:
            with transaction.atomic():
                report = diagnosis.fault_report
                diagnosis.delete()
                report.refresh_from_db()
                refresh_report_status(report, request.user)
        except ProtectedError:
            return JsonResponse(
                {"error": "No se puede eliminar: el diagnóstico ya tiene mantenimientos."}, status=409
            )
        return JsonResponse({"ok": True})

    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, diagnosis = validate_diagnosis(data, diagnosis)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    with transaction.atomic():
        diagnosis.save()
        # Saying that it needs (or not) a repair changes the status
        report = diagnosis.fault_report
        report.refresh_from_db()
        refresh_report_status(report, request.user)
    return JsonResponse(
        {"diagnosis": serialize_diagnosis(diagnoses_queryset(request.user).get(pk=diagnosis.pk), request.user)}
    )


@view_roles
@require_GET
def catalogs(request):
    """
    Options for the diagnosis form: severities and the reports that have no diagnosis yet
    (for a mechanic, only those assigned to them).
    """
    reports = FaultReport.objects.filter(diagnosis__isnull=True)
    if is_mechanic(request.user):
        reports = reports.filter(pk__in=reports_of(request.user).values("pk"))
    reports = reports.select_related("unit__unit_model__brand", "reported_by").order_by("-date", "-id")
    return JsonResponse(
        {
            "severities": [{"id": s.pk, "label": s.name} for s in Severity.objects.order_by("pk")],
            "reports": [{"id": r.pk, "label": report_label(r), "description": r.description} for r in reports],
        }
    )
