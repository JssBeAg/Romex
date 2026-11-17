from django.db import migrations


def copy_names(apps, schema_editor):
    """Each address keeps the names of the state and the city it pointed to."""
    Address = apps.get_model("locations", "Address")
    for address in Address.objects.select_related("city__state"):
        address.state = address.city.state.name
        address.municipality = address.city.name
        address.save(update_fields=["state", "municipality"])


class Migration(migrations.Migration):
    """Step 2 of 4: copy the names. It cannot be undone (the catalogs are dropped later)."""

    dependencies = [("locations", "0015_domicilio_inegi")]

    operations = [migrations.RunPython(copy_names, migrations.RunPython.noop)]
