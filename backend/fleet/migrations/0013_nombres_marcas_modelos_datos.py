from django.db import migrations


def fill_existing_rows(apps, schema_editor):
    """Existing brands and models have no name: give them the label they used to show."""
    for model_name, label in (("Brand", "Marca"), ("UnitModel", "Modelo")):
        Model = apps.get_model("fleet", model_name)
        for row in Model.objects.filter(name__isnull=True):
            row.name = f"{label} {row.pk}"
            row.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0012_nombres_marcas_modelos"),
    ]

    operations = [
        migrations.RunPython(fill_existing_rows, migrations.RunPython.noop),
    ]
