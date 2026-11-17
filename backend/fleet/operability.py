"""
Whether a unit can go out to operate.

A unit is NOT fit to operate while it has a diagnosis that says "the unit cannot keep operating"
(unit_operable = False) on a fault report that is still open. The report closes when its repair is
finished ("Reparado") or the diagnosis says no repair is needed ("Sin reparación necesaria"); from
then on the unit is fit again. Nothing is typed in by anyone: it follows the diagnoses.
"""

from .models import FaultDiagnosis, Unit
from .report_status import CLOSED_STATUSES

NOT_OPERABLE = (
    "Esa unidad no está apta para operar: tiene una falla diagnosticada que aún no se repara."
)


def not_operable_unit_ids():
    """Ids (a set) of the units that cannot go out to operate now."""
    return set(
        FaultDiagnosis.objects.filter(unit_operable=False)
        .exclude(fault_report__status__name__in=CLOSED_STATUSES)
        .values_list("fault_report__unit_id", flat=True)
    )


def not_operable_units():
    return Unit.objects.filter(pk__in=not_operable_unit_ids())
