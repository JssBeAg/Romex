from django.db import migrations

ADMIN_ROLE = "Administrador"


def copy_roles(apps, schema_editor):
    """Each user gets the role they had in usuarios_roles (superusers without one: Administrador)."""
    User = apps.get_model("accounts", "User")
    UserRole = apps.get_model("accounts", "UserRole")
    Group = apps.get_model("auth", "Group")
    for user in User.objects.filter(role__isnull=True):
        link = UserRole.objects.filter(user=user).order_by("id").first()
        if link is not None:
            user.role_id = link.group_id
        elif user.is_superuser:
            user.role, _ = Group.objects.get_or_create(name=ADMIN_ROLE)
        else:
            raise RuntimeError(
                f"El usuario {user.enrollment_id} no tiene rol y no se puede saber cuál le "
                "corresponde. Asígnale uno o reinicia la base de datos "
                "(docker compose down -v) y vuelve a migrar."
            )
        user.save(update_fields=["role"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_usuario_rol"),
    ]

    operations = [
        migrations.RunPython(copy_roles, migrations.RunPython.noop),
    ]
