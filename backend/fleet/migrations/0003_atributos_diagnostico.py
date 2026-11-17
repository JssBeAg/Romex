from django.db import migrations, models


def verificar_sin_diagnosticos(apps, schema_editor):
    """The new attributes are required and cannot be invented for existing diagnoses."""
    FaultDiagnosis = apps.get_model("fleet", "FaultDiagnosis")
    count = FaultDiagnosis.objects.count()
    if count:
        raise RuntimeError(
            f"Hay {count} diagnóstico(s) existentes y los nuevos atributos son obligatorios. "
            "Elimínalos o reinicia la base de datos (docker compose down -v) y vuelve a migrar."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0002_datos_iniciales"),
    ]

    operations = [
        migrations.RunPython(verificar_sin_diagnosticos, migrations.RunPython.noop),
        migrations.AddField(
            model_name="faultdiagnosis",
            name="date",
            field=models.DateField(db_column="fecha", verbose_name="fecha"),
        ),
        migrations.AddField(
            model_name="faultdiagnosis",
            name="detailed_cause",
            field=models.TextField(db_column="causa_detallada", verbose_name="causa detallada"),
        ),
        migrations.AddField(
            model_name="faultdiagnosis",
            name="requires_repair",
            field=models.BooleanField(db_column="requiere_reparacion", verbose_name="requiere reparación"),
        ),
        migrations.AddField(
            model_name="faultdiagnosis",
            name="unit_operable",
            field=models.BooleanField(db_column="unidad_operable", verbose_name="unidad operable"),
        ),
        migrations.AddField(
            model_name="faultdiagnosis",
            name="severity",
            field=models.CharField(
                choices=[("baja", "Baja"), ("media", "Media"), ("alta", "Alta"), ("critica", "Crítica")],
                db_column="gravedad",
                max_length=10,
                verbose_name="gravedad",
            ),
        ),
        migrations.AddConstraint(
            model_name="faultdiagnosis",
            constraint=models.CheckConstraint(
                condition=models.Q(("severity__in", ["baja", "media", "alta", "critica"])),
                name="gravedad_valida",
            ),
        ),
    ]
