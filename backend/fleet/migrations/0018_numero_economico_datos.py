from django.db import migrations


def fill_existing_units(apps, schema_editor):
    """Existing units get a provisional economic number ("U-<id>") that can be edited later."""
    Unit = apps.get_model("fleet", "Unit")
    for unit in Unit.objects.filter(economic_number__isnull=True):
        unit.economic_number = f"U-{unit.pk}"
        unit.save(update_fields=["economic_number"])


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0017_numero_economico"),
    ]

    operations = [
        migrations.RunPython(fill_existing_units, migrations.RunPython.noop),
    ]
