import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Step 3: the role is required; the link tables for roles and permissions are removed."""

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("accounts", "0005_usuario_rol_datos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="users",
                to="auth.group",
                db_column="id_rol",
                verbose_name="rol",
            ),
        ),
        migrations.RemoveField(model_name="user", name="groups"),
        migrations.RemoveField(model_name="user", name="user_permissions"),
        migrations.DeleteModel(name="UserRole"),
        migrations.DeleteModel(name="UserPermission"),
    ]
