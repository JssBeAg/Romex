from django.db import migrations

from ._datos_calles import STREET_POOL


def load_streets(apps, schema_editor):
    """Two streets per neighborhood (sample data), taken from the pool in order."""
    Neighborhood = apps.get_model("locations", "Neighborhood")
    Street = apps.get_model("locations", "Street")
    size = len(STREET_POOL)
    for index, neighborhood in enumerate(Neighborhood.objects.order_by("city_id", "name", "id")):
        for offset in (0, 1):
            Street.objects.get_or_create(
                neighborhood=neighborhood, name=STREET_POOL[(2 * index + offset) % size]
            )


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0009_calles_obligatorio"),
    ]

    operations = [
        migrations.RunPython(load_streets, migrations.RunPython.noop),
    ]
