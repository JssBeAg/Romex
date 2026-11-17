import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 1: the role becomes a column of users (nullable for now, so rows can be filled)."""

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("accounts", "0003_superusuario_datos_opcionales"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="role",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="users",
                to="auth.group",
                db_column="id_rol",
                verbose_name="rol",
            ),
        ),
    ]
