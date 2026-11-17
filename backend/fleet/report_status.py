"""
The status of a fault report is not typed in by anyone: it is worked out from what has
happened to the report, and every change is kept in the history (ReportStatusChange).

    Pendiente                 nobody is assigned to it yet
    Asignado                  the manager assigned at least one mechanic, no diagnosis yet
    Diagnosticado             it has a diagnosis that says it needs a repair, no maintenance yet
    Sin reparación necesaria  the diagnosis says it needs no repair (the report is closed)
    En reparación             it has maintenances, but none says the repair is finished
    Reparado                  a maintenance says the repair is finished (the report is closed)

Call refresh_report_status(report, user) after anything that can change it: a mechanic
assigned or removed, a diagnosis saved or deleted, a maintenance saved or deleted.
"""

from django.utils import timezone

from .models import FaultDiagnosis, FaultReportStatus, Maintenance, ReportStatusChange

PENDING_STATUS = "Pendiente"
ASSIGNED_STATUS = "Asignado"
DIAGNOSED_STATUS = "Diagnosticado"
NO_REPAIR_STATUS = "Sin reparación necesaria"
IN_REPAIR_STATUS = "En reparación"
REPAIRED_STATUS = "Reparado"

# In the order of the life of a report
STATUSES = [
    PENDING_STATUS,
    ASSIGNED_STATUS,
    DIAGNOSED_STATUS,
    NO_REPAIR_STATUS,
    IN_REPAIR_STATUS,
    REPAIRED_STATUS,
]

# The report needs nothing else: no more mechanics, and it is not "open" any more
CLOSED_STATUSES = (REPAIRED_STATUS, NO_REPAIR_STATUS)


def status_name_for(report):
    """The status the report should have right now."""
    maintenances = Maintenance.objects.filter(diagnosis__fault_report=report)
    if maintenances.filter(repair_completed=True).exists():
        return REPAIRED_STATUS
    if maintenances.exists():
        return IN_REPAIR_STATUS
    # Looked up again each time: a cached diagnosis may have been deleted a moment ago
    diagnosis = FaultDiagnosis.objects.filter(fault_report=report).first()
    if diagnosis is not None:
        return DIAGNOSED_STATUS if diagnosis.requires_repair else NO_REPAIR_STATUS
    if report.mechanic_assignments.filter(end_date__isnull=True).exists():
        return ASSIGNED_STATUS
    return PENDING_STATUS


def record_status(report, status, user):
    """Writes a line in the history."""
    ReportStatusChange.objects.create(
        fault_report=report, status=status, changed_by=user, changed_at=timezone.now()
    )


def refresh_report_status(report, user=None):
    """Brings the status of the report up to date and records the change, if there was one."""
    name = status_name_for(report)
    if report.status.name == name:
        return False
    report.status = FaultReportStatus.objects.get(name=name)
    report.save(update_fields=["status"])
    record_status(report, report.status, user)
    return True
