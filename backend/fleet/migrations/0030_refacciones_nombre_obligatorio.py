from django.db import migrations, models
from django.db.models.functions import Lower


class Migration(migrations.Migration):
    """Step 3: the name becomes required and unique (ignoring upper/lower case)."""

    dependencies = [
        ("fleet", "0029_refacciones_nombres_datos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sparepart",
            name="name",
            field=models.CharField(max_length=120, db_column="nombre", verbose_name="nombre"),
        ),
        migrations.AlterModelOptions(
            name="sparepart",
            options={"ordering": ["name"], "verbose_name": "refacción", "verbose_name_plural": "refacciones"},
        ),
        migrations.AddConstraint(
            model_name="sparepart",
            constraint=models.UniqueConstraint(Lower("name"), name="refaccion_nombre_unico"),
        ),
    ]
