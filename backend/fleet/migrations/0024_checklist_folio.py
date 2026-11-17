from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1: the folio column is added as nullable so existing rows can be filled."""

    dependencies = [
        ("fleet", "0023_evidencias_reportes"),
    ]

    operations = [
        migrations.AddField(
            model_name="checklist",
            name="folio",
            field=models.PositiveIntegerField(
                null=True, db_column="folio", verbose_name="folio"
            ),
        ),
    ]
