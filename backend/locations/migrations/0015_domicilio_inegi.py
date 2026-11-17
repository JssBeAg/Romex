from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1 of 4: the address gets the state and the municipality as text (INEGI names)."""

    dependencies = [("locations", "0014_domicilio_texto_final")]

    operations = [
        migrations.AddField(
            model_name="address",
            name="state",
            field=models.CharField(db_column="estado", default="", max_length=100, verbose_name="estado"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="address",
            name="municipality",
            field=models.CharField(db_column="municipio", default="", max_length=100, verbose_name="municipio"),
            preserve_default=False,
        ),
    ]
