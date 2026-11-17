import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3: the address points to its street; the text street and the direct neighborhood go away."""

    dependencies = [
        ("locations", "0008_calles_datos"),
    ]

    operations = [
        migrations.RemoveField(model_name="address", name="street"),
        migrations.RemoveField(model_name="address", name="neighborhood"),
        migrations.RenameField(model_name="address", old_name="street_link", new_name="street"),
        migrations.AlterField(
            model_name="address",
            name="street",
            field=models.ForeignKey(
                db_column="id_calle",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="addresses",
                to="locations.street",
                verbose_name="calle",
            ),
        ),
    ]
