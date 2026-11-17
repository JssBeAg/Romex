from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3: folio and registering mechanic become required; folios are unique per author."""

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("fleet", "0021_folios_datos"),
    ]

    operations = [
        migrations.AlterField(
            model_name=model,
            name="folio",
            field=models.PositiveIntegerField(db_column="folio", verbose_name="folio"),
        )
        for model in ("faultreport", "faultdiagnosis", "maintenance")
    ] + [
        migrations.AlterField(
            model_name="maintenance",
            name="registered_by",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="registered_maintenances",
                to=settings.AUTH_USER_MODEL,
                db_column="id_usuario_registra",
            ),
        ),
        migrations.AddConstraint(
            model_name="faultreport",
            constraint=models.UniqueConstraint(
                fields=("reported_by", "folio"), name="reporte_folio_unico"
            ),
        ),
        migrations.AddConstraint(
            model_name="faultdiagnosis",
            constraint=models.UniqueConstraint(
                fields=("diagnosed_by", "folio"), name="diagnostico_folio_unico"
            ),
        ),
        migrations.AddConstraint(
            model_name="maintenance",
            constraint=models.UniqueConstraint(
                fields=("registered_by", "folio"), name="mantenimiento_folio_unico"
            ),
        ),
    ]
