"""
JSON API to manage workers (users). Only users with the manager role can use it.

Workers are the users of the system except administrators: administrator accounts
(superusers and the Administrador role) are never listed, changed or deleted here.
"""
import json

from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.http import FileResponse, Http404, JsonResponse

from common.listing import filter_lines, list_response
from django.views.decorators.http import require_GET, require_http_methods

from locations.models import Address
from locations.validation import check_address_place

from .contacts import (
    check_phone,
    serialize_code,
    serialize_contact,
    sync_contacts,
    validate_contacts,
)
from .models import MAX_CONTACTS, PhoneCode, Sex, User
from .permissions import manager_required, validation_only
from .photos import PhotoError, photo_url, process_photo, remove_photo_file
from .roles import ADMIN_ROLE, MECHANIC_ROLE, OPERATOR_ROLE

TEXT_FIELDS = [
    "enrollment_id",
    "first_name",
    "paternal_surname",
    "maternal_surname",
    "email",
]


WORKER_SORTS = {
    "enrollment_id": ("enrollment_id",),
    "name": ("first_name", "paternal_surname", "maternal_surname"),
    "role": ("role__name",),
    "is_active": ("is_active",),
}


def workers_queryset():
    return (
        User.objects.exclude(is_superuser=True)
        .exclude(role__name=ADMIN_ROLE)
        .select_related(
            "role", "sex", "phone_code", "address"
        )
        .prefetch_related(
            "unit_assignments__unit",
            "report_assignments__fault_report__unit",
            "contacts__phone_code",
        )
        .order_by("enrollment_id")
    )


def serialize_worker(user):
    address = user.address
    role = user.role
    return {
        "id": user.pk,
        "enrollment_id": user.enrollment_id,
        "first_name": user.first_name,
        "paternal_surname": user.paternal_surname,
        "maternal_surname": user.maternal_surname,
        "email": user.email,
        "phone_code": serialize_code(user.phone_code) if user.phone_code else None,
        "phone_number": user.phone_number,
        "phone_display": user.phone_display,
        "contacts": [serialize_contact(c) for c in user.contacts.all()],
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
        "locked": user.is_locked,
        "photo_url": photo_url(user),
        "sex": {"id": user.sex_id, "label": user.sex.name},
        "role": {"id": role.pk, "label": role.name} if role else None,
        # Units this operator has now (read only here: they are assigned from the unit)
        "assigned_units": [
            {
                "id": a.unit_id,
                "economic_number": a.unit.economic_number,
                "start_date": a.start_date.isoformat(),
            }
            for a in user.unit_assignments.all()
            if a.end_date is None
        ],
        # Fault reports this mechanic has now (read only: the manager assigns them from the report)
        "assigned_reports": [
            {
                "id": a.fault_report_id,
                "economic_number": a.fault_report.unit.economic_number,
                "date": a.fault_report.date.isoformat(),
                "location": a.fault_report.location,
                "start_date": a.start_date.isoformat(),
            }
            for a in user.report_assignments.all()
            if a.end_date is None
        ],
        "address": {
            "state": address.state,
            "municipality": address.municipality,
            "neighborhood": address.neighborhood,
            "street": address.street,
            "exterior_number": address.exterior_number,
            "interior_number": address.interior_number,
        },
    }


def parse_body(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def error_list(exc):
    """Messages of a Django ValidationError grouped by field."""
    if hasattr(exc, "message_dict"):
        return {field: list(messages) for field, messages in exc.message_dict.items()}
    return {"__all__": list(exc.messages)}


def add_error(errors, field, message):
    errors.setdefault(field, []).append(message)


def merge_model_errors(errors, exc):
    """Add the messages of a ValidationError to errors, without repeating one already there."""
    for field, messages in error_list(exc).items():
        for message in messages:
            if message not in errors.get(field, []):
                add_error(errors, field, message)


def get_or_none(model, value, **extra):
    try:
        return model.objects.filter(pk=int(value), **extra).first()
    except (TypeError, ValueError):
        return None


def validate_worker(data, request_user, worker=None):
    """
    Validate the data of a worker. Returns (errors, clean) where clean holds the objects
    needed to save: sex, role, state, municipality, the address numbers and the optional password.
    Nothing is saved here.
    """
    creating = worker is None
    errors = {}
    clean = {}

    for field in TEXT_FIELDS:
        value = str(data.get(field, "")).strip()
        if not value:
            add_error(errors, field, "Este campo es obligatorio.")
        clean[field] = value

    # Principal phone: country code + digits only
    allowed = {worker.phone_code_id} if worker is not None and worker.phone_code_id else set()
    code, number, found = check_phone(data.get("phone_code_id"), data.get("phone_number"), allowed)
    clean["phone_code"], clean["phone_number"] = code, number
    for message in found["code"]:
        add_error(errors, "phone_code_id", message)
    for message in found["number"]:
        add_error(errors, "phone_number", message)

    clean["sex"] = get_or_none(Sex, data.get("sex_id"))
    if clean["sex"] is None:
        add_error(errors, "sex_id", "Elige una opción válida.")

    clean["role"] = get_or_none(Group, data.get("role_id"))
    if clean["role"] is None or clean["role"].name == ADMIN_ROLE:
        clean["role"] = None
        add_error(errors, "role_id", "Elige una opción válida.")

    address = data.get("address") if isinstance(data.get("address"), dict) else {}
    # The state and the municipality are INEGI names, kept as text
    clean["state"] = str(address.get("state", "")).strip()
    clean["municipality"] = str(address.get("municipality", "")).strip()
    saved = worker.address if worker is not None else None
    for field, message in check_address_place(
        clean["state"],
        clean["municipality"],
        saved.state if saved else "",
        saved.municipality if saved else "",
    ).items():
        add_error(errors, field, message)
    # Colonia and street are free text
    for field in ("neighborhood", "street"):
        clean[field] = str(address.get(field, "")).strip()
        if not clean[field]:
            add_error(errors, field, "Este campo es obligatorio.")
    clean["exterior_number"] = str(address.get("exterior_number", "")).strip()
    clean["interior_number"] = str(address.get("interior_number", "")).strip()
    if not clean["exterior_number"]:
        add_error(errors, "exterior_number", "Este campo es obligatorio.")

    clean["is_active"] = bool(data.get("is_active", True))

    # Alternative contacts (None = the payload does not carry them: leave them as they are)
    contact_messages, clean["contacts"] = validate_contacts(
        data,
        worker,
        {"code": code, "number": number, "email": clean["email"].lower()},
    )
    for message in contact_messages:
        add_error(errors, "contacts", message)

    password = data.get("password") or ""
    clean["password"] = password
    if creating and not password:
        add_error(errors, "password", "Este campo es obligatorio.")

    # You cannot lock yourself out of this section
    if worker is not None and worker.pk == request_user.pk:
        if not clean["is_active"]:
            add_error(errors, "is_active", "No puedes desactivar tu propia cuenta.")
        if clean["role"] is not None and clean["role"] != worker.role:
            add_error(errors, "role_id", "No puedes cambiar tu propio rol.")

    # An operator who still has a unit cannot stop being an operator
    if (
        worker is not None
        and clean["role"] is not None
        and clean["role"].name != OPERATOR_ROLE
        and worker.unit_assignments.filter(end_date__isnull=True).exists()
    ):
        add_error(
            errors, "role_id", "Tiene una unidad asignada: termina primero su asignación en la unidad."
        )

    # The same for a mechanic who still has reports
    if (
        worker is not None
        and clean["role"] is not None
        and clean["role"].name != MECHANIC_ROLE
        and worker.report_assignments.filter(end_date__isnull=True).exists()
    ):
        add_error(
            errors, "role_id", "Tiene reportes asignados: termina primero sus asignaciones en los reportes."
        )

    # Let the models check lengths, formats and uniqueness. This runs even when other fields
    # are still missing (those are left out), so each field is reported as soon as it is filled.
    candidate = worker if worker is not None else User()
    skipped = ["password", "address", "last_login", "phone_number", "phone_code"]
    for field in TEXT_FIELDS:
        setattr(candidate, field, clean[field])
        if not clean[field]:
            skipped.append(field)
    if clean["role"] is not None:
        candidate.role = clean["role"]
    else:
        skipped.append("role")
    if clean["sex"] is not None:
        candidate.sex = clean["sex"]
    else:
        skipped.append("sex")
    candidate.is_active = clean["is_active"]
    try:
        candidate.full_clean(exclude=skipped)
    except ValidationError as exc:
        merge_model_errors(errors, exc)

    if clean["state"] and clean["municipality"]:
        address_candidate = worker.address if worker is not None else Address()
        address_candidate.state = clean["state"]
        address_candidate.municipality = clean["municipality"]
        address_candidate.neighborhood = clean["neighborhood"]
        address_candidate.street = clean["street"]
        address_candidate.exterior_number = clean["exterior_number"]
        address_candidate.interior_number = clean["interior_number"]
        # Empty required texts were already reported above
        empty = [f for f in ("neighborhood", "street", "exterior_number") if not clean[f]]
        try:
            address_candidate.full_clean(exclude=empty)
        except ValidationError as exc:
            merge_model_errors(errors, exc)

    if password:
        try:
            validate_password(password, candidate)
        except ValidationError as exc:
            errors["password"] = list(exc.messages)

    return errors, clean


@manager_required
@require_http_methods(["GET", "POST"])
def workers(request):
    if request.method == "GET":
        queryset = workers_queryset()
        search = request.GET.get("q", "").strip()
        if search:
            queryset = queryset.filter(
                Q(enrollment_id__icontains=search)
                | Q(first_name__icontains=search)
                | Q(paternal_surname__icontains=search)
                | Q(maternal_surname__icontains=search)
            )
        role_id = request.GET.get("role_id", "").strip()
        if role_id.isdigit():
            queryset = queryset.filter(role_id=int(role_id))
        status = request.GET.get("status", "")
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)
        role_name = Group.objects.filter(pk=role_id).values_list("name", flat=True).first() if role_id.isdigit() else ""
        return list_response(
            request,
            queryset,
            key="workers",
            serialize=serialize_worker,
            sorts=WORKER_SORTS,
            default="enrollment_id",
            export={
                "title": "Trabajadores",
                "filters": filter_lines(
                    ("Búsqueda", search),
                    ("Rol", role_name),
                    ("Estado", {"active": "Activos", "inactive": "Inactivos"}.get(status, "")),
                ),
                "columns": [
                    ("Matrícula", 1.2, lambda w: w["enrollment_id"]),
                    ("Nombre", 3.2, lambda w: f"{w['first_name']} {w['paternal_surname']} {w['maternal_surname']}"),
                    ("Rol", 1.3, lambda w: w["role"]["label"] if w["role"] else "-"),
                    ("Correo", 2.6, lambda w: w["email"]),
                    ("Teléfono", 1.8, lambda w: w["phone_display"]),
                    ("Activo", 0.9, lambda w: w["is_active"]),
                    ("Unidades asignadas", 2.2, lambda w: ", ".join(u["economic_number"] for u in w["assigned_units"]) or "-"),
                ],
            },
        )

    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_worker(data, request.user)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    with transaction.atomic():
        address = Address.objects.create(
            state=clean["state"],
            municipality=clean["municipality"],
            neighborhood=clean["neighborhood"],
            street=clean["street"],
            exterior_number=clean["exterior_number"],
            interior_number=clean["interior_number"],
        )
        user = User(
            role=clean["role"],
            sex=clean["sex"],
            address=address,
            is_active=clean["is_active"],
            phone_code=clean["phone_code"],
            phone_number=clean["phone_number"],
            **{field: clean[field] for field in TEXT_FIELDS},
        )
        user.set_password(clean["password"])
        # The manager chose this password: the worker must replace it on the first login
        user.must_change_password = True
        user.save()
        if clean["contacts"] is not None:
            sync_contacts(user, clean["contacts"])
    return JsonResponse({"worker": serialize_worker(workers_queryset().get(pk=user.pk))}, status=201)


@manager_required
@require_http_methods(["GET", "PUT", "DELETE"])
def worker_detail(request, pk):
    worker = workers_queryset().filter(pk=pk).first()
    if worker is None:
        return JsonResponse({"error": "El trabajador no existe"}, status=404)

    if request.method == "GET":
        return JsonResponse({"worker": serialize_worker(worker)})

    if request.method == "DELETE":
        if worker.pk == request.user.pk:
            return JsonResponse({"error": "No puedes eliminar tu propia cuenta."}, status=409)
        address = worker.address
        try:
            with transaction.atomic():
                photo_file = worker  # keeps the file name for the cleanup below
                worker.delete()
                address.delete()
        except ProtectedError:
            return JsonResponse(
                {
                    "error": (
                        "No se puede eliminar: el trabajador tiene registros asociados "
                        "(reportes, diagnósticos, checklists, mantenimientos o asignaciones). "
                        "Desactívalo en su lugar."
                    )
                },
                status=409,
            )
        remove_photo_file(photo_file)
        return JsonResponse({"ok": True})

    data = parse_body(request)
    if data is None:
        return JsonResponse({"error": "JSON no válido"}, status=400)
    errors, clean = validate_worker(data, request.user, worker=worker)
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    with transaction.atomic():
        address = worker.address
        address.state = clean["state"]
        address.municipality = clean["municipality"]
        address.neighborhood = clean["neighborhood"]
        address.street = clean["street"]
        address.exterior_number = clean["exterior_number"]
        address.interior_number = clean["interior_number"]
        address.save()
        for field in TEXT_FIELDS:
            setattr(worker, field, clean[field])
        worker.phone_code = clean["phone_code"]
        worker.phone_number = clean["phone_number"]
        worker.role = clean["role"]
        worker.sex = clean["sex"]
        worker.is_active = clean["is_active"]
        if clean["password"]:
            worker.set_password(clean["password"])
            worker.must_change_password = True
        # Saving a worker from the manager's screen also lifts a lock
        worker.failed_attempts = 0
        worker.locked_until = None
        worker.save()
        if clean["contacts"] is not None:
            sync_contacts(worker, clean["contacts"])
    return JsonResponse({"worker": serialize_worker(workers_queryset().get(pk=worker.pk))})


@manager_required
@require_GET
def catalogs(request):
    """Options for the worker form: sexes, roles, phone codes and contact limit."""
    return JsonResponse(
        {
            "sexes": [{"id": s.pk, "label": s.name} for s in Sex.objects.order_by("pk")],
            "roles": [
                {"id": g.pk, "label": g.name}
                for g in Group.objects.exclude(name=ADMIN_ROLE).order_by("name")
            ],
            # Only active codes are offered; the form adds the one a worker already has
            "phone_codes": [
                serialize_code(c) for c in PhoneCode.objects.filter(is_active=True).order_by("country_name")
            ],
            "max_contacts": MAX_CONTACTS,
        }
    )


@require_http_methods(["GET", "POST", "DELETE"])
def worker_photo(request, pk):
    """
    GET: the photo. The manager can see anyone's; everyone else only their own.
    POST (multipart, field "photo") and DELETE: only the manager. The photo is optional:
    without one the screens show the person's initials.
    """
    from .roles import MANAGER_ROLE

    if not request.user.is_authenticated:
        return JsonResponse({"error": "No has iniciado sesión"}, status=401)
    is_manager = request.user.role is not None and request.user.role.name == MANAGER_ROLE

    if request.method == "GET":
        if not is_manager and request.user.pk != pk:
            return JsonResponse({"error": "No tienes acceso a esta sección"}, status=403)
        worker = User.objects.filter(pk=pk).first()
        if worker is None or not worker.photo or not worker.photo.storage.exists(worker.photo.name):
            raise Http404
        response = FileResponse(worker.photo.open("rb"), content_type="image/jpeg")
        response["X-Content-Type-Options"] = "nosniff"
        # The address carries a version (?v=), so a new photo is a new address
        response["Cache-Control"] = "private, max-age=86400"
        return response

    if not is_manager:
        return JsonResponse({"error": "No tienes acceso a esta sección"}, status=403)
    worker = workers_queryset().filter(pk=pk).first()
    if worker is None:
        return JsonResponse({"error": "El trabajador no existe"}, status=404)

    if request.method == "DELETE":
        if worker.photo:
            remove_photo_file(worker)
            worker.photo = ""
            worker.save(update_fields=["photo"])
        return JsonResponse({"worker": serialize_worker(workers_queryset().get(pk=pk))})

    upload = request.FILES.get("photo")
    if upload is None:
        return JsonResponse({"errors": {"photo": ["Elige una fotografía."]}}, status=400)
    try:
        processed = process_photo(upload)
    except PhotoError as error:
        return JsonResponse({"errors": {"photo": [str(error)]}}, status=400)
    if validation_only(request):
        return JsonResponse({"errors": {}})
    previous = worker.photo.name if worker.photo else ""
    worker.photo.save(processed.name, processed, save=False)
    worker.save(update_fields=["photo"])
    if previous:
        worker.photo.storage.delete(previous)
    return JsonResponse({"worker": serialize_worker(workers_queryset().get(pk=pk))}, status=200)
