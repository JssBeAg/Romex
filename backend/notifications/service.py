"""
Creating notifications. The rest of the system only calls notify() / notify_managers().

Two ways to avoid repeating a notification (both use `key`):
  once=False  (default) it is not repeated while the person has not read the previous one
  once=True   it is sent a single time ever for that key
"""

from audit.context import current_user
from accounts.models import User
from accounts.roles import MANAGER_ROLE

from .models import Notification


def managers():
    return User.objects.filter(is_active=True, role__name=MANAGER_ROLE)


def notify(users, kind, message, link="", key="", once=False, skip_actor=True):
    """Sends the notification to each user (the person who caused it is left out by default)."""
    actor = current_user() if skip_actor else None
    created = []
    for user in users:
        if actor is not None and user.pk == actor.pk:
            continue
        if key:
            same = Notification.objects.filter(user=user, kind=kind, key=key)
            if not once:
                same = same.filter(is_read=False)
            if same.exists():
                continue
        created.append(
            Notification(user=user, kind=kind, message=message[:300], link=link, key=key)
        )
    Notification.objects.bulk_create(created)
    return len(created)


def notify_managers(kind, message, link="", key="", once=False):
    return notify(managers(), kind, message, link, key, once)


def sync_preventive(managers_only_for=None):
    """
    Turns the preventive maintenance that is overdue or about to be into notifications for the
    managers. It is derived data, so it is checked when the bell is opened or polled; each
    (plan, unit, last service, status) is notified once.
    """
    from fleet.preventive import OVERDUE, UPCOMING, due_rows

    for row in due_rows():
        if row["status"] not in (OVERDUE, UPCOMING):
            continue
        last = row["last"]["id"] if row["last"] else 0
        overdue = row["status"] == OVERDUE
        notify(
            managers(),
            Notification.PREVENTIVE,
            f"{'Preventivo vencido' if overdue else 'Preventivo próximo'}: "
            f"{row['plan']['name']} en la unidad {row['unit']['label']}. {row['message']}",
            link="/preventivo",
            key=f"prev:{row['plan']['id']}:{row['unit']['id']}:{last}:{row['status']}",
            once=True,
            skip_actor=False,
        )
