from django.db import migrations


def crear_estatus(apps, schema_editor):
    FaultReportStatus = apps.get_model("fleet", "FaultReportStatus")
    for name in ("Pendiente", "En mantenimiento", "Reparado"):
        FaultReportStatus.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0001_inicial"),
    ]

    operations = [
        migrations.RunPython(crear_estatus, migrations.RunPython.noop),
    ]
