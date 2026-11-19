"""
JSON API to manage units. Only users with the manager role can use it.

A unit has an economic number (its identifier), a model (and through it a brand), a mileage,
a history of license plates and a history of the operators it was assigned to.
The current plate is the one with no end date. The same goes for the operator, and it is
exclusive: a unit has at most one open assignment and an operator at most one open unit
(see fleet/assignments.py). Ending an assignment sets its end date; rows are never deleted.
"""
import datetime
import json

from django.db import IntegrityError, transaction
from django.db.models import Prefetch, Q
from django.db.models import ProtectedError
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from accounts.models import User
from accounts.permissions import manager_required, validation_only
from common.listing import date_range, dates_line, filter_lines, list_response
from accounts.roles import OPERATOR_ROLE
from locations.validation import check_state

from .assignments import open_assignment_of_unit, operator_label, operator_taken_message, unit_taken_message
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
    operators = list(unit.operator_assignments.all())
    current_operator = next((a for a in operators if a.end_date is None), None)
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
        # The one operator who has the unit now (or None), and the whole history, newest first
        "current_operator": serialize_operator_assignment(current_operator) if current_operator else None,
        "operators": [serialize_operator_assignment(a) for a in operators],
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


def read_object(data, key, errors):
    """The optional object under `key` ({} when absent or null; None when it is not an object)."""
    value = data.get(key)
    if value in (None, ""):
        return {}
    if not isinstance(value, dict):
        add_error(errors, "operator", "Datos de operador no válidos.")
        return None
    return value


def validate_operator_change(data, unit, errors, clean):
    """
    Validate the change of operator. The request may send:
      - end_operator {assignment_id, end_date}: end the open assignment of the unit;
      - new_operator {operator_id, start_date}: open a new one.
    Both together reassign the unit (the change of operator), saved in one transaction.
    Problems go under the "operator" field.
    """
    clean["end_operator"] = None
    clean["new_operator"] = None
    ending, starting = read_object(data, "end_operator", errors), read_object(data, "new_operator", errors)
    if ending is None or starting is None:
        return
    today = timezone.localdate()

    # Ending: it must be the open assignment of this unit
    ended = None
    if ending:
        assignment = None
        if unit is not None:
            try:
                assignment = unit.operator_assignments.select_related("operator").filter(
                    pk=int(ending.get("assignment_id")), end_date__isnull=True
                ).first()
            except (TypeError, ValueError):
                pass
        end_date = read_date(ending.get("end_date"))
        if assignment is None:
            add_error(errors, "operator", "La asignación que se quiere terminar no existe o ya terminó.")
        elif end_date is None:
            add_error(errors, "operator", "Ingresa una fecha de fin válida.")
        elif end_date > today:
            add_error(errors, "operator", "La fecha de fin no puede ser futura.")
        elif end_date < assignment.start_date:
            add_error(
                errors,
                "operator",
                f"La fecha de fin no puede ser anterior al inicio de la asignación ({assignment.start_date.isoformat()}).",
            )
        else:
            ended = (assignment, end_date)
            clean["end_operator"] = ended
    if ending and ended is None:
        return  # a reassignment whose first half is wrong: do not judge the second half yet

    if not starting:
        return
    operator = None
    try:
        operator = User.objects.filter(
            pk=int(starting.get("operator_id")), role__name=OPERATOR_ROLE, is_active=True
        ).first()
    except (TypeError, ValueError):
        pass
    if operator is None:
        add_error(errors, "operator", "Elige un operador activo.")
        return
    start_date = read_date(starting.get("start_date"))
    if start_date is None:
        add_error(errors, "operator", "Ingresa una fecha de inicio válida.")
        return
    if start_date > today:
        add_error(errors, "operator", "La fecha de inicio no puede ser futura.")
        return

    # The unit must be free, unless its open assignment is the one being ended in this request
    if ended is not None:
        if start_date < ended[1]:
            add_error(
                errors,
                "operator",
                f"El nuevo operador no puede empezar antes de que termine el anterior ({ended[1].isoformat()}).",
            )
            return
    elif unit is not None:
        message = unit_taken_message(unit)
        if message:
            add_error(errors, "operator", message)
            return
    # The operator must not have another unit open (the assignment ended here does not count)
    message = operator_taken_message(operator, exclude_pk=ended[0].pk if ended else None)
    if message:
        add_error(errors, "operator", message)
        return
    clean["new_operator"] = (operator, start_date)


def save_operator_change(unit, clean):
    """Apply the validated change. Ending comes first, so the new assignment can open the same day."""
    if clean["end_operator"] is not None:
        assignment, end_date = clean["end_operator"]
        assignment.end_date = end_date
        assignment.save(update_fields=["end_date"])
    if clean["new_operator"] is not None:
        operator, start_date = clean["new_operator"]
        UnitOperator.objects.create(unit=unit, operator=operator, start_date=start_date)


def operator_race_error(unit, clean):
    """
    The database refused an assignment that passed validation: someone assigned the same unit or
    operator in the meantime. Explain who has it now.
    """
    message = ""
    if clean["new_operator"] is not None:
        operator = clean["new_operator"][0]
        message = (unit_taken_message(unit) if unit is not None else "") or operator_taken_message(operator)
    return JsonResponse(
        {"errors": {"operator": [message or "Otra persona cambió esta asignación. Recarga la página."]}},
        status=400,
    )


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

    validate_operator_change(data, unit, errors, clean)

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
        if clean["new_operator"] is not None:
            add_error(errors, "operator", "No se puede asignar un operador a una unidad inactiva.")
        # An inactive unit cannot keep an operator: that operator could not get another unit
        current = open_assignment_of_unit(unit) if unit is not None else None
        ending = clean["end_operator"]
        if current is not None and (ending is None or ending[0].pk != current.pk):
            add_error(
                errors,
                "is_active",
                f"No se puede desactivar: la unidad tiene asignado a {operator_label(current.operator)}. "
                "Quita primero al operador.",
            )
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
                    ("Operador", 3, lambda u: u["current_operator"]["operator"]["label"] if u["current_operator"] else "-"),
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
            save_operator_change(unit, clean)
    except PlateConflict as exc:
        return JsonResponse({"errors": {exc.field: [exc.message]}}, status=400)
    except IntegrityError:
        return operator_race_error(None, clean)
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
            save_operator_change(unit, clean)
    except PlateConflict as exc:
        return JsonResponse({"errors": {exc.field: [exc.message]}}, status=400)
    except IntegrityError:
        return operator_race_error(unit, clean)
    return JsonResponse({"unit": serialize_unit(units_queryset().get(pk=unit.pk))})


@manager_required
@require_GET
def catalogs(request):
    """Options for the unit form: brands, models and the operators without a unit (plus the current one).

    Operators that can be assigned are active and have no open unit. With ?unidad=<id>, that unit's
    current operator is included too, marked "current".
    """
    busy = UnitOperator.objects.filter(end_date__isnull=True).values("operator_id")
    free = Q(role__name=OPERATOR_ROLE, is_active=True) & ~Q(pk__in=busy)
    current_id = None
    unit_id = request.GET.get("unidad", "").strip()
    if unit_id.isdigit():
        current_id = (
            UnitOperator.objects.filter(unit_id=int(unit_id), end_date__isnull=True)
            .values_list("operator_id", flat=True)
            .first()
        )
    operators = User.objects.filter(free | Q(pk=current_id)) if current_id else User.objects.filter(free)
    return JsonResponse(
        {
            "brands": [{"id": b.pk, "label": str(b)} for b in Brand.objects.order_by("name")],
            "models": [
                {"id": m.pk, "label": str(m), "brand_id": m.brand_id}
                for m in UnitModel.objects.order_by("name")
            ],
            "operators": [
                {"id": o.pk, "label": operator_label(o), "current": o.pk == current_id}
                for o in operators.order_by("enrollment_id")
            ],
        }
    )
