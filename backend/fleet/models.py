from django.conf import settings
from django.core.validators import MinValueValidator
import os

from django.db import models
from django.db.models.functions import Lower
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils import timezone


# Python names are in English; table, column and constraint names in the database are in
# Spanish (db_table / db_column / constraint names).
#
# on_delete=PROTECT everywhere: a record cannot be deleted while others depend on it,
# so history is never lost by accident (users should be deactivated, not deleted).


class Brand(models.Model):
    name = models.CharField("nombre", max_length=100, unique=True, db_column="nombre")

    class Meta:
        db_table = "marcas"
        verbose_name = "marca"
        verbose_name_plural = "marcas"
        ordering = ["name"]

    def __str__(self):
        return self.name


class UnitModel(models.Model):
    # A brand has many models
    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="unit_models",
        verbose_name="marca",
        db_column="id_marca",
    )
    name = models.CharField("nombre", max_length=100, db_column="nombre")

    class Meta:
        db_table = "modelos"
        verbose_name = "modelo"
        verbose_name_plural = "modelos"
        ordering = ["brand__name", "name"]
        constraints = [
            models.UniqueConstraint(fields=["brand", "name"], name="modelo_nombre_unico"),
        ]

    def __str__(self):
        return self.name


class Unit(models.Model):
    # How the company identifies the unit (used instead of the license plate)
    economic_number = models.CharField(
        "número económico", max_length=20, db_column="numero_economico"
    )
    # Many units belong to one model
    unit_model = models.ForeignKey(
        UnitModel,
        on_delete=models.PROTECT,
        related_name="units",
        db_column="id_modelo",
    )
    # Odometer reading in kilometers
    mileage = models.PositiveIntegerField("kilometraje", db_column="kilometraje")
    # An inactive unit (sold, scrapped...) keeps all its history but takes no new reports,
    # checklists, maintenances or operators. Deactivate it instead of deleting it.
    is_active = models.BooleanField("activa", default=True, db_column="activa")
    # Plates the unit has had over time (N:N); the dates live in UnitLicensePlate
    license_plates = models.ManyToManyField(
        "LicensePlate",
        through="UnitLicensePlate",
        related_name="units",
    )

    class Meta:
        db_table = "unidades"
        verbose_name = "unidad"
        verbose_name_plural = "unidades"
        constraints = [
            models.UniqueConstraint(
                fields=["economic_number"], name="unidad_numero_economico_unico"
            ),
        ]

    def __str__(self):
        return self.economic_number


class LicensePlate(models.Model):
    identifier = models.CharField("placa", max_length=15, db_column="identificador")
    # The state that issued the plate
    state = models.CharField("estado", max_length=100, db_column="estado")

    class Meta:
        db_table = "placas"
        verbose_name = "placa"
        verbose_name_plural = "placas"
        constraints = [
            # The same identifier can exist in different states, but only once per state
            models.UniqueConstraint(
                fields=["state", "identifier"], name="placa_unica_por_estado"
            ),
        ]

    def save(self, *args, **kwargs):
        # Plates are stored uppercase and without surrounding spaces
        self.identifier = self.identifier.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.identifier


class UnitLicensePlate(models.Model):
    """Which plate a unit had, and since when until when. No end date = it has it now."""

    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="plate_assignments",
        db_column="id_unidad",
    )
    license_plate = models.ForeignKey(
        LicensePlate,
        on_delete=models.PROTECT,
        related_name="unit_assignments",
        db_column="id_placa",
    )
    start_date = models.DateField("inicio", db_column="fecha_inicio")
    end_date = models.DateField("fin", null=True, blank=True, db_column="fecha_fin")

    class Meta:
        db_table = "unidades_placas"
        verbose_name = "placa de unidad"
        verbose_name_plural = "placas de unidades"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="fin_no_antes_de_inicio",
            ),
            # At most one current plate per unit, and one current unit per plate
            models.UniqueConstraint(
                fields=["unit"],
                condition=models.Q(end_date__isnull=True),
                name="una_placa_vigente_por_unidad",
            ),
            models.UniqueConstraint(
                fields=["license_plate"],
                condition=models.Q(end_date__isnull=True),
                name="una_unidad_vigente_por_placa",
            ),
        ]


class UnitOperator(models.Model):
    """
    Which operator has a unit, and since when until when. No end date = has it now.
    A unit can have several operators at once, and an operator several units.
    """

    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="operator_assignments",
        db_column="id_unidad",
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="unit_assignments",
        db_column="id_operador",
    )
    start_date = models.DateField("inicio", db_column="fecha_inicio")
    end_date = models.DateField("fin", null=True, blank=True, db_column="fecha_fin")

    class Meta:
        db_table = "unidades_operadores"
        verbose_name = "operador de unidad"
        verbose_name_plural = "operadores de unidades"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="operador_fin_no_antes_de_inicio",
            ),
            # The same operator cannot be assigned twice to the same unit at the same time
            models.UniqueConstraint(
                fields=["unit", "operator"],
                condition=models.Q(end_date__isnull=True),
                name="un_operador_vigente_por_unidad",
            ),
        ]

    def __str__(self):
        return f"{self.unit} - {self.operator}"


class FaultReportStatus(models.Model):
    """
    Catalog of report statuses, created by a migration: Pendiente, Asignado, Diagnosticado,
    En reparación, Reparado and Sin reparación necesaria. The status of a report is worked out
    by the server from what has happened to it (see report_status.py), never typed in.
    """

    name = models.CharField("nombre", max_length=30, unique=True, db_column="nombre")
    # Position in the life of a report, to list the statuses in order
    order = models.PositiveSmallIntegerField("orden", default=0, db_column="orden")

    class Meta:
        db_table = "estatus_reportes"
        verbose_name = "estatus de reporte"
        verbose_name_plural = "estatus de reportes"
        ordering = ("order", "id")

    def __str__(self):
        return self.name


class FaultReport(models.Model):
    # A unit has many fault reports
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="fault_reports",
        db_column="id_unidad",
    )
    # Who made the report
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fault_reports",
        db_column="id_usuario_reporta",
    )
    # Consecutive number per author, assigned when the record is created (see folios.py)
    folio = models.PositiveIntegerField("folio", db_column="folio")
    status = models.ForeignKey(
        FaultReportStatus,
        on_delete=models.PROTECT,
        related_name="fault_reports",
        verbose_name="estatus",
        db_column="id_estatus",
    )

    # Where the fault happened, as free text (e.g. "Carretera México-Puebla km 45")
    location = models.CharField("ubicación", max_length=255, db_column="ubicacion")
    date = models.DateField("fecha", db_column="fecha")
    description = models.TextField("descripción", db_column="descripcion")

    class Meta:
        db_table = "reportes_de_fallas"
        verbose_name = "reporte de falla"
        verbose_name_plural = "reportes de fallas"
        constraints = [
            models.UniqueConstraint(fields=["reported_by", "folio"], name="reporte_folio_unico"),
        ]


class ReportStatusChange(models.Model):
    """
    Every status a fault report has had, with the moment it changed (the first row is the
    creation of the report). The current status is the latest row. Written by report_status.py.
    """

    fault_report = models.ForeignKey(
        FaultReport,
        on_delete=models.PROTECT,
        related_name="status_changes",
        verbose_name="reporte de falla",
        db_column="id_reporte",
    )
    status = models.ForeignKey(
        FaultReportStatus,
        on_delete=models.PROTECT,
        related_name="changes",
        verbose_name="estatus",
        db_column="id_estatus",
    )
    changed_at = models.DateTimeField("fecha y hora", default=timezone.now, db_column="fecha_hora")
    # Who caused the change; empty when it was made by the system (e.g. a migration)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="report_status_changes",
        verbose_name="realizado por",
        db_column="id_usuario",
    )

    class Meta:
        db_table = "historial_estatus_reportes"
        verbose_name = "cambio de estatus de reporte"
        verbose_name_plural = "historial de estatus de reportes"
        ordering = ("changed_at", "id")
        indexes = [
            models.Index(fields=["fault_report", "changed_at"], name="hist_estatus_reporte_idx"),
        ]

    def __str__(self):
        return f"{self.fault_report} → {self.status}"


class ReportMechanic(models.Model):
    """
    Which mechanic a fault report is assigned to, and since when until when. No end date =
    assigned now. A report can have several mechanics at once, and a mechanic several reports.
    """

    fault_report = models.ForeignKey(
        FaultReport,
        on_delete=models.PROTECT,
        related_name="mechanic_assignments",
        db_column="id_reporte",
    )
    mechanic = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="report_assignments",
        db_column="id_mecanico",
    )
    start_date = models.DateField("inicio", db_column="fecha_inicio")
    end_date = models.DateField("fin", null=True, blank=True, db_column="fecha_fin")

    class Meta:
        db_table = "reportes_de_fallas_mecanicos"
        verbose_name = "mecánico de reporte"
        verbose_name_plural = "mecánicos de reportes"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__isnull=True)
                | models.Q(end_date__gte=models.F("start_date")),
                name="mecanico_fin_no_antes_de_inicio",
            ),
            # The same mechanic cannot be assigned twice to the same report at the same time
            models.UniqueConstraint(
                fields=["fault_report", "mechanic"],
                condition=models.Q(end_date__isnull=True),
                name="un_mecanico_vigente_por_reporte",
            ),
        ]

    def __str__(self):
        return f"{self.fault_report} - {self.mechanic}"


class ReportEvidence(models.Model):
    """A photo attached to a fault report (a report can have several; none is also fine)."""

    fault_report = models.ForeignKey(
        FaultReport,
        on_delete=models.CASCADE,
        related_name="evidence_images",
        db_column="id_reporte_falla",
    )
    image = models.ImageField(
        "imagen", upload_to="evidencias/%Y/%m", max_length=255, db_column="archivo"
    )
    original_name = models.CharField("nombre original", max_length=255, db_column="nombre_original")
    uploaded_at = models.DateTimeField("fecha de subida", auto_now_add=True, db_column="fecha_subida")

    class Meta:
        db_table = "evidencias_reportes"
        verbose_name = "evidencia de reporte"
        verbose_name_plural = "evidencias de reportes"
        ordering = ["id"]


@receiver(post_delete, sender=ReportEvidence)
def delete_evidence_file(sender, instance, **kwargs):
    """Remove the file from disk when its row is deleted (also when the report is deleted)."""
    if instance.image and os.path.isfile(instance.image.path):
        os.remove(instance.image.path)


class Severity(models.Model):
    """Catalog of fault severities (Baja, Media, Alta, Crítica), created by a migration."""

    name = models.CharField("nombre", max_length=30, unique=True, db_column="nombre")

    class Meta:
        db_table = "gravedades"
        verbose_name = "gravedad"
        verbose_name_plural = "gravedades"

    def __str__(self):
        return self.name


class FaultDiagnosis(models.Model):
    # One fault report has at most one diagnosis (1:1)
    fault_report = models.OneToOneField(
        FaultReport,
        on_delete=models.PROTECT,
        related_name="diagnosis",
        db_column="id_reporte_falla",
    )
    # Who made the diagnosis
    diagnosed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="fault_diagnoses",
        db_column="id_usuario_diagnostica",
    )
    # Consecutive number per author, assigned when the record is created (see folios.py)
    folio = models.PositiveIntegerField("folio", db_column="folio")

    date = models.DateField("fecha", db_column="fecha")
    detailed_cause = models.TextField("causa detallada", db_column="causa_detallada")
    # Whether the fault needs a repair (if not, no maintenance is expected for this diagnosis)
    requires_repair = models.BooleanField("requiere reparación", db_column="requiere_reparacion")
    # Whether the unit can keep operating while the fault is dealt with
    unit_operable = models.BooleanField("unidad operable", db_column="unidad_operable")
    severity = models.ForeignKey(
        Severity,
        on_delete=models.PROTECT,
        related_name="diagnoses",
        verbose_name="gravedad",
        db_column="id_gravedad",
    )

    class Meta:
        db_table = "diagnosticos_de_fallas"
        verbose_name = "diagnóstico de falla"
        verbose_name_plural = "diagnósticos de fallas"
        constraints = [
            models.UniqueConstraint(
                fields=["diagnosed_by", "folio"], name="diagnostico_folio_unico"
            ),
        ]


class ServiceType(models.Model):
    """Catalog of service types (Preventivo, Correctivo), created by a migration."""

    name = models.CharField("nombre", max_length=30, unique=True, db_column="nombre")

    class Meta:
        db_table = "tipos_servicio"
        verbose_name = "tipo de servicio"
        verbose_name_plural = "tipos de servicio"

    def __str__(self):
        return self.name


class MaintenancePlan(models.Model):
    """
    A preventive maintenance plan: a service that must be repeated every so many kilometers
    and/or every so many days (e.g. "Cambio de aceite", every 10,000 km or 180 days).
    It applies to the units of one model, or to every unit when no model is chosen.
    When is each unit due? It is worked out from the last maintenance done for the plan
    (see preventive.py); nothing about it is stored.
    """

    name = models.CharField("nombre", max_length=120, db_column="nombre")
    description = models.TextField("descripción", blank=True, db_column="descripcion")
    every_km = models.PositiveIntegerField(
        "cada (km)", null=True, blank=True, validators=[MinValueValidator(1)], db_column="cada_km"
    )
    every_days = models.PositiveIntegerField(
        "cada (días)", null=True, blank=True, validators=[MinValueValidator(1)], db_column="cada_dias"
    )
    # Empty: applies to every unit
    unit_model = models.ForeignKey(
        UnitModel,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="maintenance_plans",
        verbose_name="modelo",
        db_column="id_modelo",
    )
    # An inactive plan stops giving alerts but keeps its history
    is_active = models.BooleanField("activo", default=True, db_column="activo")

    class Meta:
        db_table = "planes_mantenimiento"
        verbose_name = "plan de mantenimiento preventivo"
        verbose_name_plural = "planes de mantenimiento preventivo"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="plan_nombre_unico"),
            # At least one way of knowing when it is due
            models.CheckConstraint(
                condition=models.Q(every_km__isnull=False) | models.Q(every_days__isnull=False),
                name="plan_cada_km_o_dias",
            ),
        ]

    def __str__(self):
        return self.name


class Maintenance(models.Model):
    # The unit the service was done on. Corrective maintenance has the same unit as the
    # report of its diagnosis; preventive maintenance has no diagnosis, so it needs this.
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="maintenances",
        db_column="id_unidad",
    )
    # A diagnosis can have many maintenances. Empty (null) for preventive maintenance,
    # which does not come from a fault; corrective maintenance has a diagnosis.
    diagnosis = models.ForeignKey(
        FaultDiagnosis,
        on_delete=models.PROTECT,
        related_name="maintenances",
        null=True,
        blank=True,
        db_column="id_diagnostico",
    )
    # The mechanic who registered it (always one of the operators)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registered_maintenances",
        db_column="id_usuario_registra",
    )
    # Consecutive number per author, assigned when the record is created (see folios.py)
    folio = models.PositiveIntegerField("folio", db_column="folio")
    # Operators who did the maintenance (N:N): several per maintenance, several maintenances per operator
    operators = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="MaintenanceOperator",
        related_name="maintenances",
    )

    # Spare parts used (N:N): a maintenance can use several, and a part can be used in several
    spare_parts = models.ManyToManyField(
        "SparePart",
        through="MaintenanceSparePart",
        related_name="maintenances",
    )

    service_type = models.ForeignKey(
        ServiceType,
        on_delete=models.PROTECT,
        related_name="maintenances",
        verbose_name="tipo de servicio",
        db_column="id_tipo_servicio",
    )
    # The preventive plan this service fulfils (optional; only for preventive maintenance).
    # It restarts the count of kilometers and days of the plan for this unit.
    plan = models.ForeignKey(
        MaintenancePlan,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="maintenances",
        verbose_name="plan preventivo",
        db_column="id_plan",
    )
    # Odometer reading in kilometers when the service was done
    service_mileage = models.PositiveIntegerField("km de servicio", db_column="km_servicio")
    total_cost = models.DecimalField(
        "costo total",
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        db_column="costo_total",
    )
    date = models.DateField("fecha", db_column="fecha")
    # Optional: not every maintenance has notes
    observations = models.TextField("observaciones", blank=True, db_column="observaciones")
    # The mechanic says the repair is finished. Only corrective maintenance (with a diagnosis)
    # can say so; it is what makes the fault report "Reparado".
    repair_completed = models.BooleanField(
        "reparación terminada", default=False, db_column="reparacion_terminada"
    )

    class Meta:
        db_table = "mantenimientos"
        verbose_name = "mantenimiento"
        verbose_name_plural = "mantenimientos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(repair_completed=False) | models.Q(diagnosis__isnull=False),
                name="reparacion_terminada_solo_correctivo",
            ),
            models.UniqueConstraint(
                fields=["registered_by", "folio"], name="mantenimiento_folio_unico"
            ),
            # A plan is preventive: a maintenance with a diagnosis (corrective) has none
            models.CheckConstraint(
                condition=models.Q(plan__isnull=True) | models.Q(diagnosis__isnull=True),
                name="plan_solo_preventivo",
            ),
        ]


class SparePart(models.Model):
    """Catalog of spare parts (refacciones). They are linked to maintenances (N:N)."""

    name = models.CharField("nombre", max_length=120, db_column="nombre")
    description = models.TextField("descripción", blank=True, db_column="descripcion")
    # Optional reference price in pesos (the real cost of a service is the maintenance's total cost)
    unit_price = models.DecimalField(
        "precio unitario",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        db_column="precio_unitario",
    )
    # Below (or at) this many in stock the part is flagged as low. The stock itself is not a
    # column: it is worked out from the movements and the maintenances (see inventory.py).
    min_stock = models.PositiveIntegerField(
        "existencia mínima", default=0, db_column="existencia_minima"
    )
    # An inactive part (discontinued) keeps its history but cannot be used in new maintenances
    is_active = models.BooleanField("activa", default=True, db_column="activa")
    # Optional photo (without one the screens show a neutral icon)
    photo = models.ImageField(
        "fotografía",
        upload_to="refacciones/",
        max_length=255,
        blank=True,
        db_column="foto",
        help_text="Opcional. Se guarda reducida y sin metadatos.",
    )

    class Meta:
        db_table = "refacciones"
        verbose_name = "refacción"
        verbose_name_plural = "refacciones"
        ordering = ["name"]
        constraints = [
            # The name is unique ignoring upper/lower case
            models.UniqueConstraint(Lower("name"), name="refaccion_nombre_unico"),
        ]

    def __str__(self):
        return self.name


class MaintenanceSparePart(models.Model):
    """Link between a maintenance and a spare part used in it."""

    maintenance = models.ForeignKey(
        Maintenance,
        on_delete=models.CASCADE,
        related_name="part_usages",
        db_column="id_mantenimiento",
    )
    # PROTECT: a part that was used in a maintenance cannot be deleted from the catalog
    spare_part = models.ForeignKey(
        SparePart,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_refaccion",
    )
    # How many pieces of the part were used (they leave the stock)
    quantity = models.PositiveIntegerField(
        "cantidad",
        default=1,
        validators=[MinValueValidator(1)],
        db_column="cantidad",
    )

    class Meta:
        db_table = "mantenimientos_refacciones"
        constraints = [
            models.UniqueConstraint(
                fields=["maintenance", "spare_part"], name="mantenimiento_refaccion_unico"
            ),
        ]


class InventoryMovement(models.Model):
    """
    Pieces that come into the stock (purchases) or are corrected after a physical count.
    The pieces that leave are not here: they are the quantities used in maintenances, so
    editing or deleting a maintenance gives the pieces back by itself.
    Stock of a part = sum of its movements - pieces used in maintenances.
    """

    ENTRY = "entrada"
    ADJUSTMENT = "ajuste"
    TYPES = [(ENTRY, "Entrada"), (ADJUSTMENT, "Ajuste")]

    spare_part = models.ForeignKey(
        SparePart,
        on_delete=models.PROTECT,
        related_name="movements",
        verbose_name="refacción",
        db_column="id_refaccion",
    )
    movement_type = models.CharField("tipo", max_length=10, choices=TYPES, db_column="tipo")
    # Positive: pieces added. Negative: pieces taken off (only for adjustments)
    quantity = models.IntegerField("cantidad", db_column="cantidad")
    date = models.DateField("fecha", db_column="fecha")
    # Why (supplier, invoice, count...). Required for adjustments.
    note = models.CharField("nota", max_length=255, blank=True, db_column="nota")
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="inventory_movements",
        verbose_name="registró",
        db_column="id_usuario",
    )
    created_at = models.DateTimeField("registrado el", default=timezone.now, db_column="fecha_registro")

    class Meta:
        db_table = "movimientos_inventario"
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"
        ordering = ("-date", "-id")
        constraints = [
            models.CheckConstraint(condition=~models.Q(quantity=0), name="movimiento_cantidad_no_cero"),
            # An entry always adds pieces
            models.CheckConstraint(
                condition=~models.Q(movement_type="entrada") | models.Q(quantity__gt=0),
                name="movimiento_entrada_positiva",
            ),
            models.CheckConstraint(
                condition=models.Q(movement_type__in=["entrada", "ajuste"]),
                name="movimiento_tipo_valido",
            ),
        ]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity:+d} · {self.spare_part}"


class MaintenanceOperator(models.Model):
    """Link between a maintenance and an operator (user) who took part in it."""

    maintenance = models.ForeignKey(
        Maintenance,
        on_delete=models.CASCADE,
        related_name="+",
        db_column="id_mantenimiento",
    )
    # PROTECT: an operator who appears in a maintenance cannot be deleted (history is kept)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        db_column="id_usuario",
    )

    class Meta:
        db_table = "mantenimientos_operadores"
        constraints = [
            models.UniqueConstraint(
                fields=["maintenance", "user"], name="mantenimiento_operador_unico"
            ),
        ]


class Checklist(models.Model):
    # A unit has many checklists
    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="checklists",
        db_column="id_unidad",
    )
    # Who filled in the checklist
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="checklists",
        db_column="id_usuario_registra",
    )

    date = models.DateField("fecha", db_column="fecha")
    # Odometer reading in kilometers when the checklist was filled in
    recorded_mileage = models.PositiveIntegerField("km registrado", db_column="km_registrado")
    # Pressure in PSI and tread depth in millimeters, one decimal
    tire_pressure = models.DecimalField(
        "presión de llantas (PSI)",
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0)],
        db_column="presion_llanta",
    )
    tire_tread_depth = models.DecimalField(
        "profundidad de llantas (mm)",
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(0)],
        db_column="profundidad_llanta",
    )
    # No default on purpose: each check must be answered explicitly
    lights_ok = models.BooleanField("luces ok", db_column="luces_ok")
    fluids_ok = models.BooleanField("fluidos ok", db_column="fluidos_ok")
    no_cracks = models.BooleanField("sin grietas", db_column="sin_grietas")
    trip_description = models.TextField("descripción del viaje", db_column="descripcion_viaje")
    # Consecutive number per operator (shown as e.g. O1-0003), assigned by the server
    folio = models.PositiveIntegerField("folio", db_column="folio")

    class Meta:
        db_table = "checklists"
        verbose_name = "checklist"
        verbose_name_plural = "checklists"
        constraints = [
            models.UniqueConstraint(
                fields=["completed_by", "folio"], name="checklist_folio_unico"
            ),
        ]
