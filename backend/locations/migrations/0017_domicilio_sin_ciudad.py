from django.db import migrations


class Migration(migrations.Migration):
    """Step 3 of 4: the address no longer points to a city."""

    dependencies = [("locations", "0016_domicilio_inegi_datos")]

    operations = [migrations.RemoveField(model_name="address", name="city")]
