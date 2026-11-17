from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1: add the economic number as optional (existing units are filled in the next step)."""

    dependencies = [
        ("fleet", "0016_orden_y_etiquetas"),
    ]

    operations = [
        migrations.AddField(
            model_name="unit",
            name="economic_number",
            field=models.CharField(max_length=20, null=True, db_column="numero_economico"),
        ),
    ]
