import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1: the streets table, and a new optional street link on addresses."""

    dependencies = [
        ("locations", "0006_orden_y_etiquetas"),
    ]

    operations = [
        migrations.CreateModel(
            name="Street",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_column="nombre", max_length=150, verbose_name="nombre")),
                (
                    "neighborhood",
                    models.ForeignKey(
                        db_column="id_colonia",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="streets",
                        to="locations.neighborhood",
                        verbose_name="colonia",
                    ),
                ),
            ],
            options={
                "verbose_name": "calle",
                "verbose_name_plural": "calles",
                "db_table": "calles",
                "ordering": ["name"],
            },
        ),
        migrations.AddConstraint(
            model_name="street",
            constraint=models.UniqueConstraint(
                fields=("neighborhood", "name"), name="calle_nombre_unico"
            ),
        ),
        migrations.AddField(
            model_name="address",
            name="street_link",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="addresses",
                to="locations.street",
                db_column="id_calle",
            ),
        ),
    ]
