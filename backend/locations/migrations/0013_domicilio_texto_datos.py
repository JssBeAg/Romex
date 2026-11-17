from django.db import migrations


def copy_to_text(apps, schema_editor):
    """
    Every existing address keeps what it said: its city, and the names of its colonia and
    street (which used to be rows of the colonias and calles tables) become text.
    """
    Address = apps.get_model("locations", "Address")
    batch = []
    for address in Address.objects.select_related("street__neighborhood").iterator(chunk_size=500):
        street = address.street
        address.city_id = street.neighborhood.city_id
        address.neighborhood_text = street.neighborhood.name
        address.street_text = street.name
        batch.append(address)
        if len(batch) >= 500:
            Address.objects.bulk_update(batch, ["city", "neighborhood_text", "street_text"])
            batch = []
    if batch:
        Address.objects.bulk_update(batch, ["city", "neighborhood_text", "street_text"])


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0012_domicilio_texto"),
    ]

    operations = [
        # Not reversible with data: once the tables are gone the rows cannot come back
        migrations.RunPython(copy_to_text, migrations.RunPython.noop),
    ]
