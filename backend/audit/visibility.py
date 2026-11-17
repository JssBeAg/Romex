"""
What a manager may see in the audit trail.

The trail records everything (the administrator sees all of it in the admin panel). A manager
sees the activity of the operation, but not the private activity of the administrators, who
are above the manager and are not even listed in the workers screen:

  hidden from the manager
    - sessions and account events of administrators: logins, logouts, failed logins that typed
      an administrator's matrícula, locks, password changes and PDF exports;
    - changes to the administrator accounts themselves;
    - tables only the administrator maintains (the catalog of phone codes).
  still shown
    - the data changes an administrator makes on the operation (units, reports, parts...):
      they alter data the manager answers for, so they must not appear out of nowhere.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q

from accounts.roles import ADMIN_ROLE

from .models import AuditLog

# Lines that are about a person's session or account, not about a record
SESSION_ACTIONS = [
    AuditLog.LOGIN,
    AuditLog.LOGOUT,
    AuditLog.LOGIN_FAILED,
    AuditLog.ACCOUNT_LOCKED,
    AuditLog.PASSWORD_CHANGED,
    AuditLog.EXPORT,
]

# Tables only the administrator maintains
ADMIN_ONLY_TABLES = ["codigos_telefonicos"]


def administrators():
    """The administrator accounts: superusers and anybody with the administrator role."""
    return get_user_model().objects.filter(Q(is_superuser=True) | Q(role__name=ADMIN_ROLE))


def is_administrator(user):
    return bool(user.is_superuser or (user.role_id and user.role.name == ADMIN_ROLE))


def visible_to_manager(queryset):
    """The lines of `queryset` a manager may see (see the module description)."""
    admins = list(administrators().values_list("pk", "enrollment_id"))
    ids = [pk for pk, _ in admins]
    enrollment_ids = [enrollment_id for _, enrollment_id in admins]
    # Who did it: the account itself, anybody who was an administrator at that moment, or a
    # failed login that typed an administrator's matrícula (no account is attached to those)
    by_administrator = (
        Q(user_id__in=ids) | Q(user_role=ADMIN_ROLE) | Q(user_enrollment_id__in=enrollment_ids)
    )
    return (
        queryset.exclude(Q(action__in=SESSION_ACTIONS) & by_administrator)
        .exclude(table_name__in=ADMIN_ONLY_TABLES)
        .exclude(Q(table_name="usuarios") & Q(record_id__in=ids))
    )
