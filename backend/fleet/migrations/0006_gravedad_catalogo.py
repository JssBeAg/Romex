import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0005_migrar_gravedad"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="faultdiagnosis",
            name="gravedad_valida",
        ),
        migrations.RemoveField(
            model_name="faultdiagnosis",
            name="severity",
        ),
        migrations.RenameField(
            model_name="faultdiagnosis",
            old_name="severity_catalog",
            new_name="severity",
        ),
        migrations.AlterField(
            model_name="faultdiagnosis",
            name="severity",
            field=models.ForeignKey(
                db_column="id_gravedad",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="diagnoses",
                to="fleet.severity",
                verbose_name="gravedad",
            ),
        ),
    ]
