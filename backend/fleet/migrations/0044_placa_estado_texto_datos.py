from django.db import migrations


def copy_names(apps, schema_editor):
    LicensePlate = apps.get_model("fleet", "LicensePlate")
    for plate in LicensePlate.objects.select_related("state"):
        plate.state_name = plate.state.name
        plate.save(update_fields=["state_name"])


class Migration(migrations.Migration):
    """Step 2 of 3: copy the state names. It cannot be undone."""

    dependencies = [("fleet", "0043_placa_estado_texto")]

    operations = [migrations.RunPython(copy_names, migrations.RunPython.noop)]
