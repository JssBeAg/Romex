from django.db import migrations

TEXT_TO_NAME = {"baja": "Baja", "media": "Media", "alta": "Alta", "critica": "Crítica"}


def migrar_gravedad(apps, schema_editor):
    """Existing diagnoses keep their severity: the old text value points to the catalog row."""
    FaultDiagnosis = apps.get_model("fleet", "FaultDiagnosis")
    Severity = apps.get_model("fleet", "Severity")
    for text, name in TEXT_TO_NAME.items():
        FaultDiagnosis.objects.filter(severity=text).update(
            severity_catalog=Severity.objects.get(name=name)
        )


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0004_gravedades"),
    ]

    operations = [
        migrations.RunPython(migrar_gravedad, migrations.RunPython.noop),
    ]
