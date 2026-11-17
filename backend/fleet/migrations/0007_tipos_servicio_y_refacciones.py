import django.db.models.deletion
from django.db import migrations, models


def verificar_sin_mantenimientos(apps, schema_editor):
    """The new maintenance attributes are required and cannot be invented for existing rows."""
    Maintenance = apps.get_model("fleet", "Maintenance")
    count = Maintenance.objects.count()
    if count:
        raise RuntimeError(
            f"Hay {count} mantenimiento(s) existentes y los nuevos atributos son obligatorios. "
            "Elimínalos o reinicia la base de datos (docker compose down -v) y vuelve a migrar."
        )


def crear_tipos_servicio(apps, schema_editor):
    ServiceType = apps.get_model("fleet", "ServiceType")
    for name in ("Preventivo", "Correctivo"):
        ServiceType.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0006_gravedad_catalogo"),
    ]

    operations = [
        migrations.RunPython(verificar_sin_mantenimientos, migrations.RunPython.noop),
        migrations.CreateModel(
            name="ServiceType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_column="nombre", max_length=30, unique=True, verbose_name="nombre")),
            ],
            options={
                "verbose_name": "tipo de servicio",
                "verbose_name_plural": "tipos de servicio",
                "db_table": "tipos_servicio",
            },
        ),
        migrations.RunPython(crear_tipos_servicio, migrations.RunPython.noop),
        migrations.CreateModel(
            name="SparePart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "maintenance",
                    models.ForeignKey(
                        db_column="id_mantenimiento",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="spare_parts",
                        to="fleet.maintenance",
                    ),
                ),
            ],
            options={
                "verbose_name": "refacción",
                "verbose_name_plural": "refacciones",
                "db_table": "refacciones",
            },
        ),
    ]
