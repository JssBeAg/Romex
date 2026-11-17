import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Step 1 of making colonia and street plain text inside the address: the new columns
    (id_ciudad, colonia, calle) next to the old id_calle. The next migration fills them in.
    """

    dependencies = [
        ("locations", "0011_ciudades_todos_los_estados"),
    ]

    operations = [
        migrations.AddField(
            model_name="address",
            name="city",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="addresses",
                to="locations.city",
                db_column="id_ciudad",
            ),
        ),
        migrations.AddField(
            model_name="address",
            name="neighborhood_text",
            field=models.CharField(default="", max_length=150, db_column="colonia"),
        ),
        migrations.AddField(
            model_name="address",
            name="street_text",
            field=models.CharField(default="", max_length=150, db_column="calle"),
        ),
    ]
