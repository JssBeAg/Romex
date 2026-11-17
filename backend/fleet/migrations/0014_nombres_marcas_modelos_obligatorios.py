from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3: names become required and unique."""

    dependencies = [
        ("fleet", "0013_nombres_marcas_modelos_datos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="brand",
            name="name",
            field=models.CharField(
                max_length=100, unique=True, db_column="nombre", verbose_name="nombre"
            ),
        ),
        migrations.AlterField(
            model_name="unitmodel",
            name="name",
            field=models.CharField(max_length=100, db_column="nombre", verbose_name="nombre"),
        ),
        migrations.AddConstraint(
            model_name="unitmodel",
            constraint=models.UniqueConstraint(
                fields=("brand", "name"), name="modelo_nombre_unico"
            ),
        ),
    ]
