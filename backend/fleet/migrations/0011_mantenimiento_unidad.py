import django.db.models.deletion
from django.db import migrations, models


def verificar_sin_mantenimientos(apps, schema_editor):
    """The unit is required and cannot be guessed for existing maintenances."""
    Maintenance = apps.get_model("fleet", "Maintenance")
    count = Maintenance.objects.count()
    if count:
        raise RuntimeError(
            f"Hay {count} mantenimiento(s) existentes y ahora deben tener unidad. "
            "Elimínalos o reinicia la base de datos (docker compose down -v) y vuelve a migrar."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0010_refacciones_catalogo"),
    ]

    operations = [
        migrations.RunPython(verificar_sin_mantenimientos, migrations.RunPython.noop),
        migrations.AddField(
            model_name="maintenance",
            name="unit",
            field=models.ForeignKey(
                db_column="id_unidad",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="maintenances",
                to="fleet.unit",
            ),
        ),
    ]
