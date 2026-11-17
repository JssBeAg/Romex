import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3: names and neighborhood become required, the streets table disappears."""

    dependencies = [
        ("locations", "0003_nombres_datos"),
    ]

    operations = [
        migrations.RemoveField(model_name="address", name="street"),
        migrations.RenameField(model_name="address", old_name="street_name", new_name="street"),
        migrations.DeleteModel(name="Street"),
        migrations.AlterField(
            model_name="address",
            name="street",
            field=models.CharField(max_length=150, db_column="calle", verbose_name="calle"),
        ),
        migrations.AlterField(
            model_name="address",
            name="neighborhood",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="addresses",
                to="locations.neighborhood",
                db_column="id_colonia",
                verbose_name="colonia",
            ),
        ),
        migrations.AlterField(
            model_name="country",
            name="name",
            field=models.CharField(
                max_length=100, unique=True, db_column="nombre", verbose_name="nombre"
            ),
        ),
        migrations.AlterField(
            model_name="state",
            name="name",
            field=models.CharField(max_length=100, db_column="nombre", verbose_name="nombre"),
        ),
        migrations.AlterField(
            model_name="city",
            name="name",
            field=models.CharField(max_length=100, db_column="nombre", verbose_name="nombre"),
        ),
        migrations.AlterField(
            model_name="neighborhood",
            name="name",
            field=models.CharField(max_length=150, db_column="nombre", verbose_name="nombre"),
        ),
        migrations.AddConstraint(
            model_name="state",
            constraint=models.UniqueConstraint(
                fields=("country", "name"), name="estado_nombre_unico"
            ),
        ),
        migrations.AddConstraint(
            model_name="city",
            constraint=models.UniqueConstraint(
                fields=("state", "name"), name="ciudad_nombre_unico"
            ),
        ),
        migrations.AddConstraint(
            model_name="neighborhood",
            constraint=models.UniqueConstraint(
                fields=("city", "name"), name="colonia_nombre_unico"
            ),
        ),
    ]
