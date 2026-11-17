"""
JSON API for checklists (the pre-trip inspection of a unit).

  - Managers can see every checklist (read only).
  - Operators can create checklists and see, edit and delete their own.
  - Everybody else (mechanics, administrators) has no access.
The author and the folio are set by the server, never taken from the request.
"""
import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from accounts.permissions import roles_required, validation_only
from common.listing import date_range, dates_line, filter_lines, list_response, wants_pdf
from accounts.roles import MANAGER_ROLE, OPERATOR_ROLE

from . import sheets
from .assignments import NOT_ASSIGNED, assigned_units, may_use_unit
from .folios import folio_code, next_folio
from .models import Checklist, Unit
from .operability import NOT_OPERABLE, not_operable_unit_ids
from .reports_api import add_error, is_operator, parse_body, record_title, unit_label

view_roles = roles_required(MANAGER_ROLE, OPERATOR_ROLE)

BOOLEAN_FIELDS = ("lights_ok", "fluids_ok", "no_cracks")


CHECKLIST_SORTS = {
    "date": ("date",),
    "unit": ("unit__economic_number",),
    "completed_by": ("completed_by__first_name", "completed_by__paternal_surname"),
    "mileage": ("recorded_mileage",),
}


def checklists_queryset(user):
    """Checklists the user can see: all of them, or only their own for operators."""
    queryset = Checklist.objects.select_related("unit__unit_model__brand", "completed_by").order_by(
        "-date", "-id"
    )
    if is_operator(user):
        queryset = queryset.filter(completed_by=user)
    return queryset


def checklist_title(checklist):
    return record_title("Checklist", checklist.completed_by, checklist.folio, checklist.date, checklist.unit)


def serialize_checklist(checklist, user):
    author = checklist.completed_by
    return {
        "id": checklist.pk,
        "title": checklist_title(checklist),
        "folio": folio_code(author, checklist.folio),
        "date": checklist.date.isoformat(),
        "unit": {"id": checklist.unit_id, "label": unit_label(checklist.unit)},
        "completed_by": {"id": author.pk, "label": f"{author.get_full_name()} ({author.enrollment_id})"},
        "recorded_mileage": checklist.recorded_mileage,
        "tire_pressure": str(checklist.tire_pressure),
        "tire_tread_depth": str(checklist.tire_tread_depth),
        "lights_ok": checklist.lights_ok,
        "fluids_ok": checklist.fluids_ok,
        "no_cracks": checklist.no_cracks,
        "trip_description": checklist.trip_description,
        # Only the operator who wrote it
        "can_modify": is_operator(user) and checklist.completed_by_id == user.pk,
    }


def read_decimal(data, field, errors):
    try:
        value = Decimal(str(data.get(field, "")).strip())
        if not value.is_finite() or value < 0:
            raise InvalidOperation
        return value
    except InvalidOperation:
        add_error(errors, field, "Ingresa un número válido mayor o igual a 0.")
        return None


def validate_checklist(data, checklist):
    """Validate the data a checklist is created or edited with. Returns (errors, checklist)."""
    errors = {}

    unit = None
    try:
        unit = Unit.objects.filter(pk=int(data.get("unit_id"))).first()
    except (TypeError, ValueError):
        pass
    if unit is None:
        add_error(errors, "unit_id", "Elige una opción válida.")
    elif not may_use_unit(checklist.completed_by, unit, checklist.unit_id):
        add_error(errors, "unit_id", NOT_ASSIGNED)
    elif unit.pk != checklist.unit_id and unit.pk in not_operable_unit_ids():
        # A checklist is the check before going out: a unit that cannot operate takes no new one.
        # (One that already has this unit may keep it: past records are not rewritten.)
        add_error(errors, "unit_id", NOT_OPERABLE)

    date = None
    try:
        date = datetime.date.fromisoformat(str(data.get("date", "")))
        if date > datetime.date.today():
            add_error(errors, "date", "La fecha no puede ser futura.")
    except ValueError:
        add_error(errors, "date", "Ingresa una fecha válida.")

    mileage = None
    try:
        mileage = int(str(data.get("recorded_mileage", "")).strip())
        if mileage < 0:
            raise ValueError
    except ValueError:
        add_error(errors, "recorded_mileage", "Ingresa un número entero mayor o igual a 0.")

    pressure = read_decimal(data, "tire_pressure", errors)
    tread = read_decimal(data, "tire_tread_depth", errors)

    # Each check must be answered explicitly (true or false), there is no default
    for field in BOOLEAN_FIELDS:
        value = data.get(field)
        if isinstance(value, str):
            value = {"true": True, "false": False}.get(value.lower())
        if not isinstance(value, bool):
            add_error(errors, field, "Responde sí o no.")
        else:
            setattr(checklist, field, value)

    checklist.trip_description = str(data.get("trip_description", "")).strip()
    if not checklist.trip_description:
        add_error(errors, "trip_description", "Este campo es obligatorio.")

    if errors:
        return errors, checklist

    checklist.unit = unit
    checklist.date = date
    checklist.recorded_mileage = mileage
    checklist.tire_pressure = pressure
    checklist.tire_tread_depth = tread
    try:
        checklist.full_clean(exclude=["completed_by", "folio"])
    except ValidationError as exc:
        errors.update({field: list(messages) for field, messages in exc.message_dict.items()})
    return errors, checklist


@view_roles
@require_http_methods(["GET", "POST"])
def checklists(request):
    if request.method == "GET":
        queryset = checklists_queryset(request.user)
        search = request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(unit__economic_number__icontains=search)
                | Q(unit__plate_assignments__license_plate__identifier__icontains=search)
                | Q(trip_description__icontains=search)
            ).distinct()
        unit_id = request.GET.get("unit_id", "").strip()
        if unit_id.isdigit():
            queryset = queryset.filter(unit_id=int(unit_id))
        # ?problems=1 -> only checklists where something was not right
        problems = request.GET.get("problems") == "1"
        if problems:
            queryset = queryset.filter(Q(lights_ok=False) | Q(fluids_ok=False) | Q(no_cracks=False))
        queryset = date_range(queryset, request)
        yes_no = lambda value: "Sí" if value else "No"
        return list_response(
            request,
            queryset,
            key="checklists",
            serialize=lambda c: serialize_checklist(c, request.user),
            sorts=CHECKLIST_SORTS,
            default="-date",
            export={
                "title": "Checklists",
                "filters": filter_lines(
                    ("Búsqueda", search), dates_line(request), ("Solo con problemas", "Sí" if problems else "")
                ),
                "columns": [
                    ("Folio", 1.3, lambda c: c["folio"]),
                    ("Fecha", 1.3, lambda c: c["date"]),
                    ("Unidad", 2.4, lambda c: c["unit"]["label"]),
                    ("Operador", 2.4, lambda c: c["completed_by"]["label"]),
                    ("Km", 1, lambda c: c["recorded_mileage"]),
                    ("Presión llantas", 1.1, lambda c: c["tire_pressure"]),
                    ("Profundidad", 1.1, lambda c: c["tire_tread_depth"]),
                    ("Luces", 0.8, lambda c: yes_no(c["lights_ok"])),
                    ("Fluidos", 0.8, lambda c: yes_no(c["fluids_ok"])),
                    ("Sin grietas", 0.9, lambda c: yes_no(c["no_cracks"])),
                    ("Viaje", 3, lambda c: c["trip_description"]),
                ],
            },
        )

    if not is_operator(request.user):
        return JsonResponse({"error": "Solo los operadores pueden crear checklists."}, status=403)
    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)

    checklist = Checklist(completed_by=request.user)
    errors, checklist = validate_checklist(data, checklist)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    with transaction.atomic():
        checklist.folio = next_folio(Checklist, "completed_by", request.user)
        checklist.save()
    return JsonResponse(
        {"checklist": serialize_checklist(checklists_queryset(request.user).get(pk=checklist.pk), request.user)},
        status=201,
    )


@view_roles
@require_http_methods(["GET", "PUT", "DELETE"])
def checklist_detail(request, pk):
    checklist = checklists_queryset(request.user).filter(pk=pk).first()
    if checklist is None:
        return JsonResponse({"error": "El checklist no existe"}, status=404)

    if request.method == "GET":
        data = serialize_checklist(checklist, request.user)
        if wants_pdf(request):
            return sheets.checklist_sheet(request.user, data)
        return JsonResponse({"checklist": data})

    if not (is_operator(request.user) and checklist.completed_by_id == request.user.pk):
        return JsonResponse({"error": "Solo el operador que lo registró puede modificar un checklist."}, status=403)

    if request.method == "DELETE":
        checklist.delete()
        return JsonResponse({"ok": True})

    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, checklist = validate_checklist(data, checklist)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    checklist.save()
    return JsonResponse(
        {"checklist": serialize_checklist(checklists_queryset(request.user).get(pk=checklist.pk), request.user)}
    )


@view_roles
@require_GET
def catalogs(request):
    """
    Options for the checklist form: the units (only the assigned ones for an operator) that are fit
    to operate, and apart the ones that are left out for not being fit (so the form can say so).
    """
    units = assigned_units(request.user) if is_operator(request.user) else Unit.objects.filter(is_active=True)
    units = units.select_related("unit_model__brand").order_by("economic_number")
    blocked = not_operable_unit_ids()
    return JsonResponse(
        {
            "units": [{"id": u.pk, "label": unit_label(u)} for u in units if u.pk not in blocked],
            "not_operable": [{"id": u.pk, "label": unit_label(u)} for u in units if u.pk in blocked],
        }
    )
