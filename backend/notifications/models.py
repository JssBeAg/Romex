from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """A message for one user ("a report was assigned to you"). Shown in the bell of the menu."""

    REPORT_NEW = "reporte_nuevo"
    REPORT_ASSIGNED = "reporte_asignado"
    REPORT_STATUS = "reporte_estatus"
    LOW_STOCK = "stock_bajo"
    PREVENTIVE = "preventivo"
    ACCOUNT_LOCKED = "cuenta_bloqueada"
    KINDS = [
        (REPORT_NEW, "Reporte nuevo"),
        (REPORT_ASSIGNED, "Reporte asignado"),
        (REPORT_STATUS, "Cambio de estatus"),
        (LOW_STOCK, "Stock bajo"),
        (PREVENTIVE, "Mantenimiento preventivo"),
        (ACCOUNT_LOCKED, "Cuenta bloqueada"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="usuario",
        db_column="id_usuario",
    )
    kind = models.CharField("tipo", max_length=30, choices=KINDS, db_column="tipo")
    message = models.CharField("mensaje", max_length=300, db_column="mensaje")
    # Where the notification leads (a page of the frontend, e.g. /reportes/5)
    link = models.CharField("enlace", max_length=200, blank=True, db_column="enlace")
    # Identifies what the notification is about, to avoid sending the same one twice
    key = models.CharField("clave", max_length=120, blank=True, db_column="clave")
    is_read = models.BooleanField("leída", default=False, db_column="leida")
    created_at = models.DateTimeField("fecha y hora", default=timezone.now, db_column="fecha_hora")

    class Meta:
        db_table = "notificaciones"
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=["user", "is_read"], name="notificacion_usuario_leida"),
        ]

    def __str__(self):
        return f"{self.user_id}: {self.message}"
