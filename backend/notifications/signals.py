"""
Events of the system that create notifications. Listening to saves keeps the API views free
of notification code (the same idea as the audit trail).
"""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from fleet.inventory import is_low, stock_of
from fleet.models import (
    FaultReport,
    InventoryMovement,
    MaintenanceSparePart,
    ReportMechanic,
    ReportStatusChange,
    SparePart,
)
from fleet.report_status import CLOSED_STATUSES

from .models import Notification
from .service import notify, notify_managers


@receiver(post_save, sender=FaultReport)
def report_created(sender, instance, created, raw=False, **kwargs):
    if created and not raw:
        notify_managers(
            Notification.REPORT_NEW,
            f"Nuevo reporte de falla en la unidad {instance.unit.economic_number}: {instance.description[:80]}",
            link=f"/reportes/{instance.pk}",
        )


@receiver(post_save, sender=ReportMechanic)
def mechanic_assigned(sender, instance, created, raw=False, **kwargs):
    if created and not raw and instance.end_date is None:
        report = instance.fault_report
        notify(
            [instance.mechanic],
            Notification.REPORT_ASSIGNED,
            f"Se te asignó el reporte de la unidad {report.unit.economic_number}: {report.description[:80]}",
            link=f"/reportes/{report.pk}",
        )


@receiver(post_save, sender=ReportStatusChange)
def status_changed(sender, instance, created, raw=False, **kwargs):
    if not created or raw:
        return
    report = instance.fault_report
    status = instance.status.name
    # The operator who reported follows what happens to their report
    notify(
        [report.reported_by],
        Notification.REPORT_STATUS,
        f"Tu reporte de la unidad {report.unit.economic_number} ahora está: {status}.",
        link=f"/reportes/{report.pk}",
    )
    if status in CLOSED_STATUSES:
        notify_managers(
            Notification.REPORT_STATUS,
            f"Reporte cerrado ({status}) en la unidad {report.unit.economic_number}.",
            link=f"/reportes/{report.pk}",
        )


def _check_low_stock(part_id):
    part = SparePart.objects.filter(pk=part_id, is_active=True).first()
    if part is None:
        return
    stock = stock_of(part.pk)
    if is_low(stock, part.min_stock):
        notify_managers(
            Notification.LOW_STOCK,
            f"Stock bajo: {part.name} (quedan {stock}, mínimo {part.min_stock}).",
            link=f"/refacciones/{part.pk}",
            key=f"low:{part.pk}",
        )


@receiver(post_save, sender=MaintenanceSparePart)
@receiver(post_save, sender=InventoryMovement)
def stock_moved(sender, instance, raw=False, **kwargs):
    if not raw:
        # After the transaction, so the stock is the final one (a maintenance rewrites its pieces)
        transaction.on_commit(lambda: _check_low_stock(instance.spare_part_id))
