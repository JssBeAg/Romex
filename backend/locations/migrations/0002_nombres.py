from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1: add the name columns as optional (existing rows are filled in the next step)."""

    dependencies = [
        ("locations", "0001_inicial"),
    ]

    operations = [
        migrations.AddField(
            model_name=model,
            name="name",
            field=models.CharField(max_length=150, null=True, db_column="nombre"),
        )
        for model in ("country", "state", "city", "neighborhood")
    ] + [
        migrations.AddField(
            model_name="address",
            name="neighborhood",
            field=models.ForeignKey(
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name="addresses",
                to="locations.neighborhood",
                db_column="id_colonia",
            ),
        ),
        migrations.AddField(
            model_name="address",
            name="street_name",
            field=models.CharField(max_length=150, null=True, db_column="calle"),
        ),
    ]
