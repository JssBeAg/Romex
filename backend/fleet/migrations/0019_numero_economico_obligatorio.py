from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3: the economic number becomes required and unique."""

    dependencies = [
        ("fleet", "0018_numero_economico_datos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="unit",
            name="economic_number",
            field=models.CharField(
                max_length=20, db_column="numero_economico", verbose_name="número económico"
            ),
        ),
        migrations.AddConstraint(
            model_name="unit",
            constraint=models.UniqueConstraint(
                fields=("economic_number",), name="unidad_numero_economico_unico"
            ),
        ),
    ]
