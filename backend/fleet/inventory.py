"""
Stock of the spare parts. It is never stored: it is worked out each time from

    stock = pieces that came in (entries and adjustments) - pieces used in maintenances

so it cannot get out of step with the maintenances (editing or deleting one gives its pieces
back). Use with_stock() to get the stock of many parts in one query.
"""

from django.db.models import F, IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce

from .models import InventoryMovement, MaintenanceSparePart, SparePart


def _sum_subquery(model, field, **extra):
    return Coalesce(
        Subquery(
            model.objects.filter(spare_part=OuterRef("pk"), **extra)
            .order_by()
            .values("spare_part")
            .annotate(total=Sum(field))
            .values("total"),
            output_field=IntegerField(),
        ),
        Value(0),
    )


def with_stock(queryset=None):
    """Parts with `received`, `used` and `stock` (received - used) as attributes."""
    queryset = SparePart.objects.all() if queryset is None else queryset
    return queryset.annotate(
        received=_sum_subquery(InventoryMovement, "quantity"),
        used=_sum_subquery(MaintenanceSparePart, "quantity"),
    ).annotate(stock=F("received") - F("used"))


def stock_of(part_id, exclude_maintenance=None):
    """
    Pieces in stock of one part. `exclude_maintenance` leaves out what that maintenance used
    (when it is edited, its own pieces count as available again).
    """
    received = (
        InventoryMovement.objects.filter(spare_part_id=part_id).aggregate(t=Sum("quantity"))["t"] or 0
    )
    used = MaintenanceSparePart.objects.filter(spare_part_id=part_id)
    if exclude_maintenance is not None:
        used = used.exclude(maintenance=exclude_maintenance)
    return received - (used.aggregate(t=Sum("quantity"))["t"] or 0)


def is_low(stock, min_stock):
    """Low stock: it reached the minimum. A minimum of 0 means "do not warn me"."""
    return min_stock > 0 and stock <= min_stock
