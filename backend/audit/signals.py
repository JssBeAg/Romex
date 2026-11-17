"""
Writes the audit trail by listening to every save and delete of the audited models, so the
API views do not have to remember to do it. The line is written inside the same transaction
as the change: if the change is rolled back, so is its line.
"""

import datetime
import decimal

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .context import current_ip, current_user
from .models import AuditLog
from .registry import AUDITED_NAMES, FIELD_LABELS, SECRET_FIELDS, SKIPPED_FIELDS, audited_models

AUDITED = set(audited_models())

SECRET_MARK = "[nueva contraseña]"


def _plain(value):
    """A value as the JSON column can keep it."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    return str(value)


def _field_value(instance, field):
    """What a person would read for this field: the related record's name for a foreign key."""
    raw = field.value_from_object(instance)
    if field.is_relation and raw is not None:
        try:
            return _plain(str(getattr(instance, field.name)))
        except Exception:  # the related row may already be gone
            return _plain(raw)
    if hasattr(raw, "name") and not isinstance(raw, str):  # files: keep the file name
        return raw.name or None
    return _plain(raw)


def _tracked_fields(instance):
    return [
        f
        for f in instance._meta.concrete_fields
        if not f.primary_key and f.name not in SKIPPED_FIELDS
    ]


def _label(field):
    if field.name in FIELD_LABELS:
        return FIELD_LABELS[field.name]
    text = str(field.verbose_name)
    return text[:1].upper() + text[1:]


def _snapshot(instance):
    return {f.attname: _field_value(instance, f) for f in _tracked_fields(instance)}


def _title_function(instance):
    """The function the API uses to name this kind of record, when there is one."""
    name = type(instance).__name__
    if name == "FaultReport":
        from fleet.reports_api import report_title as title
    elif name == "FaultDiagnosis":
        from fleet.diagnoses_api import diagnosis_title as title
    elif name == "Maintenance":
        from fleet.maintenances_api import maintenance_title as title
    elif name == "Checklist":
        from fleet.checklists_api import checklist_title as title
    else:
        return str
    return title


def _describe(instance):
    """How a person recognises the record: its title, or its kind and number."""
    try:
        text = _title_function(instance)(instance)
        if not text.endswith(" object (%s)" % instance.pk) and "object (" not in text:
            return text[:300]
    except Exception:  # a related row may be gone already (cascade deletes)
        pass
    kind = AUDITED_NAMES.get(type(instance)._meta.label, instance._meta.verbose_name)
    return f"{kind} {instance.pk}"


def _who():
    """The fields of the line that say who did it."""
    user = current_user()
    if user is None:
        return {"user": None, "user_enrollment_id": "", "user_name": "Sistema", "user_role": ""}
    name = " ".join(
        part for part in (user.first_name, user.paternal_surname, user.maternal_surname) if part
    )
    return {
        "user": user,
        "user_enrollment_id": user.get_username(),
        "user_name": name,
        "user_role": user.role.name if user.role_id else "",
    }


def _write(instance, action, changes):
    AuditLog.objects.create(
        action=action,
        table_name=instance._meta.db_table,
        record_id=instance.pk,
        record=_describe(instance),
        changes=changes or None,
        ip_address=current_ip(),
        **_who(),
    )


@receiver(pre_save)
def remember_old_values(sender, instance, raw=False, **kwargs):
    """Before an update, keep how the record was, to find out what changed afterwards."""
    if sender not in AUDITED or raw:
        return
    instance._audit_old = None
    if instance.pk is not None and not instance._state.adding:
        old = sender._default_manager.filter(pk=instance.pk).first()
        if old is not None:
            instance._audit_old = _snapshot(old)


@receiver(post_save)
def log_save(sender, instance, created, raw=False, **kwargs):
    if sender not in AUDITED or raw:
        return
    fields = {f.attname: f for f in _tracked_fields(instance)}
    new = _snapshot(instance)
    old = getattr(instance, "_audit_old", None)

    changes = {}
    if created or old is None:
        # Everything that has a value (the rest would only be noise)
        for attname, value in new.items():
            if value not in (None, ""):
                changes[_label(fields[attname])] = [None, value]
        action = AuditLog.CREATE
    else:
        for attname, value in new.items():
            if old.get(attname) != value:
                changes[_label(fields[attname])] = [old.get(attname), value]
        action = AuditLog.UPDATE
        if not changes:
            return  # saved without changing anything

    for attname in SECRET_FIELDS:
        label = _label(fields[attname]) if attname in fields else None
        if label in changes:
            changes[label] = [None, SECRET_MARK] if created or old is None else ["[oculta]", "[modificada]"]
    _write(instance, action, changes)


@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if sender not in AUDITED:
        return
    fields = {f.attname: f for f in _tracked_fields(instance)}
    changes = {
        _label(fields[attname]): [value, None]
        for attname, value in _snapshot(instance).items()
        if value not in (None, "") and attname not in SECRET_FIELDS
    }
    _write(instance, AuditLog.DELETE, changes)


def _session_line(action, user, enrollment_id, record=""):
    name = ""
    role = ""
    if user is not None:
        name = " ".join(p for p in (user.first_name, user.paternal_surname, user.maternal_surname) if p)
        role = user.role.name if user.role_id else ""
    AuditLog.objects.create(
        action=action,
        user=user,
        user_enrollment_id=enrollment_id,
        user_name=name,
        user_role=role,
        record=record,
        ip_address=current_ip(),
    )


def log_account_event(action, user):
    """Lines for account security events (lock, password change) that are not model saves."""
    _session_line(action, user, user.get_username())


def log_export(user, title):
    """A line saying who exported which PDF (the filters are not kept, only the title)."""
    _session_line(AuditLog.EXPORT, user, user.get_username(), record=title[:300])


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    _session_line(AuditLog.LOGIN, user, user.get_username())


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    if user is not None:
        _session_line(AuditLog.LOGOUT, user, user.get_username())


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request=None, **kwargs):
    # Only the typed matrícula is kept; the password is never read
    typed = str(credentials.get("username", ""))[:30]
    _session_line(AuditLog.LOGIN_FAILED, None, typed)
