"""Which models are audited, and how their tables are named for the people who read the trail."""

from django.apps import apps

# "app_label.ModelName" -> name shown in the trail (singular)
AUDITED = {
    "accounts.User": "Trabajador",
    "accounts.WorkerContact": "Contacto del trabajador",
    "accounts.PhoneCode": "Código telefónico",
    "fleet.Brand": "Marca",
    "fleet.UnitModel": "Modelo",
    "fleet.Unit": "Unidad",
    "fleet.LicensePlate": "Placa",
    "fleet.UnitLicensePlate": "Asignación de placa",
    "fleet.UnitOperator": "Asignación de operador",
    "fleet.FaultReport": "Reporte de falla",
    "fleet.ReportMechanic": "Asignación de mecánico",
    "fleet.ReportEvidence": "Evidencia de reporte",
    "fleet.FaultDiagnosis": "Diagnóstico",
    "fleet.Maintenance": "Mantenimiento",
    "fleet.MaintenanceSparePart": "Refacción de mantenimiento",
    "fleet.MaintenanceOperator": "Participante de mantenimiento",
    "fleet.SparePart": "Refacción",
    "fleet.InventoryMovement": "Movimiento de inventario",
    "fleet.MaintenancePlan": "Plan de preventivo",
    "fleet.Checklist": "Checklist",
}

AUDITED_NAMES = dict(AUDITED)

# Fields that never go into the trail (noise, or secrets)
SKIPPED_FIELDS = {"last_login", "failed_attempts", "locked_until"}
SECRET_FIELDS = {"password"}


def audited_models():
    return [apps.get_model(label) for label in AUDITED]


def table_labels():
    """db_table -> name shown in the trail."""
    return {apps.get_model(label)._meta.db_table: name for label, name in AUDITED.items()}


# Spanish names for fields whose model label is not in Spanish (by field name)
FIELD_LABELS = {
    "unit": "Unidad",
    "unit_model": "Modelo",
    "license_plate": "Placa",
    "operator": "Operador",
    "mechanic": "Mecánico",
    "fault_report": "Reporte de falla",
    "reported_by": "Reportó",
    "diagnosed_by": "Diagnosticó",
    "registered_by": "Registró",
    "completed_by": "Completó",
    "diagnosis": "Diagnóstico",
    "maintenance": "Mantenimiento",
    "spare_part": "Refacción",
    "plan": "Plan preventivo",
    "movement_type": "Tipo",
    "user": "Usuario",
    "folio": "Folio",
}
