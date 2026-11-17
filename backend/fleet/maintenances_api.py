"""
JSON API for maintenances.

  - Managers can see every maintenance (read only).
  - Mechanics can see, create, edit and delete the maintenances they took part in (their own).
  - Everybody else has no access.
A maintenance is "corrective" (it comes from a diagnosis) or "preventive" (no diagnosis, so
the unit is chosen directly). The mechanic who registers it is always one of its operators.
"""
import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from accounts.models import User
from accounts.permissions import roles_required, validation_only
from common.listing import date_range, dates_line, filter_lines, list_response, wants_pdf
from accounts.roles import MANAGER_ROLE, MECHANIC_ROLE

from . import sheets
from .assignments import reports_of
from .diagnoses_api import diagnosis_title, is_mechanic
from .folios import next_folio
from .inventory import stock_of, with_stock
from .models import (
    FaultDiagnosis,
    FaultReportStatus,
    Maintenance,
    MaintenancePlan,
    MaintenanceSparePart,
    ServiceType,
    SparePart,
    Unit,
)
from .report_status import REPAIRED_STATUS, refresh_report_status
from .reports_api import add_error, parse_body, record_title, unit_label

MAX_PARTS_PER_ITEM = 9999  # pieces of one part in one maintenance
PREVENTIVE = "Preventivo"
CORRECTIVE = "Correctivo"

view_roles = roles_required(MANAGER_ROLE, MECHANIC_ROLE)


MAINTENANCE_SORTS = {
    "date": ("date",),
    "unit": ("unit__economic_number",),
    "service_type": ("service_type__name",),
    "cost": ("total_cost",),
    "mileage": ("service_mileage",),
}


def maintenances_queryset(user):
    """
    Maintenances the user can see: all of them for managers. A mechanic sees the corrective ones
    of the reports assigned to them, and the preventive ones they took part in.
    """
    queryset = (
        Maintenance.objects.select_related(
            "unit__unit_model__brand", "service_type", "diagnosis__fault_report", "diagnosis__diagnosed_by",
            "registered_by", "plan"
        )
        .prefetch_related("operators", Prefetch("part_usages", queryset=MaintenanceSparePart.objects.select_related("spare_part")))
        .order_by("-date", "-id")
    )
    if is_mechanic(user):
        took_part = Maintenance.objects.filter(operators=user).values("pk")
        queryset = queryset.filter(
            Q(diagnosis__isnull=True, pk__in=took_part)
            | Q(diagnosis__fault_report__in=reports_of(user).values("pk"))
        )
    return queryset


def person_label(user):
    return f"{user.get_full_name()} ({user.enrollment_id})"


def maintenance_title(maintenance):
    return record_title(
        "Mantenimiento", maintenance.registered_by, maintenance.folio, maintenance.date, maintenance.unit
    )


def serialize_maintenance(maintenance, user):
    operators = list(maintenance.operators.all())
    diagnosis = maintenance.diagnosis
    return {
        "id": maintenance.pk,
        "title": maintenance_title(maintenance),
        "date": maintenance.date.isoformat(),
        "service_type": {"id": maintenance.service_type_id, "label": maintenance.service_type.name},
        "service_mileage": maintenance.service_mileage,
        "total_cost": str(maintenance.total_cost),
        "observations": maintenance.observations,
        "repair_completed": maintenance.repair_completed,
        "unit": {"id": maintenance.unit_id, "label": unit_label(maintenance.unit)},
        "diagnosis": (
            {"id": diagnosis.pk, "label": diagnosis_title(diagnosis), "detailed_cause": diagnosis.detailed_cause}
            if diagnosis
            else None
        ),
        "plan": {"id": maintenance.plan_id, "label": maintenance.plan.name} if maintenance.plan_id else None,
        "operators": [{"id": o.pk, "label": person_label(o)} for o in operators],
        "spare_parts": [
            {"id": u.spare_part_id, "label": str(u.spare_part), "quantity": u.quantity}
            for u in sorted(maintenance.part_usages.all(), key=lambda u: str(u.spare_part))
        ],
        # A mechanic only sees the maintenances they may work on (see maintenances_queryset)
        "can_modify": is_mechanic(user),
    }


def read_parts(value, errors):
    """
    The parts used, as {part id: pieces}. In the request: a list of {"id": 3, "quantity": 2}.
    Problems go to errors["spare_parts"].
    """
    if value is None:
        return {}
    if not isinstance(value, list):
        add_error(errors, "spare_parts", "Datos no válidos.")
        return {}
    parts = {}
    for item in value:
        try:
            part_id, quantity = int(item["id"]), int(item["quantity"])
        except (TypeError, ValueError, KeyError):
            add_error(errors, "spare_parts", "Datos no válidos.")
            return {}
        if part_id in parts:
            add_error(errors, "spare_parts", "Una refacción está repetida.")
        elif quantity < 1 or quantity > MAX_PARTS_PER_ITEM:
            add_error(
                errors, "spare_parts", f"La cantidad debe ser un número entero entre 1 y {MAX_PARTS_PER_ITEM}."
            )
        parts[part_id] = quantity
    known = dict(SparePart.objects.filter(pk__in=parts).values_list("pk", "name"))
    if len(known) != len(parts):
        add_error(errors, "spare_parts", "Alguna de las refacciones elegidas no es válida.")
    return parts


def stock_errors(parts, maintenance=None):
    """Messages for the parts that are not in stock in that amount (own pieces count as free)."""
    messages = []
    names = dict(SparePart.objects.filter(pk__in=parts).values_list("pk", "name"))
    for part_id, quantity in parts.items():
        if part_id not in names:
            continue
        available = stock_of(part_id, exclude_maintenance=maintenance)
        if quantity > available:
            messages.append(
                f"No hay existencias suficientes de {names[part_id]}: "
                f"disponibles {max(available, 0)}, pediste {quantity}."
            )
    return messages


class StockShortage(Exception):
    """Another maintenance took the pieces between the check and the save."""

    def __init__(self, messages):
        self.messages = messages


def save_parts(maintenance, parts):
    """
    Makes the parts of the maintenance be exactly `parts` ({part id: pieces}). The parts are
    locked and the stock checked again, so two maintenances cannot use the same last piece.
    """
    list(SparePart.objects.select_for_update().filter(pk__in=parts).values_list("pk", flat=True))
    messages = stock_errors(parts, maintenance)
    if messages:
        raise StockShortage(messages)
    MaintenanceSparePart.objects.filter(maintenance=maintenance).exclude(spare_part_id__in=parts).delete()
    for part_id, quantity in parts.items():
        MaintenanceSparePart.objects.update_or_create(
            maintenance=maintenance, spare_part_id=part_id, defaults={"quantity": quantity}
        )


def int_list(value):
    """A list of ids from the request, or None if it is not a list of whole numbers."""
    if value is None:
        return []
    if not isinstance(value, list):
        return None
    try:
        return [int(v) for v in value]
    except (TypeError, ValueError):
        return None


def validate_maintenance(data, user, maintenance=None):
    """
    Validate the data of a maintenance. Returns (errors, clean).
    When editing, the type, the diagnosis and the unit cannot change.
    """
    errors = {}
    clean = {}
    creating = maintenance is None

    if creating:
        service_type = None
        try:
            service_type = ServiceType.objects.filter(pk=int(data.get("service_type_id"))).first()
        except (TypeError, ValueError):
            pass
        if service_type is None:
            add_error(errors, "service_type_id", "Elige una opción válida.")
        clean["service_type"] = service_type

        diagnosis = unit = None
        if service_type is not None and service_type.name == CORRECTIVE:
            # Corrective: it comes from one of the mechanic's diagnoses that needs a repair
            try:
                diagnosis = (
                    FaultDiagnosis.objects.select_related("fault_report__status")
                    .filter(
                        pk=int(data.get("diagnosis_id")),
                        requires_repair=True,
                        fault_report__in=reports_of(user).values("pk"),
                    )
                    .first()
                )
            except (TypeError, ValueError):
                pass
            if diagnosis is None:
                add_error(
                    errors, "diagnosis_id",
                    "Elige un diagnóstico de un reporte asignado a ti que requiera reparación.",
                )
            elif diagnosis.fault_report.status.name == REPAIRED_STATUS:
                # A repaired report takes no more maintenances
                add_error(
                    errors, "diagnosis_id",
                    "Este reporte ya está reparado: no se pueden registrar más mantenimientos.",
                )
            else:
                unit = diagnosis.fault_report.unit
        elif service_type is not None:
            # Preventive: no diagnosis, the unit is chosen directly
            if data.get("diagnosis_id"):
                add_error(errors, "diagnosis_id", "Un mantenimiento preventivo no lleva diagnóstico.")
            try:
                unit = Unit.objects.filter(pk=int(data.get("unit_id")), is_active=True).first()
            except (TypeError, ValueError):
                pass
            if unit is None:
                add_error(errors, "unit_id", "Elige una opción válida.")
        clean["diagnosis"], clean["unit"] = diagnosis, unit

    try:
        clean["service_mileage"] = int(str(data.get("service_mileage", "")).strip())
        if clean["service_mileage"] < 0:
            raise ValueError
    except ValueError:
        add_error(errors, "service_mileage", "Ingresa un número entero mayor o igual a 0.")

    try:
        clean["total_cost"] = Decimal(str(data.get("total_cost", "")).strip())
        if not clean["total_cost"].is_finite():
            raise InvalidOperation
    except InvalidOperation:
        add_error(errors, "total_cost", "Ingresa un número válido.")

    try:
        clean["date"] = datetime.date.fromisoformat(str(data.get("date", "")))
        if clean["date"] > datetime.date.today():
            add_error(errors, "date", "La fecha no puede ser futura.")
    except ValueError:
        add_error(errors, "date", "Ingresa una fecha válida.")

    clean["observations"] = str(data.get("observations", "")).strip()

    # "The repair is finished": only for corrective maintenance (the one that has a diagnosis)
    completed = data.get("repair_completed", False)
    if isinstance(completed, str):
        completed = {"true": True, "false": False}.get(completed.lower())
    if not isinstance(completed, bool):
        add_error(errors, "repair_completed", "Datos no válidos.")
        completed = False
    has_diagnosis = clean.get("diagnosis") is not None if creating else maintenance.diagnosis_id is not None
    if completed and not has_diagnosis:
        add_error(
            errors, "repair_completed",
            "Solo un mantenimiento correctivo puede marcar la reparación como terminada.",
        )
    clean["repair_completed"] = completed

    # Operators: people who did the work. The mechanic who saves is always one of them.
    operator_ids = int_list(data.get("operator_ids"))
    if operator_ids is None:
        add_error(errors, "operator_ids", "Datos no válidos.")
        operator_ids = []
    operators = set(
        eligible_operators().filter(pk__in=operator_ids).values_list("pk", flat=True)
    )
    if len(operators) != len(set(operator_ids)):
        add_error(errors, "operator_ids", "Solo se pueden elegir mecánicos activos como participantes.")
    operators.add(user.pk)
    clean["operator_ids"] = operators

    # The preventive plan this service fulfils (optional, preventive only)
    clean["plan"] = None
    raw_plan = data.get("plan_id")
    if raw_plan not in (None, ""):
        target_unit = clean.get("unit") if creating else maintenance.unit
        if has_diagnosis:
            add_error(errors, "plan_id", "Solo un mantenimiento preventivo puede cumplir un plan.")
        elif target_unit is not None:
            try:
                plan = MaintenancePlan.objects.filter(pk=int(raw_plan)).first()
            except (TypeError, ValueError):
                plan = None
            current = None if creating else maintenance.plan_id
            if plan is None or (not plan.is_active and plan.pk != current):
                add_error(errors, "plan_id", "Elige un plan activo.")
            elif plan.unit_model_id not in (None, target_unit.unit_model_id):
                add_error(errors, "plan_id", "Ese plan no aplica al modelo de esta unidad.")
            else:
                clean["plan"] = plan
    clean["spare_parts"] = read_parts(data.get("spare_parts"), errors)
    if not errors:
        # An inactive part cannot be used in new work (a maintenance may keep the ones it already has)
        already = set(maintenance.part_usages.values_list("spare_part_id", flat=True)) if maintenance else set()
        for part in SparePart.objects.filter(pk__in=clean["spare_parts"], is_active=False):
            if part.pk not in already:
                add_error(errors, "spare_parts", f"{part.name} está inactiva: ya no se puede usar.")
        for message in stock_errors(clean["spare_parts"], maintenance):
            add_error(errors, "spare_parts", message)

    if not errors:
        candidate = maintenance or Maintenance(
            unit=clean["unit"],
            diagnosis=clean["diagnosis"],
            service_type=clean["service_type"],
            registered_by=user,
        )
        for field in ("service_mileage", "total_cost", "date", "observations", "repair_completed"):
            setattr(candidate, field, clean[field])
        try:
            candidate.full_clean(exclude=["folio"])
        except ValidationError as exc:
            errors.update({field: list(messages) for field, messages in exc.message_dict.items()})
        candidate.plan = clean["plan"]
        clean["candidate"] = candidate
    return errors, clean


def eligible_operators():
    """Active mechanics: the only people who can be listed as having done a maintenance."""
    return User.objects.filter(is_active=True, role__name=MECHANIC_ROLE).order_by("enrollment_id")


@view_roles
@require_http_methods(["GET", "POST"])
def maintenances(request):
    if request.method == "GET":
        queryset = maintenances_queryset(request.user)
        search = request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(unit__economic_number__icontains=search)
                | Q(unit__plate_assignments__license_plate__identifier__icontains=search)
                | Q(observations__icontains=search)
            ).distinct()
        type_id = request.GET.get("service_type_id", "").strip()
        if type_id.isdigit():
            queryset = queryset.filter(service_type_id=int(type_id))
        unit_id = request.GET.get("unit_id", "").strip()
        if unit_id.isdigit():
            queryset = queryset.filter(unit_id=int(unit_id))
        queryset = date_range(queryset, request)
        type_name = ServiceType.objects.filter(pk=type_id).values_list("name", flat=True).first() if type_id.isdigit() else ""
        return list_response(
            request,
            queryset,
            key="maintenances",
            serialize=lambda m: serialize_maintenance(m, request.user),
            sorts=MAINTENANCE_SORTS,
            default="-date",
            export={
                "title": "Mantenimientos",
                "filters": filter_lines(("Búsqueda", search), ("Tipo", type_name), dates_line(request)),
                "columns": [
                    ("Mantenimiento", 3, lambda m: m["title"]),
                    ("Fecha", 1.2, lambda m: m["date"]),
                    ("Tipo", 1.2, lambda m: m["service_type"]["label"]),
                    ("Unidad", 2.2, lambda m: m["unit"]["label"]),
                    ("Km", 1, lambda m: m["service_mileage"]),
                    ("Costo (MXN)", 1.3, lambda m: m["total_cost"]),
                    ("Refacciones", 3, lambda m: ", ".join(f"{p['label']} x{p['quantity']}" for p in m["spare_parts"]) or "-"),
                    ("Mecánicos", 2.4, lambda m: ", ".join(o["label"] for o in m["operators"]) or "-"),
                ],
            },
        )

    if not is_mechanic(request.user):
        return JsonResponse({"error": "Solo los mecánicos pueden registrar mantenimientos."}, status=403)
    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_maintenance(data, request.user)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    try:
        with transaction.atomic():
            maintenance = clean["candidate"]
            maintenance.folio = next_folio(Maintenance, "registered_by", request.user)
            maintenance.save()
            maintenance.operators.set(clean["operator_ids"])
            save_parts(maintenance, clean["spare_parts"])
            # The report's status follows its maintenances
            if clean["diagnosis"] is not None:
                refresh_report_status(clean["diagnosis"].fault_report, request.user)
    except StockShortage as exc:
        return JsonResponse({"errors": {"spare_parts": exc.messages}}, status=400)
    return JsonResponse(
        {"maintenance": serialize_maintenance(maintenances_queryset(request.user).get(pk=maintenance.pk), request.user)},
        status=201,
    )


@view_roles
@require_http_methods(["GET", "PUT", "DELETE"])
def maintenance_detail(request, pk):
    maintenance = maintenances_queryset(request.user).filter(pk=pk).first()
    if maintenance is None:
        return JsonResponse({"error": "El mantenimiento no existe"}, status=404)

    if request.method == "GET":
        data = serialize_maintenance(maintenance, request.user)
        if wants_pdf(request):
            return sheets.maintenance_sheet(request.user, data)
        return JsonResponse({"maintenance": data})

    if not is_mechanic(request.user):
        return JsonResponse({"error": "Solo los mecánicos pueden modificar mantenimientos."}, status=403)

    if request.method == "DELETE":
        diagnosis = maintenance.diagnosis
        with transaction.atomic():
            maintenance.delete()
            # The report's status follows the maintenances that are left
            if diagnosis is not None:
                report = diagnosis.fault_report
                report.refresh_from_db()
                refresh_report_status(report, request.user)
        return JsonResponse({"ok": True})

    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_maintenance(data, request.user, maintenance=maintenance)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    try:
        with transaction.atomic():
            maintenance.save()
            maintenance.operators.set(clean["operator_ids"])
            save_parts(maintenance, clean["spare_parts"])
            if maintenance.diagnosis is not None:
                report = maintenance.diagnosis.fault_report
                report.refresh_from_db()
                refresh_report_status(report, request.user)
    except StockShortage as exc:
        return JsonResponse({"errors": {"spare_parts": exc.messages}}, status=400)
    return JsonResponse(
        {"maintenance": serialize_maintenance(maintenances_queryset(request.user).get(pk=maintenance.pk), request.user)}
    )


@view_roles
@require_GET
def catalogs(request):
    """Options for the maintenance form."""
    diagnoses = (
        FaultDiagnosis.objects.filter(
            fault_report__in=reports_of(request.user).values("pk"), requires_repair=True
        )
        .exclude(fault_report__status__name=REPAIRED_STATUS)
        .select_related("fault_report__unit__unit_model__brand", "diagnosed_by")
        .order_by("-date", "-id")
    )
    units = Unit.objects.filter(is_active=True).select_related("unit_model__brand").order_by("economic_number")
    return JsonResponse(
        {
            "current_user_id": request.user.pk,
            "service_types": [{"id": t.pk, "label": t.name} for t in ServiceType.objects.order_by("pk")],
            "diagnoses": [
                {
                    "id": d.pk,
                    "label": diagnosis_title(d),
                    "detailed_cause": d.detailed_cause,
                }
                for d in diagnoses
            ],
            "units": [{"id": u.pk, "label": unit_label(u), "unit_model_id": u.unit_model_id} for u in units],
            # Active preventive plans (a plan without model applies to every unit)
            "plans": [
                {"id": p.pk, "label": p.name, "unit_model_id": p.unit_model_id}
                for p in MaintenancePlan.objects.filter(is_active=True).order_by("name")
            ],
            "operators": [{"id": u.pk, "label": person_label(u)} for u in eligible_operators()],
            # With how many pieces are in stock, so the form can show it
            "spare_parts": [
                {"id": p.pk, "label": str(p), "stock": p.stock}
                for p in with_stock(SparePart.objects.filter(is_active=True)).order_by("name")
            ],
        }
    )
