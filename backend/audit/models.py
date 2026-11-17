from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """
    One line of the audit trail: who did what, to which record and when.

    Lines are written by signals (see signals.py), never by the views, and they cannot be
    changed or deleted afterwards. The person's matrícula, name and role are copied into
    the line, so the trail stays readable even if the worker changes or is removed.
    """

    CREATE = "crear"
    UPDATE = "modificar"
    DELETE = "eliminar"
    LOGIN = "inicio_sesion"
    LOGOUT = "cierre_sesion"
    LOGIN_FAILED = "inicio_sesion_fallido"
    ACCOUNT_LOCKED = "cuenta_bloqueada"
    PASSWORD_CHANGED = "contrasena_cambiada"
    EXPORT = "exportar"
    ACTIONS = [
        (CREATE, "Creó"),
        (UPDATE, "Modificó"),
        (DELETE, "Eliminó"),
        (LOGIN, "Inició sesión"),
        (LOGOUT, "Cerró sesión"),
        (LOGIN_FAILED, "Intento de inicio de sesión fallido"),
        (ACCOUNT_LOCKED, "Cuenta bloqueada por intentos fallidos"),
        (PASSWORD_CHANGED, "Cambió su contraseña"),
        (EXPORT, "Exportó un PDF"),
    ]

    timestamp = models.DateTimeField("fecha y hora", auto_now_add=True, db_column="fecha_hora")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
        verbose_name="usuario",
        db_column="id_usuario",
    )
    # What the user was like at that moment (a failed login keeps the typed matrícula here)
    user_enrollment_id = models.CharField(
        "matrícula", max_length=30, blank=True, db_column="matricula_usuario"
    )
    user_name = models.CharField("nombre", max_length=460, blank=True, db_column="nombre_usuario")
    user_role = models.CharField("rol", max_length=150, blank=True, db_column="rol_usuario")
    action = models.CharField("acción", max_length=30, choices=ACTIONS, db_column="accion")
    # db_table of the changed record (e.g. "unidades"); empty for sessions
    table_name = models.CharField("tabla", max_length=60, blank=True, db_column="tabla")
    record_id = models.BigIntegerField("id del registro", null=True, blank=True, db_column="id_registro")
    # How the record was called (e.g. "E-1 (Freightliner / 114SD)")
    record = models.CharField("registro", max_length=300, blank=True, db_column="registro")
    # {"Campo": [valor anterior, valor nuevo]}; the passwords are never stored
    changes = models.JSONField("cambios", null=True, blank=True, db_column="cambios")
    ip_address = models.GenericIPAddressField("dirección IP", null=True, blank=True, db_column="direccion_ip")

    class Meta:
        db_table = "bitacora_auditoria"
        verbose_name = "registro de bitácora"
        verbose_name_plural = "bitácora"
        ordering = ("-timestamp", "-id")
        indexes = [
            models.Index(fields=["-timestamp"], name="bitacora_fecha_idx"),
            models.Index(fields=["table_name", "record_id"], name="bitacora_registro_idx"),
        ]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} · {self.user_enrollment_id or 'Sistema'} · {self.get_action_display()}"

    def save(self, *args, **kwargs):
        # A line is written once and never edited
        if not self._state.adding:
            raise PermissionError("Las líneas de la bitácora no se pueden modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Las líneas de la bitácora no se pueden eliminar.")
