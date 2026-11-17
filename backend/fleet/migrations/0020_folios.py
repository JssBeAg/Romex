from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1: add folio and registering mechanic as optional (filled in the next step)."""

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("fleet", "0019_numero_economico_obligatorio"),
    ]

    operations = [
        migrations.AddField(
            model_name=model,
            name="folio",
            field=models.PositiveIntegerField(null=True, db_column="folio"),
        )
        for model in ("faultreport", "faultdiagnosis", "maintenance")
    ] + [
        migrations.AddField(
            model_name="maintenance",
            name="registered_by",
            field=models.ForeignKey(
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="registered_maintenances",
                to=settings.AUTH_USER_MODEL,
                db_column="id_usuario_registra",
            ),
        ),
    ]
