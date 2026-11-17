import django.db.models.deletion
from django.db import migrations, models


def crear_gravedades(apps, schema_editor):
    Severity = apps.get_model("fleet", "Severity")
    for name in ("Baja", "Media", "Alta", "Crítica"):
        Severity.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0003_atributos_diagnostico"),
    ]

    operations = [
        migrations.CreateModel(
            name="Severity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_column="nombre", max_length=30, unique=True, verbose_name="nombre")),
            ],
            options={
                "verbose_name": "gravedad",
                "verbose_name_plural": "gravedades",
                "db_table": "gravedades",
            },
        ),
        migrations.RunPython(crear_gravedades, migrations.RunPython.noop),
        # Temporary name: the old text column is still called "severity" until the next steps
        migrations.AddField(
            model_name="faultdiagnosis",
            name="severity_catalog",
            field=models.ForeignKey(
                null=True,
                db_column="id_gravedad",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="diagnoses",
                to="fleet.severity",
                verbose_name="gravedad",
            ),
        ),
    ]
