from django.db import migrations


def fill_existing_rows(apps, schema_editor):
    """
    Rows that already exist have no name: give them the label they used to show ("País 1"...).
    Each address takes the neighborhood of its old street, and the street becomes text.
    """
    for model_name, label in (
        ("Country", "País"),
        ("State", "Estado"),
        ("City", "Ciudad"),
        ("Neighborhood", "Colonia"),
    ):
        Model = apps.get_model("locations", model_name)
        for row in Model.objects.filter(name__isnull=True):
            row.name = f"{label} {row.pk}"
            row.save(update_fields=["name"])

    Address = apps.get_model("locations", "Address")
    for address in Address.objects.select_related("street").all():
        address.neighborhood_id = address.street.neighborhood_id
        address.street_name = f"Calle {address.street_id}"
        address.save(update_fields=["neighborhood", "street_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0002_nombres"),
    ]

    operations = [
        migrations.RunPython(fill_existing_rows, migrations.RunPython.noop),
    ]
