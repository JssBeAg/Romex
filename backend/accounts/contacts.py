"""
Phones with an international code and the alternative contacts of a worker.

- The principal phone is `User.phone_code` + `User.phone_number` (digits only).
- Alternative ways to reach the SAME worker are rows of `WorkerContact`, at most
  MAX_CONTACTS per worker: phones (code + number) or emails, with a label such as
  "Número 2" and, optionally, the name of the person they belong to.
- The API sends the list as a whole: `contacts` absent means "leave them as they are";
  present, it replaces the stored list (rows with an `id` are updated, the rest are
  created and the ones that are missing are deleted).
"""
import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .models import MAX_CONTACTS, PhoneCode, WorkerContact, phone_validator

# ITU E.164: country code + national number is at most 15 digits
MAX_PHONE_DIGITS = 15
LABEL_MAX = 40
NAME_MAX = 150


def clean_number(raw):
    """What the person typed without the usual separators: "844 123-4567" -> "8441234567"."""
    return re.sub(r"[\s().-]", "", str(raw or "")).strip()


def get_code(value):
    try:
        return PhoneCode.objects.filter(pk=int(value)).first()
    except (TypeError, ValueError):
        return None


def check_phone(code_id, raw_number, allowed_inactive=()):
    """
    Validate a phone given as code id + number. Returns (code, number, messages) where
    messages is a dict {"code": [...], "number": [...]}. An inactive code is only accepted
    when it is already in use by this worker (`allowed_inactive` holds those ids).
    """
    messages = {"code": [], "number": []}
    code = get_code(code_id)
    if code is None or (not code.is_active and code.pk not in allowed_inactive):
        code = None
        messages["code"].append("Elige una opción válida.")
    number = clean_number(raw_number)
    if not number:
        messages["number"].append("Este campo es obligatorio.")
    else:
        try:
            phone_validator(number)
        except ValidationError as exc:
            messages["number"].extend(exc.messages)
        else:
            if code is not None and len(code.code) + len(number) > MAX_PHONE_DIGITS:
                messages["number"].append(
                    f"Con el código del país, el teléfono no puede pasar de {MAX_PHONE_DIGITS} dígitos."
                )
    return code, number, messages


def contact_key(kind, code_id, value):
    """Identity of a contact, to detect repeated ones."""
    if kind == WorkerContact.EMAIL:
        return (kind, None, value.lower())
    return (kind, code_id, value)


def default_label(kind, position):
    """Principal phone/email is number 1, so the first extra one is "Número 2"."""
    return f"{'Número' if kind == WorkerContact.PHONE else 'Correo'} {position + 2}"


def validate_contacts(data, worker, principal):
    """
    Validate the `contacts` list of a payload.

    `principal` is {"code": PhoneCode|None, "number": str, "email": str}, to reject a
    contact that repeats the principal ones. Returns (messages, items): `items` is None
    when the payload has no `contacts` (nothing to change); `messages` is a list of texts.
    """
    if "contacts" not in data:
        return [], None
    raw_items = data["contacts"]
    if not isinstance(raw_items, list):
        return ["Los contactos no tienen un formato válido."], None
    messages = []
    if len(raw_items) > MAX_CONTACTS:
        messages.append(f"Solo se permiten {MAX_CONTACTS} contactos adicionales.")
        raw_items = raw_items[:MAX_CONTACTS]

    own = {}
    in_use = set()
    if worker is not None:
        own = {c.pk: c for c in worker.contacts.all()}
        in_use = {c.phone_code_id for c in own.values() if c.phone_code_id}
        if worker.phone_code_id:
            in_use.add(worker.phone_code_id)

    seen = {}
    if principal.get("code") is not None and principal.get("number"):
        seen[contact_key(WorkerContact.PHONE, principal["code"].pk, principal["number"])] = (
            "el teléfono principal"
        )
    if principal.get("email"):
        seen[contact_key(WorkerContact.EMAIL, None, principal["email"])] = "el correo principal"

    items = []
    counters = {WorkerContact.PHONE: 0, WorkerContact.EMAIL: 0}
    for position, raw in enumerate(raw_items):
        row_name = f"Contacto {position + 1}"
        if not isinstance(raw, dict):
            messages.append(f"{row_name}: formato no válido.")
            continue
        kind = raw.get("kind")
        if kind not in (WorkerContact.PHONE, WorkerContact.EMAIL):
            messages.append(f"{row_name}: elige si es un teléfono o un correo.")
            continue
        label = str(raw.get("label") or "").strip()
        contact_name = str(raw.get("contact_name") or "").strip()
        if not label:
            label = default_label(kind, counters[kind])
        counters[kind] += 1
        row_name = label
        problems = []
        if len(label) > LABEL_MAX:
            problems.append(f"la etiqueta no puede pasar de {LABEL_MAX} caracteres")
        if len(contact_name) > NAME_MAX:
            problems.append(f"el nombre no puede pasar de {NAME_MAX} caracteres")

        existing = None
        if raw.get("id") not in (None, ""):
            try:
                existing = own.get(int(raw["id"]))
            except (TypeError, ValueError):
                existing = None
            if existing is None:
                problems.append("el contacto ya no existe, recarga la página")

        code = None
        if kind == WorkerContact.PHONE:
            code, value, found = check_phone(raw.get("phone_code_id"), raw.get("value"), in_use)
            problems += [m.rstrip(".")[:1].lower() + m.rstrip(".")[1:] for m in found["code"] + found["number"]]
        else:
            value = str(raw.get("value") or "").strip()
            if not value:
                problems.append("escribe el correo")
            else:
                try:
                    validate_email(value)
                except ValidationError:
                    problems.append("el correo no es válido")
                if len(value) > 254:
                    problems.append("el correo es demasiado largo")

        if problems:
            messages.append(f"{row_name}: " + "; ".join(problems) + ".")
            continue
        key = contact_key(kind, code.pk if code else None, value)
        if key in seen:
            messages.append(f"{row_name}: repite {seen[key]}.")
            continue
        seen[key] = row_name
        items.append(
            {
                "id": existing.pk if existing else None,
                "kind": kind,
                "phone_code": code,
                "value": value.lower() if kind == WorkerContact.EMAIL else value,
                "label": label,
                "contact_name": contact_name,
            }
        )
    return messages, items


def sync_contacts(worker, items):
    """
    Make the stored contacts equal to `items` (already validated). Call it inside a
    transaction: it locks the worker row so two edits at once cannot go over the limit.
    """
    from .models import User

    User.objects.select_for_update().filter(pk=worker.pk).first()
    existing = {c.pk: c for c in WorkerContact.objects.filter(user=worker)}
    kept = set()
    for order, item in enumerate(items):
        contact = existing.get(item["id"]) if item["id"] else None
        if contact is None:
            contact = WorkerContact(user=worker)
        values = {
            "kind": item["kind"],
            "phone_code": item["phone_code"],
            "value": item["value"],
            "label": item["label"],
            "contact_name": item["contact_name"],
            "order": order,
        }
        changed = contact.pk is None or any(getattr(contact, k) != v for k, v in values.items())
        for key, value in values.items():
            setattr(contact, key, value)
        if changed:
            contact.save()
        kept.add(contact.pk)
    for pk, contact in existing.items():
        if pk not in kept:
            contact.delete()
    if WorkerContact.objects.filter(user=worker).count() > MAX_CONTACTS:
        raise ValueError("Too many contacts")  # cannot happen after validate_contacts


def serialize_contact(contact):
    return {
        "id": contact.pk,
        "kind": contact.kind,
        "phone_code_id": contact.phone_code_id,
        "phone_code": serialize_code(contact.phone_code) if contact.phone_code else None,
        "value": contact.value,
        "display": contact.display,
        "label": contact.label,
        "contact_name": contact.contact_name,
    }


def serialize_code(code):
    return {"id": code.pk, "iso": code.iso, "code": code.code, "label": f"{code.country_name} (+{code.code})"}
