import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Step 3: the old street link goes away, the text columns take their final names, the city is
    required, and the colonias and calles tables are dropped (their names now live in the
    address as text).
    """

    dependencies = [
        ("locations", "0013_domicilio_texto_datos"),
    ]

    operations = [
        migrations.RemoveField(model_name="address", name="street"),
        migrations.RenameField(model_name="address", old_name="street_text", new_name="street"),
        migrations.RenameField(model_name="address", old_name="neighborhood_text", new_name="neighborhood"),
        migrations.AlterField(
            model_name="address",
            name="street",
            field=models.CharField(max_length=150, db_column="calle", verbose_name="calle"),
        ),
        migrations.AlterField(
            model_name="address",
            name="neighborhood",
            field=models.CharField(max_length=150, db_column="colonia", verbose_name="colonia"),
        ),
        migrations.AlterField(
            model_name="address",
            name="city",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="addresses",
                to="locations.city",
                db_column="id_ciudad",
                verbose_name="ciudad",
            ),
        ),
        migrations.DeleteModel(name="Street"),
        migrations.DeleteModel(name="Neighborhood"),
    ]
