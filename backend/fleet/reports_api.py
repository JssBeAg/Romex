"""
JSON API for fault reports.

  - Managers and mechanics can see every report (read only).
  - Operators can create reports and see, edit and delete their own, as long as the
    report is still pending. The author and the status are set by the server.
  - Everybody else (including administrators) has no access.
"""
import datetime
import json
import os

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch, ProtectedError, Q
from django.http import FileResponse, Http404, JsonResponse
from django.http.multipartparser import MultiPartParser, MultiPartParserError
from django.views.decorators.http import require_GET, require_http_methods

from accounts.models import User
from accounts.permissions import roles_required, validation_only
from accounts.roles import MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE

from common.listing import date_range, dates_line, filter_lines, list_response, wants_pdf

from . import sheets
from .assignments import NOT_ASSIGNED, assigned_units, may_use_unit, reports_of
from .evidence import CONTENT_TYPES, MAX_REQUEST_BYTES, check_images, to_content_file
from .folios import folio_code, next_folio
from .models import (
    FaultReport,
    FaultReportStatus,
    ReportEvidence,
    ReportMechanic,
    ReportStatusChange,
    Unit,
)
from .report_status import CLOSED_STATUSES, PENDING_STATUS, REPAIRED_STATUS, record_status, refresh_report_status

view_roles = roles_required(MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE)
manager_only = roles_required(MANAGER_ROLE)


def is_operator(user):
    return user.role is not None and user.role.name == OPERATOR_ROLE


def is_mechanic(user):
    return user.role is not None and user.role.name == MECHANIC_ROLE


def is_manager(user):
    return user.role is not None and user.role.name == MANAGER_ROLE


def reports_queryset(user):
    """
    Reports the user is allowed to see: all of them for managers, only their own for operators
    and only the ones assigned to them for mechanics.
    """
    mechanics = ReportMechanic.objects.select_related("mechanic").order_by("-start_date", "-id")
    changes = ReportStatusChange.objects.select_related("status", "changed_by").order_by("changed_at", "id")
    queryset = (
        FaultReport.objects.select_related(
            "unit__unit_model__brand", "status", "reported_by", "diagnosis"
        )
        .prefetch_related(
            "evidence_images",
            Prefetch("mechanic_assignments", queryset=mechanics),
            Prefetch("status_changes", queryset=changes),
        )
        .order_by("-date", "-id")
    )
    if is_operator(user):
        queryset = queryset.filter(reported_by=user)
    elif is_mechanic(user):
        queryset = queryset.filter(pk__in=reports_of(user).values("pk"))
    return queryset


def unit_label(unit):
    """Economic number of the unit, with its brand and model."""
    return f"{unit.economic_number} ({unit.unit_model.brand} / {unit.unit_model})"


def record_title(kind, author, folio, date, unit):
    """How a record is identified: kind, folio (author + number), date and the unit's economic number."""
    return f"{kind} {folio_code(author, folio)} · {date.isoformat()} · {unit.economic_number}"


def report_title(report):
    return record_title("Reporte", report.reported_by, report.folio, report.date, report.unit)


def can_modify(user, report):
    """Only the operator who wrote the report, while it is still pending."""
    return is_operator(user) and report.reported_by_id == user.pk and report.status.name == PENDING_STATUS


def mechanic_label(mechanic):
    return f"{mechanic.get_full_name()} ({mechanic.enrollment_id})"


def serialize_mechanic_assignment(assignment):
    return {
        "id": assignment.pk,
        "mechanic": {"id": assignment.mechanic_id, "label": mechanic_label(assignment.mechanic)},
        "start_date": assignment.start_date.isoformat(),
        "end_date": assignment.end_date.isoformat() if assignment.end_date else None,
    }


def serialize_report(report, user):
    reporter = report.reported_by
    return {
        "id": report.pk,
        "title": report_title(report),
        "date": report.date.isoformat(),
        "location": report.location,
        # Photos: the file is fetched from `url` (relative to /api/), which checks permissions
        "evidence": [
            {
                "id": e.pk,
                "name": e.original_name,
                "url": f"reportes-fallas/{report.pk}/evidencias/{e.pk}/",
            }
            for e in report.evidence_images.all()
        ],
        "description": report.description,
        "status": {"id": report.status_id, "label": report.status.name},
        "unit": {"id": report.unit_id, "label": unit_label(report.unit)},
        "reported_by": {"id": reporter.pk, "label": f"{reporter.get_full_name()} ({reporter.enrollment_id})"},
        "has_diagnosis": hasattr(report, "diagnosis"),
        "can_modify": can_modify(user, report),
        # Only managers see who it is assigned to and can change it (a repaired report needs no one)
        "mechanics": (
            [serialize_mechanic_assignment(a) for a in report.mechanic_assignments.all()]
            if is_manager(user)
            else []
        ),
        "can_assign": is_manager(user) and report.status.name not in CLOSED_STATUSES,
        # Every status the report has had, oldest first
        "status_history": [
            {
                "id": c.pk,
                "status": c.status.name,
                "changed_at": c.changed_at.isoformat(),
                "changed_by": (
                    f"{c.changed_by.get_full_name()} ({c.changed_by.enrollment_id})" if c.changed_by else "Sistema"
                ),
            }
            for c in report.status_changes.all()
        ],
    }


def read_report_request(request):
    """
    The data of a create/edit request: (data, photos, ids of photos to remove), or None if it
    cannot be read. Forms are sent as multipart (fields + photos); plain JSON also works.
    """
    content_type = request.META.get("CONTENT_TYPE", "")
    if content_type.startswith("multipart/form-data"):
        try:
            if request.method == "POST":
                post, files = request.POST, request.FILES
            else:
                # Django only reads multipart bodies for POST; read it by hand for PUT
                post, files = MultiPartParser(
                    request.META, request, request.upload_handlers, request.encoding
                ).parse()
        except MultiPartParserError:
            return None
        return post.dict(), files.getlist("images"), post.getlist("remove_evidence_ids")
    data = parse_body(request)
    if data is None:
        return None
    remove_ids = data.get("remove_evidence_ids", [])
    return data, [], remove_ids if isinstance(remove_ids, list) else []


def too_large(request):
    """The whole request is bigger than the photos allowed plus a margin for the other fields."""
    try:
        return int(request.META.get("CONTENT_LENGTH") or 0) > MAX_REQUEST_BYTES
    except ValueError:
        return True


def parse_body(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def add_error(errors, field, message):
    errors.setdefault(field, []).append(message)


def validate_report(data, report):
    """Validate the data a report is created or edited with. Returns (errors, report)."""
    errors = {}

    unit = None
    try:
        unit = Unit.objects.filter(pk=int(data.get("unit_id"))).first()
    except (TypeError, ValueError):
        pass
    if unit is None:
        add_error(errors, "unit_id", "Elige una opción válida.")
    elif not may_use_unit(report.reported_by, unit, report.unit_id):
        add_error(errors, "unit_id", NOT_ASSIGNED)

    try:
        date = datetime.date.fromisoformat(str(data.get("date", "")))
        if date > datetime.date.today():
            add_error(errors, "date", "La fecha no puede ser futura.")
    except ValueError:
        date = None
        add_error(errors, "date", "Ingresa una fecha válida.")

    report.location = str(data.get("location", "")).strip()
    report.description = str(data.get("description", "")).strip()
    if not report.location:
        add_error(errors, "location", "Este campo es obligatorio.")
    if not report.description:
        add_error(errors, "description", "Este campo es obligatorio.")

    if errors:
        return errors, report

    report.unit = unit
    report.date = date
    try:
        report.full_clean(exclude=["status", "reported_by", "folio"])
    except ValidationError as exc:
        errors.update({field: list(messages) for field, messages in exc.message_dict.items()})
    return errors, report


REPORT_SORTS = {
    "date": ("date",),
    "status": ("status__order",),
    "unit": ("unit__economic_number",),
    "location": ("location",),
    "reported_by": ("reported_by__first_name", "reported_by__paternal_surname"),
}


@view_roles
@require_http_methods(["GET", "POST"])
def reports(request):
    if request.method == "GET":
        queryset = reports_queryset(request.user)
        search = request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(unit__economic_number__icontains=search)
                | Q(unit__plate_assignments__license_plate__identifier__icontains=search)
                | Q(location__icontains=search)
            ).distinct()
        status_id = request.GET.get("status_id", "").strip()
        if status_id.isdigit():
            queryset = queryset.filter(status_id=int(status_id))
        unit_id = request.GET.get("unit_id", "").strip()
        if unit_id.isdigit():
            queryset = queryset.filter(unit_id=int(unit_id))
        queryset = date_range(queryset, request)
        status_name = FaultReportStatus.objects.filter(pk=status_id).values_list("name", flat=True).first() if status_id.isdigit() else ""
        return list_response(
            request,
            queryset,
            key="reports",
            serialize=lambda r: serialize_report(r, request.user),
            sorts=REPORT_SORTS,
            default="-date",
            export={
                "title": "Reportes de fallas",
                "filters": filter_lines(
                    ("Búsqueda", search), ("Estatus", status_name), dates_line(request)
                ),
                "columns": [
                    ("Reporte", 3, lambda r: r["title"]),
                    ("Fecha", 1.2, lambda r: r["date"]),
                    ("Unidad", 2.2, lambda r: r["unit"]["label"]),
                    ("Ubicación", 2.4, lambda r: r["location"]),
                    ("Falla", 3, lambda r: r["description"]),
                    ("Estatus", 1.6, lambda r: r["status"]["label"]),
                    ("Reportó", 2.2, lambda r: r["reported_by"]["label"]),
                    ("Mecánico", 2.2, lambda r: ", ".join(m["mechanic"]["label"] for m in r["mechanics"] if m["end_date"] is None) or "-"),
                ],
            },
        )

    if not is_operator(request.user):
        return JsonResponse({"error": "Solo los operadores pueden crear reportes."}, status=403)
    if too_large(request):
        return JsonResponse({"error": "Las imágenes superan el tamaño permitido."}, status=413)
    parsed = read_report_request(request)
    if parsed is None:
        return JsonResponse({"error": "Datos no válidos"}, status=400)
    data, files, _ = parsed

    # The author and the status are never taken from the request
    report = FaultReport(
        reported_by=request.user,
        status=FaultReportStatus.objects.get(name=PENDING_STATUS),
    )
    errors, report = validate_report(data, report)
    photos = check_images(files, 0, errors, add_error)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    with transaction.atomic():
        report.folio = next_folio(FaultReport, "reported_by", request.user)
        report.save()
        record_status(report, report.status, request.user)
        save_photos(report, photos)
    return JsonResponse(
        {"report": serialize_report(reports_queryset(request.user).get(pk=report.pk), request.user)},
        status=201,
    )


def save_photos(report, photos):
    for file, extension in photos:
        ReportEvidence.objects.create(
            fault_report=report,
            original_name=file.name[:255],
            image=to_content_file(file, extension),
        )


@view_roles
@require_http_methods(["GET", "PUT", "DELETE"])
def report_detail(request, pk):
    report = reports_queryset(request.user).filter(pk=pk).first()
    if report is None:
        return JsonResponse({"error": "El reporte no existe"}, status=404)

    if request.method == "GET":
        data = serialize_report(report, request.user)
        if wants_pdf(request):
            return sheets.report_sheet(request.user, data)
        return JsonResponse({"report": data})

    if not is_operator(request.user):
        return JsonResponse({"error": "Solo los operadores pueden modificar reportes."}, status=403)
    if not can_modify(request.user, report):
        return JsonResponse(
            {"error": "Solo puedes modificar tus reportes mientras estén pendientes."}, status=403
        )

    if request.method == "DELETE":
        try:
            with transaction.atomic():
                ReportMechanic.objects.filter(fault_report=report).delete()
                ReportStatusChange.objects.filter(fault_report=report).delete()
                report.delete()
        except ProtectedError:
            return JsonResponse(
                {"error": "No se puede eliminar: el reporte ya tiene un diagnóstico."}, status=409
            )
        return JsonResponse({"ok": True})

    if too_large(request):
        return JsonResponse({"error": "Las imágenes superan el tamaño permitido."}, status=413)
    parsed = read_report_request(request)
    if parsed is None:
        return JsonResponse({"error": "Datos no válidos"}, status=400)
    data, files, remove_ids = parsed

    errors, report = validate_report(data, report)
    current = {e.pk for e in report.evidence_images.all()}
    try:
        to_remove = {int(i) for i in remove_ids}
    except (TypeError, ValueError):
        to_remove = set()
        add_error(errors, "images", "Datos de imágenes no válidos.")
    if not to_remove <= current:
        add_error(errors, "images", "Alguna de las imágenes a quitar no existe.")
        to_remove &= current
    photos = check_images(files, len(current - to_remove), errors, add_error)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    with transaction.atomic():
        report.save()
        for evidence in ReportEvidence.objects.filter(fault_report=report, pk__in=to_remove):
            evidence.delete()
        save_photos(report, photos)
    return JsonResponse(
        {"report": serialize_report(reports_queryset(request.user).get(pk=report.pk), request.user)}
    )


@view_roles
@require_GET
def evidence_file(request, pk, evidence_id):
    """One photo of a report, only for people who can see that report."""
    report = reports_queryset(request.user).filter(pk=pk).first()
    evidence = ReportEvidence.objects.filter(fault_report=report, pk=evidence_id).first() if report else None
    if evidence is None or not os.path.isfile(evidence.image.path):
        raise Http404
    extension = evidence.image.name.rsplit(".", 1)[-1].lower()
    response = FileResponse(
        evidence.image.open("rb"), content_type=CONTENT_TYPES.get(extension, "application/octet-stream")
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, max-age=3600"
    return response


@view_roles
@require_GET
def catalogs(request):
    """
    Options for the report form and the list filter: units and statuses (and, for managers,
    the active mechanics a report can be assigned to). An operator only gets their own units.
    """
    units = assigned_units(request.user) if is_operator(request.user) else Unit.objects.filter(is_active=True)
    units = units.select_related("unit_model__brand").order_by("economic_number")
    return JsonResponse(
        {
            "units": [{"id": u.pk, "label": unit_label(u)} for u in units],
            "statuses": [{"id": s.pk, "label": s.name} for s in FaultReportStatus.objects.order_by("order", "pk")],
            "mechanics": (
                [
                    {"id": m.pk, "label": mechanic_label(m)}
                    for m in User.objects.filter(role__name=MECHANIC_ROLE, is_active=True).order_by(
                        "enrollment_id"
                    )
                ]
                if is_manager(request.user)
                else []
            ),
        }
    )


def read_date(value):
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


@manager_only
@require_http_methods(["POST"])
def report_mechanics(request, pk):
    """The manager assigns a mechanic to a report."""
    report = reports_queryset(request.user).filter(pk=pk).first()
    if report is None:
        return JsonResponse({"error": "El reporte no existe"}, status=404)
    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)

    errors = {}
    if report.status.name == REPAIRED_STATUS:
        add_error(errors, "mechanics", "El reporte ya está reparado: no necesita un mecánico.")
    elif report.status.name in CLOSED_STATUSES:
        add_error(errors, "mechanics", "El reporte ya está cerrado: no necesita un mecánico.")
    mechanic = None
    try:
        mechanic = User.objects.filter(
            pk=int(data.get("mechanic_id")), role__name=MECHANIC_ROLE, is_active=True
        ).first()
    except (TypeError, ValueError):
        pass
    if mechanic is None:
        add_error(errors, "mechanics", "Elige un mecánico activo.")
    start_date = read_date(data.get("start_date"))
    if start_date is None:
        add_error(errors, "mechanics", "Ingresa una fecha de inicio válida.")
    elif start_date > datetime.date.today():
        add_error(errors, "mechanics", "La fecha de inicio no puede ser futura.")
    if mechanic is not None and report.mechanic_assignments.filter(
        mechanic=mechanic, end_date__isnull=True
    ).exists():
        add_error(errors, "mechanics", f"{mechanic_label(mechanic)} ya está asignado a este reporte.")
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    with transaction.atomic():
        ReportMechanic.objects.create(fault_report=report, mechanic=mechanic, start_date=start_date)
        refresh_report_status(report, request.user)
    return JsonResponse(
        {"report": serialize_report(reports_queryset(request.user).get(pk=report.pk), request.user)},
        status=201,
    )


@manager_only
@require_http_methods(["PUT"])
def report_mechanic_detail(request, pk, assignment_id):
    """The manager ends the assignment of a mechanic to a report."""
    report = reports_queryset(request.user).filter(pk=pk).first()
    assignment = (
        report.mechanic_assignments.select_related("mechanic")
        .filter(pk=assignment_id, end_date__isnull=True)
        .first()
        if report
        else None
    )
    if assignment is None:
        return JsonResponse({"error": "La asignación no existe o ya terminó"}, status=404)
    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)

    name = mechanic_label(assignment.mechanic)
    end_date = read_date(data.get("end_date"))
    errors = {}
    if end_date is None:
        add_error(errors, "mechanics", f"{name}: ingresa una fecha de fin válida.")
    elif end_date > datetime.date.today():
        add_error(errors, "mechanics", f"{name}: la fecha de fin no puede ser futura.")
    elif end_date < assignment.start_date:
        add_error(
            errors,
            "mechanics",
            f"{name}: la fecha de fin no puede ser anterior al inicio de la asignación ({assignment.start_date.isoformat()}).",
        )
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    with transaction.atomic():
        assignment.end_date = end_date
        assignment.save(update_fields=["end_date"])
        refresh_report_status(report, request.user)
    return JsonResponse(
        {"report": serialize_report(reports_queryset(request.user).get(pk=report.pk), request.user)}
    )
