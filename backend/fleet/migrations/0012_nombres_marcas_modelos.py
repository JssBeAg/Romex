from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1: add the name columns as optional (existing rows are filled in the next step)."""

    dependencies = [
        ("fleet", "0011_mantenimiento_unidad"),
    ]

    operations = [
        migrations.AddField(
            model_name="brand",
            name="name",
            field=models.CharField(max_length=100, null=True, db_column="nombre"),
        ),
        migrations.AddField(
            model_name="unitmodel",
            name="name",
            field=models.CharField(max_length=100, null=True, db_column="nombre"),
        ),
    ]
