"""
JSON API for the preventive maintenance plans and for what is due.

  GET    /api/preventivo/vencimientos/   what is due (managers and mechanics; ?status=, ?q=)
  GET    /api/preventivo/planes/         the plans (managers and mechanics)
  POST   /api/preventivo/planes/         create a plan (managers)
  GET    /api/preventivo/planes/<id>/    one plan
  PUT    /api/preventivo/planes/<id>/    edit a plan (managers)
  DELETE /api/preventivo/planes/<id>/    delete a plan nobody has used (managers)
  GET    /api/preventivo/catalogos/      options of the plan form (managers)
"""

from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from accounts.permissions import manager_required, roles_required, validation_only
from common import pdf
from common.listing import filter_lines, list_response, wants_pdf
from accounts.roles import MANAGER_ROLE, MECHANIC_ROLE

from .models import MaintenancePlan, UnitModel
from .preventive import STATUS_LABELS, due_rows, summary
from .reports_api import add_error, parse_body
from .spare_parts_api import whole_number

view_roles = roles_required(MANAGER_ROLE, MECHANIC_ROLE)

MAX_INTERVAL = 10_000_000


def serialize_plan(plan, with_counts=True):
    return {
        "id": plan.pk,
        "name": plan.name,
        "description": plan.description,
        "every_km": plan.every_km,
        "every_days": plan.every_days,
        "unit_model": (
            {"id": plan.unit_model_id, "label": f"{plan.unit_model.brand.name} / {plan.unit_model.name}"}
            if plan.unit_model_id
            else None
        ),
        "is_active": plan.is_active,
        "services": plan.maintenances.count() if with_counts else None,
        # A plan that was used keeps its history: deactivate it instead of deleting it
        "can_delete": not plan.maintenances.exists(),
    }


def validate_plan(data, plan):
    errors, clean = {}, {}

    name = str(data.get("name", "")).strip()
    if not name:
        add_error(errors, "name", "Este campo es obligatorio.")
    elif len(name) > 120:
        add_error(errors, "name", "Máximo 120 caracteres.")
    elif MaintenancePlan.objects.filter(name__iexact=name).exclude(pk=plan.pk).exists():
        add_error(errors, "name", "Ya existe un plan con este nombre.")
    clean["name"] = name
    clean["description"] = str(data.get("description", "")).strip()

    for field, label in (("every_km", "kilómetros"), ("every_days", "días")):
        raw = data.get(field)
        clean[field] = None
        if raw not in (None, ""):
            value = whole_number(raw)
            if value is None or value < 1 or value > MAX_INTERVAL:
                add_error(errors, field, f"Ingresa un número entero de {label} mayor a 0.")
            else:
                clean[field] = value
    if (
        clean["every_km"] is None
        and clean["every_days"] is None
        and "every_km" not in errors
        and "every_days" not in errors
    ):
        add_error(errors, "every_km", "Indica cada cuántos kilómetros o cada cuántos días se repite.")

    clean["unit_model"] = None
    raw_model = data.get("unit_model_id")
    if raw_model not in (None, ""):
        model_id = whole_number(raw_model)
        clean["unit_model"] = UnitModel.objects.filter(pk=model_id).first() if model_id else None
        if clean["unit_model"] is None:
            add_error(errors, "unit_model_id", "Elige una opción válida.")

    active = data.get("is_active", True)
    if not isinstance(active, bool):
        add_error(errors, "is_active", "Datos no válidos.")
        active = True
    clean["is_active"] = active
    return errors, clean


@view_roles
@require_GET
def due(request):
    """What is due, most urgent first. The counts cover everything; the list can be filtered."""
    rows = due_rows()
    counts = summary(rows)
    status = request.GET.get("status", "").strip()
    if status in STATUS_LABELS:
        rows = [r for r in rows if r["status"] == status]
    text = request.GET.get("q", "").strip().lower()
    if text:
        rows = [r for r in rows if text in r["unit"]["label"].lower() or text in r["plan"]["name"].lower()]
    if wants_pdf(request):
        return pdf.list_pdf(
            request.user,
            "Mantenimiento preventivo: vencimientos",
            filter_lines(("Búsqueda", text), ("Estado", STATUS_LABELS.get(status, ""))),
            [("Unidad", 2.4), ("Plan", 3), ("Estado", 1.6), ("Detalle", 5)],
            [[r["unit"]["label"], r["plan"]["name"], r["status_label"], r["message"]] for r in rows],
        )
    return JsonResponse({"rows": rows, "summary": counts})


PLAN_SORTS = {
    "name": ("name",),
    "every_km": ("every_km",),
    "every_days": ("every_days",),
    "is_active": ("is_active",),
}


@view_roles
@require_http_methods(["GET", "POST"])
def plans(request):
    if request.method == "GET":
        queryset = MaintenancePlan.objects.select_related("unit_model__brand")
        search = request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        status = request.GET.get("status", "")
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)
        return list_response(
            request,
            queryset,
            key="plans",
            serialize=serialize_plan,
            sorts=PLAN_SORTS,
            default="name",
            export={
                "title": "Planes de mantenimiento preventivo",
                "filters": filter_lines(
                    ("Búsqueda", search),
                    ("Estado", {"active": "Activos", "inactive": "Inactivos"}.get(status, "")),
                ),
                "columns": [
                    ("Plan", 3, lambda p: p["name"]),
                    ("Cada (km)", 1, lambda p: p["every_km"] or "-"),
                    ("Cada (días)", 1, lambda p: p["every_days"] or "-"),
                    ("Modelo", 2, lambda p: p["unit_model"]["label"] if p["unit_model"] else "Todos"),
                    ("Activo", 0.8, lambda p: p["is_active"]),
                    ("Servicios", 0.9, lambda p: p["services"]),
                    ("Descripción", 4, lambda p: p["description"]),
                ],
            },
        )

    if request.user.role.name != MANAGER_ROLE:
        return JsonResponse({"error": "Solo el gerente puede administrar los planes"}, status=403)
    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_plan(data, MaintenancePlan())
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    plan = MaintenancePlan.objects.create(**clean)
    return JsonResponse({"plan": serialize_plan(plan)}, status=201)


@view_roles
@require_http_methods(["GET", "PUT", "DELETE"])
def plan_detail(request, pk):
    plan = MaintenancePlan.objects.select_related("unit_model__brand").filter(pk=pk).first()
    if plan is None:
        return JsonResponse({"error": "El plan no existe"}, status=404)
    if request.method == "GET":
        return JsonResponse({"plan": serialize_plan(plan)})

    if request.user.role.name != MANAGER_ROLE:
        return JsonResponse({"error": "Solo el gerente puede administrar los planes"}, status=403)
    if request.method == "DELETE":
        if plan.maintenances.exists():
            return JsonResponse(
                {"error": "No se puede eliminar: ya hay mantenimientos de este plan. Desactívalo."},
                status=409,
            )
        plan.delete()
        return JsonResponse({"ok": True})

    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_plan(data, plan)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    for field, value in clean.items():
        setattr(plan, field, value)
    plan.save()
    return JsonResponse({"plan": serialize_plan(plan)})


@manager_required
@require_GET
def catalogs(request):
    return JsonResponse(
        {
            "models": [
                {"id": m.pk, "label": f"{m.brand.name} / {m.name}"}
                for m in UnitModel.objects.select_related("brand").order_by("brand__name", "name")
            ]
        }
    )
