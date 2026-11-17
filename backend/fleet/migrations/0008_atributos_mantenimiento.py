import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    # mantenimientos is empty at this point (migration 0007 checked it)
    dependencies = [
        ("fleet", "0007_tipos_servicio_y_refacciones"),
    ]

    operations = [
        migrations.AddField(
            model_name="maintenance",
            name="service_type",
            field=models.ForeignKey(
                db_column="id_tipo_servicio",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="maintenances",
                to="fleet.servicetype",
                verbose_name="tipo de servicio",
            ),
        ),
        migrations.AddField(
            model_name="maintenance",
            name="service_mileage",
            field=models.PositiveIntegerField(db_column="km_servicio", verbose_name="km de servicio"),
        ),
        migrations.AddField(
            model_name="maintenance",
            name="total_cost",
            field=models.DecimalField(
                db_column="costo_total",
                decimal_places=2,
                max_digits=12,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="costo total",
            ),
        ),
        migrations.AddField(
            model_name="maintenance",
            name="date",
            field=models.DateField(db_column="fecha", verbose_name="fecha"),
        ),
        migrations.AddField(
            model_name="maintenance",
            name="observations",
            field=models.TextField(blank=True, db_column="observaciones", verbose_name="observaciones"),
        ),
    ]
