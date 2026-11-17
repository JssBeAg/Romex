import datetime

from django.db import migrations
from django.utils import timezone

STATUSES = [
    "Pendiente",
    "Asignado",
    "Diagnosticado",
    "Sin reparación necesaria",
    "En reparación",
    "Reparado",
]


def crear_estatus(apps, schema_editor):
    """The old "En mantenimiento" becomes "En reparación" (same row, so reports keep it)."""
    Status = apps.get_model("fleet", "FaultReportStatus")
    Status.objects.filter(name="En mantenimiento").update(name="En reparación")
    for position, name in enumerate(STATUSES, start=1):
        status, _ = Status.objects.get_or_create(name=name)
        status.order = position
        status.save(update_fields=["order"])


def recalcular_reportes(apps, schema_editor):
    """Gives every existing report its status under the new rules, and its first history line."""
    Status = apps.get_model("fleet", "FaultReportStatus")
    Report = apps.get_model("fleet", "FaultReport")
    Diagnosis = apps.get_model("fleet", "FaultDiagnosis")
    Maintenance = apps.get_model("fleet", "Maintenance")
    Assignment = apps.get_model("fleet", "ReportMechanic")
    Change = apps.get_model("fleet", "ReportStatusChange")
    by_name = {s.name: s for s in Status.objects.all()}

    for report in Report.objects.all():
        maintenances = Maintenance.objects.filter(diagnosis__fault_report=report)
        diagnosis = Diagnosis.objects.filter(fault_report=report).first()
        if maintenances.filter(repair_completed=True).exists():
            name = "Reparado"
        elif maintenances.exists():
            name = "En reparación"
        elif diagnosis is not None:
            name = "Diagnosticado" if diagnosis.requires_repair else "Sin reparación necesaria"
        elif Assignment.objects.filter(fault_report=report, end_date__isnull=True).exists():
            name = "Asignado"
        else:
            name = "Pendiente"
        if report.status_id != by_name[name].pk:
            report.status = by_name[name]
            report.save(update_fields=["status"])
        # The history starts at the day of the report (the real moments were not recorded)
        started = timezone.make_aware(datetime.datetime.combine(report.date, datetime.time(0, 0)))
        Change.objects.create(fault_report=report, status=by_name[name], changed_at=started)


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0034_estatus_reportes_historial"),
    ]

    operations = [
        migrations.RunPython(crear_estatus, migrations.RunPython.noop),
        migrations.RunPython(recalcular_reportes, migrations.RunPython.noop),
    ]
