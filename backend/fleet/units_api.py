"""
JSON API to manage units. Only users with the manager role can use it.

A unit has an economic number (its identifier), a model (and through it a brand), a mileage,
a history of license plates and a history of the operators it was assigned to.
The current plate is the one with no end date; the same goes for the operators (a unit can
have several at once, and an operator several units).
"""
import datetime
import json

from django.db import transaction
from django.db.models import Prefetch, Q
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from accounts.models import User
from accounts.permissions import manager_required, validation_only
from common.listing import date_range, dates_line, filter_lines, list_response
from accounts.roles import OPERATOR_ROLE
from locations.validation import check_state

from .models import Brand, FaultReport, LicensePlate, Unit, UnitLicensePlate, UnitModel, UnitOperator
from .report_status import CLOSED_STATUSES

PLATE_MAX_LENGTH = LicensePlate._meta.get_field("identifier").max_length


class PlateConflict(Exception):
    """The requested plate cannot be assigned; carries the form field to blame."""

    def __init__(self, field, message):
        super().__init__(message)
        self.field = field
        self.message = message


UNIT_SORTS = {
    "economic_number": ("economic_number",),
    "brand": ("unit_model__brand__name", "unit_model__name"),
    "model": ("unit_model__name",),
    "mileage": ("mileage",),
}


def units_queryset():
    assignments = UnitLicensePlate.objects.select_related("license_plate").order_by(
        "-start_date", "-id"
    )
    operators = UnitOperator.objects.select_related("operator").order_by("-start_date", "-id")
    return (
        Unit.objects.select_related("unit_model__brand")
        .prefetch_related(
            Prefetch("plate_assignments", queryset=assignments),
            Prefetch("operator_assignments", queryset=operators),
        )
        .order_by("id")
    )


def operator_label(operator):
    return f"{operator.get_full_name()} ({operator.enrollment_id})"


def serialize_operator_assignment(assignment):
    return {
        "id": assignment.pk,
        "operator": {"id": assignment.operator_id, "label": operator_label(assignment.operator)},
        "start_date": assignment.start_date.isoformat(),
        "end_date": assignment.end_date.isoformat() if assignment.end_date else None,
    }


def serialize_assignment(assignment):
    plate = assignment.license_plate
    return {
        "identifier": plate.identifier,
        "state": plate.state,
        "start_date": assignment.start_date.isoformat(),
        "end_date": assignment.end_date.isoformat() if assignment.end_date else None,
    }


def serialize_unit(unit):
    # plate_assignments is prefetched, newest first; the current one has no end date
    assignments = list(unit.plate_assignments.all())
    current = next((a for a in assignments if a.end_date is None), None)
    unit_model = unit.unit_model
    return {
        "id": unit.pk,
        "economic_number": unit.economic_number,
        "mileage": unit.mileage,
        "is_active": unit.is_active,
        "unit_model": {"id": unit_model.pk, "label": str(unit_model)},
        "brand": {"id": unit_model.brand_id, "label": str(unit_model.brand)},
        "current_plate": serialize_assignment(current) if current else None,
        "plate_history": [serialize_assignment(a) for a in assignments],
        # Newest first; the ones with no end date are assigned now
        "operators": [serialize_operator_assignment(a) for a in unit.operator_assignments.all()],
    }


def parse_body(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def add_error(errors, field, message):
    errors.setdefault(field, []).append(message)


def get_or_none(model, value):
    try:
        return model.objects.filter(pk=int(value)).first()
    except (TypeError, ValueError):
        return None


ECONOMIC_NUMBER_MAX_LENGTH = Unit._meta.get_field("economic_number").max_length


def read_date(value):
    try:
        return datetime.date.fromisoformat(str(value))
    except ValueError:
        return None


def validate_operators(data, unit, errors, clean):
    """
    Validate the changes to the operators of the unit: assignments to start (add_operators) and
    assignments to end (end_operators). Problems go under the "operators" field.
    """
    clean["add_operators"] = []
    clean["end_operators"] = []
    adds, ends = data.get("add_operators") or [], data.get("end_operators") or []
    if not isinstance(adds, list) or not isinstance(ends, list) or not all(
        isinstance(item, dict) for item in adds + ends
    ):
        add_error(errors, "operators", "Datos de operadores no válidos.")
        return
    today = datetime.date.today()

    # Assignments to end: they must be assignments of this unit that are still in force
    ending = {}  # operator id -> the end date being set
    seen = set()
    for item in ends:
        assignment = None
        if unit is not None:
            try:
                assignment = unit.operator_assignments.select_related("operator").filter(
                    pk=int(item.get("assignment_id")), end_date__isnull=True
                ).first()
            except (TypeError, ValueError):
                pass
        if assignment is None:
            add_error(errors, "operators", "Una asignación que se quiere terminar no existe o ya terminó.")
            continue
        if assignment.pk in seen:
            continue
        seen.add(assignment.pk)
        name = operator_label(assignment.operator)
        end_date = read_date(item.get("end_date"))
        if end_date is None:
            add_error(errors, "operators", f"{name}: ingresa una fecha de fin válida.")
        elif end_date > today:
            add_error(errors, "operators", f"{name}: la fecha de fin no puede ser futura.")
        elif end_date < assignment.start_date:
            add_error(
                errors,
                "operators",
                f"{name}: la fecha de fin no puede ser anterior al inicio de la asignación ({assignment.start_date.isoformat()}).",
            )
        else:
            clean["end_operators"].append((assignment, end_date))
            ending[assignment.operator_id] = end_date

    # Assignments to start: active operators, not already having this unit
    added = set()
    for item in adds:
        operator = None
        try:
            operator = User.objects.filter(
                pk=int(item.get("operator_id")), role__name=OPERATOR_ROLE, is_active=True
            ).first()
        except (TypeError, ValueError):
            pass
        if operator is None:
            add_error(errors, "operators", "Elige un operador activo.")
            continue
        name = operator_label(operator)
        if operator.pk in added:
            add_error(errors, "operators", f"{name}: está repetido en la lista.")
            continue
        added.add(operator.pk)
        start_date = read_date(item.get("start_date"))
        if start_date is None:
            add_error(errors, "operators", f"{name}: ingresa una fecha de inicio válida.")
            continue
        if start_date > today:
            add_error(errors, "operators", f"{name}: la fecha de inicio no puede ser futura.")
            continue
        has_it_now = (
            unit is not None
            and unit.operator_assignments.filter(operator=operator, end_date__isnull=True).exists()
        )
        if has_it_now and operator.pk not in ending:
            add_error(errors, "operators", f"{name}: ya tiene asignada esta unidad.")
        elif operator.pk in ending and start_date < ending[operator.pk]:
            add_error(
                errors,
                "operators",
                f"{name}: la nueva asignación no puede empezar antes de que termine la anterior ({ending[operator.pk].isoformat()}).",
            )
        else:
            clean["add_operators"].append((operator, start_date))


def save_operator_changes(unit, clean):
    """Apply the validated changes. Ending comes first so an operator can start again the same day."""
    for assignment, end_date in clean["end_operators"]:
        assignment.end_date = end_date
        assignment.save(update_fields=["end_date"])
    for operator, start_date in clean["add_operators"]:
        UnitOperator.objects.create(unit=unit, operator=operator, start_date=start_date)


def validate_unit(data, plate_required, unit=None):
    """Validate the data of a unit. Returns (errors, clean). Nothing is saved here."""
    errors = {}
    clean = {}

    clean["economic_number"] = str(data.get("economic_number", "")).strip()
    if not clean["economic_number"]:
        add_error(errors, "economic_number", "Este campo es obligatorio.")
    elif len(clean["economic_number"]) > ECONOMIC_NUMBER_MAX_LENGTH:
        add_error(
            errors, "economic_number", f"Máximo {ECONOMIC_NUMBER_MAX_LENGTH} caracteres."
        )
    else:
        taken = Unit.objects.filter(economic_number__iexact=clean["economic_number"])
        if unit is not None:
            taken = taken.exclude(pk=unit.pk)
        if taken.exists():
            add_error(errors, "economic_number", "Ya existe una unidad con este número económico.")

    clean["unit_model"] = get_or_none(UnitModel, data.get("unit_model_id"))
    if clean["unit_model"] is None:
        add_error(errors, "unit_model_id", "Elige una opción válida.")

    try:
        clean["mileage"] = int(str(data.get("mileage", "")).strip())
        if clean["mileage"] < 0:
            raise ValueError
    except ValueError:
        clean["mileage"] = None
        add_error(errors, "mileage", "Ingresa un número entero mayor o igual a 0.")

    clean["plate"] = None
    raw = data.get("plate")
    if not raw:
        if plate_required:
            add_error(errors, "plate", "La placa es obligatoria.")
    elif not isinstance(raw, dict):
        add_error(errors, "plate", "Datos de placa no válidos.")
    else:
        state = str(raw.get("state", "")).strip()
        message = check_state(state)
        if message:
            add_error(errors, "plate_state", message)
        identifier = str(raw.get("identifier", "")).strip().upper()
        if not identifier:
            add_error(errors, "plate_identifier", "Este campo es obligatorio.")
        elif len(identifier) > PLATE_MAX_LENGTH:
            add_error(errors, "plate_identifier", f"Máximo {PLATE_MAX_LENGTH} caracteres.")
        try:
            start_date = datetime.date.fromisoformat(str(raw.get("start_date", "")))
        except ValueError:
            start_date = None
            add_error(errors, "plate_start_date", "Ingresa una fecha válida.")
        clean["plate"] = {"state": state, "identifier": identifier, "start_date": start_date}

    validate_operators(data, unit, errors, clean)

    # Active or not (when the request does not say, an existing unit keeps what it has)
    raw_active = data.get("is_active", unit.is_active if unit is not None else True)
    if not isinstance(raw_active, bool):
        add_error(errors, "is_active", "Datos no válidos.")
        raw_active = True
    clean["is_active"] = raw_active
    if not raw_active:
        if unit is not None and unit.is_active and FaultReport.objects.filter(unit=unit).exclude(
            status__name__in=CLOSED_STATUSES
        ).exists():
            add_error(errors, "is_active", "No se puede desactivar: la unidad tiene reportes de fallas abiertos.")
        if clean["add_operators"]:
            add_error(errors, "operators", "No se pueden asignar operadores a una unidad inactiva.")
    return errors, clean


def check_plate(unit, plate_data):
    """
    Check that the unit (None while it is being created) can get this plate. Writes nothing.
    Returns the unit's current assignment and the plate if it already exists.
    Raises PlateConflict when it cannot be done.
    """
    state, identifier, start = (plate_data[k] for k in ("state", "identifier", "start_date"))
    current = unit.plate_assignments.filter(end_date__isnull=True).first() if unit else None
    plate = LicensePlate.objects.filter(state=state, identifier=identifier).first()

    if plate is not None:
        in_use = UnitLicensePlate.objects.filter(license_plate=plate, end_date__isnull=True)
        if unit is not None:
            in_use = in_use.exclude(unit=unit)
        if in_use.exists():
            raise PlateConflict("plate_identifier", "Esa placa ya está asignada a otra unidad.")
        if current is not None and current.license_plate_id == plate.pk:
            raise PlateConflict("plate_identifier", "Esa placa ya es la vigente de esta unidad.")

    if current is not None and start < current.start_date:
        raise PlateConflict(
            "plate_start_date",
            f"La fecha de inicio no puede ser anterior al inicio de la placa actual ({current.start_date.isoformat()}).",
        )
    return current, plate


def assign_plate(unit, plate_data):
    """
    Give the unit a plate starting on a date. The plate it had before (if any) ends that day.
    Creates the plate if it does not exist yet. Raises PlateConflict when it cannot be done.
    """
    state, identifier, start = (plate_data[k] for k in ("state", "identifier", "start_date"))
    current, plate = check_plate(unit, plate_data)
    if plate is None:
        plate = LicensePlate.objects.create(state=state, identifier=identifier)
    if current is not None:
        current.end_date = start
        current.save(update_fields=["end_date"])
    UnitLicensePlate.objects.create(unit=unit, license_plate=plate, start_date=start)


def find_plate_conflict(unit, errors, clean):
    """Add to errors the problem with the plate (if any) once its own fields are valid."""
    plate = clean["plate"]
    plate_fields = ("plate_state", "plate_identifier", "plate_start_date")
    if plate is None or any(field in errors for field in plate_fields):
        return
    try:
        check_plate(unit, plate)
    except PlateConflict as exc:
        add_error(errors, exc.field, exc.message)


@manager_required
@require_http_methods(["GET", "POST"])
def units(request):
    if request.method == "GET":
        queryset = units_queryset()
        search = request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(economic_number__icontains=search)
                | Q(plate_assignments__license_plate__identifier__icontains=search)
            ).distinct()
        status = request.GET.get("status", "")
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)
        brand_id = request.GET.get("brand_id", "").strip()
        if brand_id.isdigit():
            queryset = queryset.filter(unit_model__brand_id=int(brand_id))
        brand_name = Brand.objects.filter(pk=brand_id).values_list("name", flat=True).first() if brand_id.isdigit() else ""
        return list_response(
            request,
            queryset,
            key="units",
            serialize=serialize_unit,
            sorts=UNIT_SORTS,
            default="economic_number",
            export={
                "title": "Unidades",
                "filters": filter_lines(
                    ("Búsqueda", search),
                    ("Marca", brand_name),
                    ("Estado", {"active": "Activas", "inactive": "Inactivas"}.get(status, "")),
                ),
                "columns": [
                    ("Número económico", 1.6, lambda u: u["economic_number"]),
                    ("Estado", 1, lambda u: "Activa" if u["is_active"] else "Inactiva"),
                    ("Placa actual", 1.6, lambda u: u["current_plate"]["identifier"] if u["current_plate"] else "Sin placa"),
                    ("Estado de la placa", 1.8, lambda u: u["current_plate"]["state"] if u["current_plate"] else "-"),
                    ("Marca", 1.6, lambda u: u["brand"]["label"]),
                    ("Modelo", 1.6, lambda u: u["unit_model"]["label"]),
                    ("Kilometraje", 1.2, lambda u: u["mileage"]),
                    ("Operadores vigentes", 3, lambda u: ", ".join(o["operator"]["label"] for o in u["operators"] if o["end_date"] is None) or "-"),
                ],
            },
        )

    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_unit(data, plate_required=True)
    find_plate_conflict(None, errors, clean)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    try:
        with transaction.atomic():
            unit = Unit.objects.create(
                economic_number=clean["economic_number"],
                unit_model=clean["unit_model"],
                mileage=clean["mileage"],
                is_active=clean["is_active"],
            )
            assign_plate(unit, clean["plate"])
            save_operator_changes(unit, clean)
    except PlateConflict as exc:
        return JsonResponse({"errors": {exc.field: [exc.message]}}, status=400)
    return JsonResponse({"unit": serialize_unit(units_queryset().get(pk=unit.pk))}, status=201)


@manager_required
@require_http_methods(["GET", "PUT", "DELETE"])
def unit_detail(request, pk):
    unit = units_queryset().filter(pk=pk).first()
    if unit is None:
        return JsonResponse({"error": "La unidad no existe"}, status=404)

    if request.method == "GET":
        return JsonResponse({"unit": serialize_unit(unit)})

    if request.method == "DELETE":
        try:
            with transaction.atomic():
                # The plate and operator histories belong to the unit; reports and checklists do not
                UnitLicensePlate.objects.filter(unit=unit).delete()
                UnitOperator.objects.filter(unit=unit).delete()
                unit.delete()
        except ProtectedError:
            return JsonResponse(
                {
                    "error": (
                        "No se puede eliminar: la unidad tiene registros asociados "
                        "(reportes de fallas, checklists o mantenimientos). Desactívala para conservar su historial."
                    )
                },
                status=409,
            )
        return JsonResponse({"ok": True})

    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_unit(data, plate_required=False, unit=unit)
    find_plate_conflict(unit, errors, clean)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    try:
        with transaction.atomic():
            unit.economic_number = clean["economic_number"]
            unit.unit_model = clean["unit_model"]
            unit.mileage = clean["mileage"]
            unit.is_active = clean["is_active"]
            unit.save()
            if clean["plate"] is not None:
                assign_plate(unit, clean["plate"])
            save_operator_changes(unit, clean)
    except PlateConflict as exc:
        return JsonResponse({"errors": {exc.field: [exc.message]}}, status=400)
    return JsonResponse({"unit": serialize_unit(units_queryset().get(pk=unit.pk))})


@manager_required
@require_GET
def catalogs(request):
    """Options for the unit form: brands, models (each with its brand) and the active operators."""
    return JsonResponse(
        {
            "brands": [{"id": b.pk, "label": str(b)} for b in Brand.objects.order_by("name")],
            "models": [
                {"id": m.pk, "label": str(m), "brand_id": m.brand_id}
                for m in UnitModel.objects.order_by("name")
            ],
            "operators": [
                {"id": o.pk, "label": operator_label(o)}
                for o in User.objects.filter(role__name=OPERATOR_ROLE, is_active=True).order_by(
                    "enrollment_id"
                )
            ],
        }
    )
