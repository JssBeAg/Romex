from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0009_mantenimientos_refacciones"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="sparepart",
            name="maintenance",
        ),
        migrations.AddField(
            model_name="maintenance",
            name="spare_parts",
            field=models.ManyToManyField(
                related_name="maintenances",
                through="fleet.MaintenanceSparePart",
                to="fleet.sparepart",
            ),
        ),
    ]
