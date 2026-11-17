"""
Account security rules: lock after repeated failed logins, password change.

Counters are written with queryset.update() so they do not fire the audit signals (a failed
login would otherwise fill the trail with "user modified" lines); the events that matter
(lock, password change) are written explicitly.
"""

import datetime

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from audit.models import AuditLog
from audit.signals import log_account_event

from .models import User

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 15


def minutes_left(user):
    """Whole minutes until the lock ends (at least 1)."""
    seconds = (user.locked_until - timezone.now()).total_seconds()
    return max(1, int(seconds // 60) + (1 if seconds % 60 else 0))


def register_failed_login(enrollment_id):
    """Counts a failed login of an existing active user and locks the account at the limit."""
    user = User.objects.filter(enrollment_id=enrollment_id, is_active=True).first()
    if user is None:
        return
    attempts = user.failed_attempts + 1
    if attempts >= MAX_FAILED_ATTEMPTS:
        until = timezone.now() + datetime.timedelta(minutes=LOCK_MINUTES)
        User.objects.filter(pk=user.pk).update(failed_attempts=0, locked_until=until)
        log_account_event(AuditLog.ACCOUNT_LOCKED, user)
        from audit.visibility import is_administrator
        from notifications.models import Notification
        from notifications.service import notify_managers

        if is_administrator(user):
            return  # managers do not manage administrator accounts, so they are not told
        notify_managers(
            Notification.ACCOUNT_LOCKED,
            f"Cuenta bloqueada por intentos fallidos: {user.get_full_name()} ({user.get_username()}).",
            link="/trabajadores",
            key=f"lock:{user.pk}",
        )
    else:
        User.objects.filter(pk=user.pk).update(failed_attempts=attempts)


def clear_failed_logins(user):
    if user.failed_attempts or user.locked_until:
        User.objects.filter(pk=user.pk).update(failed_attempts=0, locked_until=None)


def validate_new_password(user, current, new, confirm):
    """Field errors for a password change (empty when it is valid)."""
    errors = {}
    if not current:
        errors["current_password"] = ["Este campo es obligatorio."]
    elif not user.check_password(current):
        errors["current_password"] = ["La contraseña actual no es correcta."]
    if not new:
        errors["new_password"] = ["Este campo es obligatorio."]
    else:
        problems = []
        if user.check_password(new):
            problems.append("La contraseña nueva debe ser distinta de la actual.")
        if new == user.get_username():
            problems.append("La contraseña no puede ser igual a tu matrícula.")
        try:
            validate_password(new, user)
        except ValidationError as exc:
            problems.extend(exc.messages)
        if problems:
            errors["new_password"] = problems
    if new and confirm != new:
        errors["confirm_password"] = ["La confirmación no coincide con la contraseña nueva."]
    elif not confirm:
        errors["confirm_password"] = ["Este campo es obligatorio."]
    return errors


def change_password(user, new):
    user.set_password(new)
    user.must_change_password = False
    user.password_changed_at = timezone.now()
    user.save()
    log_account_event(AuditLog.PASSWORD_CHANGED, user)
