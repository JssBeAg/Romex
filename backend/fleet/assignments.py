"""
Who has what. An assignment with no end date is the one in force now.
  - Operators can only report failures and fill checklists for the units they have.
  - Mechanics can only see, diagnose and repair the fault reports assigned to them.
"""
from .models import FaultReport, Unit

NOT_ASSIGNED = "Esa unidad no está asignada a ti."


def assigned_units(operator):
    """Units the operator has now. Both conditions go in one filter so they apply to the same assignment."""
    return Unit.objects.filter(
        operator_assignments__operator=operator,
        operator_assignments__end_date__isnull=True,
        is_active=True,  # an inactive unit takes no new records
    )


def may_use_unit(operator, unit, current_unit_id=None):
    """
    True when the operator has the unit now. A record that already uses a unit may keep it
    (current_unit_id) even if the assignment ended later: past records are not rewritten.
    """
    if current_unit_id is not None and unit.pk == current_unit_id:
        return True
    return assigned_units(operator).filter(pk=unit.pk).exists()


def reports_of(mechanic):
    """Fault reports assigned to the mechanic now."""
    return FaultReport.objects.filter(
        mechanic_assignments__mechanic=mechanic,
        mechanic_assignments__end_date__isnull=True,
    )
