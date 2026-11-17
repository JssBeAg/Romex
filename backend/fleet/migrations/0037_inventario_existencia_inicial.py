import datetime

from django.db import migrations
from django.db.models import Sum


def existencia_inicial(apps, schema_editor):
    """
    The maintenances that already exist used parts before there was any stock. So the stock does
    not start below zero, each part gets one entry for the pieces already used (stock 0 now).
    """
    Part = apps.get_model("fleet", "SparePart")
    Usage = apps.get_model("fleet", "MaintenanceSparePart")
    Movement = apps.get_model("fleet", "InventoryMovement")
    for part in Part.objects.all():
        used = Usage.objects.filter(spare_part=part).aggregate(t=Sum("quantity"))["t"] or 0
        if used > 0:
            Movement.objects.create(
                spare_part=part,
                movement_type="entrada",
                quantity=used,
                date=datetime.date.today(),
                note="Existencia inicial: piezas ya usadas en mantenimientos anteriores",
            )


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0036_inventario"),
    ]

    operations = [
        migrations.RunPython(existencia_inicial, migrations.RunPython.noop),
    ]
