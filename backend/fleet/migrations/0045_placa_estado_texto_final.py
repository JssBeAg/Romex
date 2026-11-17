from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3 of 3: the text column takes the place of the state foreign key."""

    dependencies = [("fleet", "0044_placa_estado_texto_datos")]

    operations = [
        migrations.RemoveConstraint(model_name="licenseplate", name="placa_unica_por_estado"),
        migrations.RemoveField(model_name="licenseplate", name="state"),
        migrations.RenameField(model_name="licenseplate", old_name="state_name", new_name="state"),
        migrations.AlterField(
            model_name="licenseplate",
            name="state",
            field=models.CharField(db_column="estado", max_length=100, verbose_name="estado"),
        ),
        migrations.AddConstraint(
            model_name="licenseplate",
            constraint=models.UniqueConstraint(fields=("state", "identifier"), name="placa_unica_por_estado"),
        ),
    ]
