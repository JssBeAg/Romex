"""
JSON API for the spare parts and their stock (managers only).

  GET    /api/refacciones/                     list with stock (?q=text, ?low=1 only low stock)
  POST   /api/refacciones/                     create (optional initial_stock becomes an entry)
  GET    /api/refacciones/<id>/                one part, with its history of pieces in and out
  PUT    /api/refacciones/<id>/                edit name, description, price and minimum stock
  DELETE /api/refacciones/<id>/                only while no maintenance has used it
  POST   /api/refacciones/<id>/movimientos/    an entry (purchase) or an adjustment (count)
  GET    /api/refacciones/<id>/foto/           the photo (404 when it has none)
  POST   /api/refacciones/<id>/foto/           upload or replace it (multipart, field "photo")
  DELETE /api/refacciones/<id>/foto/           remove it

Pieces go out only by being used in a maintenance (see maintenances_api.py). The stock is
worked out each time (see inventory.py), never typed in.
"""

import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import F, Q
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_http_methods

from accounts.permissions import manager_required, validation_only
from accounts.photos import PhotoError, photo_url, process_photo, remove_photo_file
from common.listing import date_range, dates_line, filter_lines, list_response, wants_pdf

from .inventory import is_low, stock_of, with_stock
from . import sheets
from .models import InventoryMovement, MaintenanceSparePart, SparePart
from .reports_api import add_error, parse_body

MAX_QUANTITY = 1_000_000
MAX_PRICE = Decimal("9999999999.99")


def whole_number(value):
    """An int from the request (a number or a numeric text), or None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return None


def person(user):
    return f"{user.get_full_name()} ({user.enrollment_id})" if user else "Sistema"


def serialize_part(part):
    """`part` comes from with_stock(): it has received, used and stock."""
    return {
        "id": part.pk,
        "name": part.name,
        "description": part.description,
        "unit_price": None if part.unit_price is None else str(part.unit_price),
        "min_stock": part.min_stock,
        "stock": part.stock,
        "used": part.used,
        "is_active": part.is_active,
        "photo_url": photo_url(part, "refacciones"),
        # (an inactive part gives no alerts)
        "low_stock": part.is_active and is_low(part.stock, part.min_stock),
        # Only a part no maintenance has used can be deleted
        "can_delete": part.used == 0,
    }


def history_of(part):
    """
    What happened to the stock of a part, newest first: entries and adjustments, and the
    pieces used in maintenances, each with the stock that was left after it.
    """
    events = []
    for m in InventoryMovement.objects.filter(spare_part=part).select_related("registered_by"):
        events.append(
            {
                "date": m.date,
                "order": 0,  # on the same day, pieces come in before they go out
                "id": m.pk,
                "kind": m.get_movement_type_display(),
                "change": m.quantity,
                "detail": m.note,
                "who": person(m.registered_by),
                "link": None,
            }
        )
    usages = MaintenanceSparePart.objects.filter(spare_part=part).select_related(
        "maintenance__unit", "maintenance__registered_by"
    )
    for u in usages:
        mt = u.maintenance
        events.append(
            {
                "date": mt.date,
                "order": 1,
                "id": u.pk,
                "kind": "Uso en mantenimiento",
                "change": -u.quantity,
                "detail": f"Unidad {mt.unit.economic_number}",
                "who": person(mt.registered_by),
                "link": f"/mantenimientos/{mt.pk}",
            }
        )
    events.sort(key=lambda e: (e["date"], e["order"], e["id"]))
    balance = 0
    for e in events:
        balance += e["change"]
        e["balance"] = balance
        e["date"] = e["date"].isoformat()
        del e["order"]
    return list(reversed(events))


def get_part(pk):
    return with_stock(SparePart.objects.filter(pk=pk)).first()


def validate_part(data, part, creating):
    """Returns (errors, clean). `clean` holds the values to save."""
    errors, clean = {}, {}

    name = str(data.get("name", "")).strip()
    if not name:
        add_error(errors, "name", "Este campo es obligatorio.")
    elif len(name) > 120:
        add_error(errors, "name", "Máximo 120 caracteres.")
    elif SparePart.objects.filter(name__iexact=name).exclude(pk=part.pk).exists():
        add_error(errors, "name", "Ya existe una refacción con este nombre.")
    clean["name"] = name

    clean["description"] = str(data.get("description", "")).strip()

    raw_price = data.get("unit_price")
    clean["unit_price"] = None
    if raw_price not in (None, ""):
        try:
            price = Decimal(str(raw_price).strip())
            if not price.is_finite() or price < 0:
                raise InvalidOperation
            if price > MAX_PRICE or price.as_tuple().exponent < -2:
                add_error(errors, "unit_price", "Ingresa un precio con máximo 2 decimales.")
            clean["unit_price"] = price
        except InvalidOperation:
            add_error(errors, "unit_price", "Ingresa un precio válido (0 o más).")

    raw_min = data.get("min_stock", 0)
    min_stock = 0 if raw_min in (None, "") else whole_number(raw_min)
    if min_stock is None or min_stock < 0 or min_stock > MAX_QUANTITY:
        add_error(errors, "min_stock", "Ingresa un número entero de 0 o más.")
        min_stock = 0
    clean["min_stock"] = min_stock

    raw_active = data.get("is_active", part.is_active if part.pk else True)
    if not isinstance(raw_active, bool):
        add_error(errors, "is_active", "Datos no válidos.")
        raw_active = True
    clean["is_active"] = raw_active

    clean["initial_stock"] = 0
    if creating:
        raw_initial = data.get("initial_stock", 0)
        initial = 0 if raw_initial in (None, "") else whole_number(raw_initial)
        if initial is None or initial < 0 or initial > MAX_QUANTITY:
            add_error(errors, "initial_stock", "Ingresa un número entero de 0 o más.")
            initial = 0
        clean["initial_stock"] = initial
    return errors, clean


def validate_movement(data, part):
    """Returns (errors, clean) for an entry or an adjustment of the part."""
    errors, clean = {}, {}

    movement_type = str(data.get("movement_type", "")).strip()
    if movement_type not in (InventoryMovement.ENTRY, InventoryMovement.ADJUSTMENT):
        add_error(errors, "movement_type", "Elige una opción válida.")
    clean["movement_type"] = movement_type

    quantity = whole_number(data.get("quantity"))
    if quantity is None or quantity == 0 or abs(quantity) > MAX_QUANTITY:
        add_error(errors, "quantity", "Ingresa un número entero distinto de cero.")
    elif movement_type == InventoryMovement.ENTRY and quantity < 0:
        add_error(errors, "quantity", "Una entrada debe sumar piezas (número positivo).")
    elif quantity < 0 and abs(quantity) > stock_of(part.pk):
        add_error(
            errors,
            "quantity",
            f"No puedes quitar más piezas de las que hay: existencias {max(stock_of(part.pk), 0)}.",
        )
    clean["quantity"] = quantity

    raw_date = str(data.get("date", "")).strip()
    try:
        date = datetime.date.fromisoformat(raw_date)
        if date > datetime.date.today():
            add_error(errors, "date", "La fecha no puede ser futura.")
    except ValueError:
        add_error(errors, "date", "Ingresa una fecha válida.")
        date = None
    clean["date"] = date

    note = str(data.get("note", "")).strip()
    if len(note) > 255:
        add_error(errors, "note", "Máximo 255 caracteres.")
    if movement_type == InventoryMovement.ADJUSTMENT and not note:
        add_error(errors, "note", "Explica el motivo del ajuste.")
    clean["note"] = note
    return errors, clean


PART_SORTS = {
    "name": ("name",),
    "stock": ("stock",),
    "min_stock": ("min_stock",),
    "price": ("unit_price",),
}


@manager_required
@require_http_methods(["GET", "POST"])
def spare_parts(request):
    if request.method == "GET":
        queryset = with_stock()
        search = request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        status = request.GET.get("status", "")
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)
        # Low stock as a database condition (the same rule as inventory.is_low)
        low = Q(is_active=True, min_stock__gt=0, stock__lte=F("min_stock"))
        low_count = queryset.filter(low).count()
        if request.GET.get("low") == "1":
            queryset = queryset.filter(low)
        return list_response(
            request,
            queryset,
            key="spare_parts",
            serialize=serialize_part,
            sorts=PART_SORTS,
            default="name",
            extra={"low_stock_count": low_count},
            export={
                "title": "Refacciones e inventario",
                "filters": filter_lines(
                    ("Búsqueda", search),
                    ("Estado", {"active": "Activas", "inactive": "Inactivas"}.get(status, "")),
                    ("Solo stock bajo", "Sí" if request.GET.get("low") == "1" else ""),
                ),
                "columns": [
                    ("Refacción", 3, lambda p: p["name"]),
                    ("Estado", 1, lambda p: "Activa" if p["is_active"] else "Inactiva"),
                    ("Existencias", 1.1, lambda p: p["stock"]),
                    ("Mínimo", 1, lambda p: p["min_stock"]),
                    ("Usadas", 1, lambda p: p["used"]),
                    ("Stock bajo", 1, lambda p: "Sí" if p["low_stock"] else "No"),
                    ("Precio ref. (MXN)", 1.4, lambda p: p["unit_price"] or "-"),
                    ("Descripción", 4, lambda p: p["description"]),
                ],
            },
        )

    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_part(data, SparePart(), creating=True)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    with transaction.atomic():
        part = SparePart.objects.create(
            name=clean["name"],
            description=clean["description"],
            unit_price=clean["unit_price"],
            min_stock=clean["min_stock"],
            is_active=clean["is_active"],
        )
        if clean["initial_stock"] > 0:
            InventoryMovement.objects.create(
                spare_part=part,
                movement_type=InventoryMovement.ENTRY,
                quantity=clean["initial_stock"],
                date=datetime.date.today(),
                note="Existencia inicial",
                registered_by=request.user,
            )
    return JsonResponse({"spare_part": serialize_part(get_part(part.pk))}, status=201)


@manager_required
@require_http_methods(["GET", "PUT", "DELETE"])
def spare_part_detail(request, pk):
    found = get_part(pk)
    if found is None:
        return JsonResponse({"error": "La refacción no existe"}, status=404)

    if request.method == "GET":
        data = {**serialize_part(found), "history": history_of(found)}
        if wants_pdf(request):
            return sheets.part_sheet(request.user, data)
        return JsonResponse({"spare_part": data})

    part = SparePart.objects.get(pk=pk)
    if request.method == "DELETE":
        if found.used > 0:
            return JsonResponse(
                {
                    "error": "No se puede eliminar: la refacción ya se usó en mantenimientos. "
                    "Desactívala para conservar su historial."
                },
                status=409
            )
        with transaction.atomic():
            InventoryMovement.objects.filter(spare_part=part).delete()
            part.delete()
        remove_photo_file(part)  # the file goes only once the row is really gone
        return JsonResponse({"ok": True})

    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_part(data, part, creating=False)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    part.name = clean["name"]
    part.description = clean["description"]
    part.unit_price = clean["unit_price"]
    part.min_stock = clean["min_stock"]
    part.is_active = clean["is_active"]
    part.save()
    found = get_part(pk)
    return JsonResponse({"spare_part": {**serialize_part(found), "history": history_of(found)}})


@manager_required
@require_http_methods(["POST"])
def spare_part_movements(request, pk):
    """The manager registers pieces that came in, or corrects the stock after a count."""
    part = SparePart.objects.filter(pk=pk).first()
    if part is None:
        return JsonResponse({"error": "La refacción no existe"}, status=404)
    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_movement(data, part)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)
    with transaction.atomic():
        # Locked, so a maintenance cannot use the pieces this adjustment takes off at the same time
        SparePart.objects.select_for_update().get(pk=pk)
        if clean["quantity"] < 0 and abs(clean["quantity"]) > stock_of(pk):
            return JsonResponse(
                {"errors": {"quantity": ["Las existencias cambiaron: revisa la cantidad."]}}, status=400
            )
        InventoryMovement.objects.create(
            spare_part=part,
            movement_type=clean["movement_type"],
            quantity=clean["quantity"],
            date=clean["date"],
            note=clean["note"],
            registered_by=request.user,
        )
    found = get_part(pk)
    return JsonResponse({"spare_part": {**serialize_part(found), "history": history_of(found)}}, status=201)


@manager_required
@require_http_methods(["GET", "POST", "DELETE"])
def spare_part_photo(request, pk):
    """
    The photo of a part (optional). Only managers use the spare parts, so only they can see,
    upload or remove it. What is uploaded is never stored as it comes: see accounts/photos.py.
    """
    part = SparePart.objects.filter(pk=pk).first()
    if part is None:
        return JsonResponse({"error": "La refacción no existe"}, status=404)

    if request.method == "GET":
        if not part.photo or not part.photo.storage.exists(part.photo.name):
            raise Http404
        response = FileResponse(part.photo.open("rb"), content_type="image/jpeg")
        response["X-Content-Type-Options"] = "nosniff"
        # The address carries a version (?v=), so a new photo is a new address
        response["Cache-Control"] = "private, max-age=86400"
        return response

    if request.method == "DELETE":
        if part.photo:
            remove_photo_file(part)
            part.photo = ""
            part.save(update_fields=["photo"])
        return JsonResponse({"spare_part": serialize_part(get_part(pk))})

    upload = request.FILES.get("photo")
    if upload is None:
        return JsonResponse({"errors": {"photo": ["Elige una fotografía."]}}, status=400)
    try:
        processed = process_photo(upload, square=False)
    except PhotoError as error:
        return JsonResponse({"errors": {"photo": [str(error)]}}, status=400)
    if validation_only(request):
        return JsonResponse({"errors": {}})
    previous = part.photo.name if part.photo else ""
    part.photo.save(processed.name, processed, save=False)
    part.save(update_fields=["photo"])
    if previous:
        part.photo.storage.delete(previous)
    return JsonResponse({"spare_part": serialize_part(get_part(pk))})
