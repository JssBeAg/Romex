import django.db.models.deletion
from django.db import migrations, models


def copiar_vinculos(apps, schema_editor):
    """Each existing part was tied to one maintenance: keep that link in the new table."""
    SparePart = apps.get_model("fleet", "SparePart")
    Link = apps.get_model("fleet", "MaintenanceSparePart")
    Link.objects.bulk_create(
        [Link(maintenance_id=part.maintenance_id, spare_part_id=part.pk) for part in SparePart.objects.all()]
    )


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0008_atributos_mantenimiento"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaintenanceSparePart",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "maintenance",
                    models.ForeignKey(
                        db_column="id_mantenimiento",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="+",
                        to="fleet.maintenance",
                    ),
                ),
                (
                    "spare_part",
                    models.ForeignKey(
                        db_column="id_refaccion",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="fleet.sparepart",
                    ),
                ),
            ],
            options={"db_table": "mantenimientos_refacciones"},
        ),
        migrations.AddConstraint(
            model_name="maintenancesparepart",
            constraint=models.UniqueConstraint(
                fields=("maintenance", "spare_part"), name="mantenimiento_refaccion_unico"
            ),
        ),
        migrations.RunPython(copiar_vinculos, migrations.RunPython.noop),
    ]
