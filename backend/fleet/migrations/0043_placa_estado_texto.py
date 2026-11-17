from django.db import migrations, models


class Migration(migrations.Migration):
    """Plates keep the name of the issuing state as text. Step 1 of 3: a temporary column."""

    dependencies = [
        ("fleet", "0042_foto_refaccion"),
        ("locations", "0017_domicilio_sin_ciudad"),
    ]

    operations = [
        migrations.AddField(
            model_name="licenseplate",
            name="state_name",
            field=models.CharField(db_column="estado_nombre", default="", max_length=100),
            preserve_default=False,
        ),
    ]
