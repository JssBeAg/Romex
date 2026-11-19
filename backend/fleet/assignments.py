"""
Who has what. An assignment with no end date is the open one: the one in force now.
  - A unit has at most one operator with an open assignment, and an operator at most one unit.
  - Operators can only report failures and fill checklists for the unit they have open.
  - Mechanics can only see, diagnose and repair the fault reports assigned to them.
"""
from .models import FaultReport, Unit, UnitOperator

NOT_ASSIGNED = "Esa unidad no está asignada a ti."


def operator_label(operator):
    return f"{operator.get_full_name()} ({operator.enrollment_id})"


def open_assignment_of_unit(unit, exclude_pk=None):
    queryset = UnitOperator.objects.select_related("operator").filter(unit=unit, end_date__isnull=True)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.first()


def open_assignment_of_operator(operator, exclude_pk=None):
    queryset = UnitOperator.objects.select_related("unit").filter(operator=operator, end_date__isnull=True)
    if exclude_pk is not None:
        queryset = queryset.exclude(pk=exclude_pk)
    return queryset.first()


def unit_taken_message(unit, exclude_pk=None):
    """Why the unit cannot get another operator now, or "" when it can."""
    current = open_assignment_of_unit(unit, exclude_pk)
    if current is None:
        return ""
    return (
        f"La unidad {unit.economic_number} ya está asignada a {operator_label(current.operator)}. "
        "Primero termina esa asignación."
    )


def operator_taken_message(operator, exclude_pk=None):
    """Why the operator cannot get another unit now, or "" when they can."""
    current = open_assignment_of_operator(operator, exclude_pk)
    if current is None:
        return ""
    return (
        f"{operator_label(operator)} ya tiene asignada la unidad {current.unit.economic_number}. "
        "Primero termina esa asignación."
    )


def assigned_units(operator):
    """
    The unit the operator has open now (at most one, as a queryset). Both conditions go in one
    filter so they apply to the same assignment.
    """
    return Unit.objects.filter(
        operator_assignments__operator=operator,
        operator_assignments__end_date__isnull=True,
        is_active=True,  # an inactive unit takes no new records
    )


def may_use_unit(operator, unit, current_unit_id=None):
    """
    True when the operator has the unit open now. A record that already uses a unit may keep it
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
