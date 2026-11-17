from django.db import migrations


def link_existing_addresses(apps, schema_editor):
    """Addresses that stored the street as text get a street row (same name) in their neighborhood."""
    Address = apps.get_model("locations", "Address")
    Street = apps.get_model("locations", "Street")
    for address in Address.objects.filter(street_link__isnull=True):
        street, _ = Street.objects.get_or_create(
            neighborhood_id=address.neighborhood_id, name=address.street
        )
        address.street_link_id = street.pk
        address.save(update_fields=["street_link"])


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0007_calles"),
    ]

    operations = [
        migrations.RunPython(link_existing_addresses, migrations.RunPython.noop),
    ]
