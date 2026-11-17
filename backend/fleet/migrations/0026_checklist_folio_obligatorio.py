from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3: the folio becomes required and unique per operator."""

    dependencies = [
        ("fleet", "0025_checklist_folio_datos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="checklist",
            name="folio",
            field=models.PositiveIntegerField(db_column="folio", verbose_name="folio"),
        ),
        migrations.AddConstraint(
            model_name="checklist",
            constraint=models.UniqueConstraint(
                fields=("completed_by", "folio"), name="checklist_folio_unico"
            ),
        ),
    ]
