from django.db import migrations


class Migration(migrations.Migration):
    """Step 4 of 4: the country, state and city tables go away (INEGI's service replaces them)."""

    dependencies = [
        ("locations", "0017_domicilio_sin_ciudad"),
        ("fleet", "0045_placa_estado_texto_final"),
    ]

    operations = [
        migrations.DeleteModel(name="City"),
        migrations.DeleteModel(name="State"),
        migrations.DeleteModel(name="Country"),
    ]
