from django.db import migrations

# Two plans as a starting point; the manager can edit or deactivate them
PLANS = [
    ("Cambio de aceite y filtros", "Aceite de motor, filtro de aceite y filtro de combustible.", 10000, 180),
    ("Revisión de frenos y llantas", "Balatas, tambores, presión y profundidad de llantas.", 20000, 365),
]


def crear_planes(apps, schema_editor):
    Plan = apps.get_model("fleet", "MaintenancePlan")
    for name, description, km, days in PLANS:
        Plan.objects.get_or_create(
            name=name, defaults={"description": description, "every_km": km, "every_days": days}
        )


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0039_planes_preventivos"),
    ]

    operations = [
        migrations.RunPython(crear_planes, migrations.RunPython.noop),
    ]
