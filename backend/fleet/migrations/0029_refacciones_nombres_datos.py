from django.db import migrations


def fill_names(apps, schema_editor):
    """Parts that already existed (they had no data) get a placeholder name from their id."""
    SparePart = apps.get_model("fleet", "SparePart")
    for part in SparePart.objects.filter(name__isnull=True):
        part.name = f"Refacción {part.pk}"
        part.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0028_refacciones_campos"),
    ]

    operations = [
        migrations.RunPython(fill_names, migrations.RunPython.noop),
    ]
