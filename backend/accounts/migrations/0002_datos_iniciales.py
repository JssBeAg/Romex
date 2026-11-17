from django.db import migrations


def crear_sexos(apps, schema_editor):
    Sex = apps.get_model("accounts", "Sex")
    for name in ("Hombre", "Mujer"):
        Sex.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_inicial"),
    ]

    operations = [
        migrations.RunPython(crear_sexos, migrations.RunPython.noop),
    ]
