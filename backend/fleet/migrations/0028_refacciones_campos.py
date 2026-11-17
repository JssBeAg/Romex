import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1: new columns. The name is nullable for now so existing rows can be filled."""

    dependencies = [
        ("fleet", "0027_mantenimiento_reparacion_terminada"),
    ]

    operations = [
        migrations.AddField(
            model_name="sparepart",
            name="name",
            field=models.CharField(null=True, max_length=120, db_column="nombre", verbose_name="nombre"),
        ),
        migrations.AddField(
            model_name="sparepart",
            name="description",
            field=models.TextField(blank=True, default="", db_column="descripcion", verbose_name="descripción"),
            # The default only fills existing rows; the model itself has none
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="sparepart",
            name="unit_price",
            field=models.DecimalField(
                null=True,
                blank=True,
                max_digits=12,
                decimal_places=2,
                validators=[django.core.validators.MinValueValidator(0)],
                db_column="precio_unitario",
                verbose_name="precio unitario",
            ),
        ),
    ]
