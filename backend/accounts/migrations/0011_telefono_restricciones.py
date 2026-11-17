"""Closes the phone change: digits-only national number and the new CHECK constraints
(run after 0010 has converted the existing numbers, so no row breaks them)."""

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_codigos_telefonicos_datos"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="user",
            name="usuario_datos_completos_salvo_superusuario",
        ),
        migrations.AlterField(
            model_name="user",
            name="phone_number",
            field=models.CharField(
                blank=True,
                db_column="telefono",
                max_length=14,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Escribe solo números (de 4 a 14 dígitos), sin el código del país.",
                        regex="^\\d{4,14}$",
                    )
                ],
                verbose_name="número telefónico",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("is_superuser", True),
                    models.Q(
                        ("sex__isnull", False),
                        ("address__isnull", False),
                        models.Q(("email", ""), _negated=True),
                        models.Q(("phone_number", ""), _negated=True),
                        ("phone_code__isnull", False),
                    ),
                    _connector="OR",
                ),
                name="usuario_datos_completos_salvo_superusuario",
            ),
        ),
        migrations.AddConstraint(
            model_name="user",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("phone_number", ""), ("phone_code__isnull", False), _connector="OR"
                ),
                name="usuario_telefono_requiere_codigo",
            ),
        ),
    ]
