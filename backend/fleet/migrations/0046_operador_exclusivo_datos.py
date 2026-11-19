"""
Exclusive operator assignment, step 1 of 2 (data): before the unique constraints of 0047 exist,
leave at most one open assignment per unit and one per operator.

  - Per unit with several open assignments: the one with the latest start date stays open
    (on a tie, the newest row); the others get end date = today (Mexico City).
  - Then the same per operator with several open units.

No row is deleted. Idempotent: a second run finds nothing to close. No reverse is needed:
undoing it leaves the data as it is (a closed assignment is valid history either way).
"""

from django.db import migrations
from django.utils import timezone


def close_duplicate_open_assignments(UnitOperator, today):
    """Close the extra open assignments. Returns how many were closed. Also used by the tests."""
    closed = 0
    for field in ("unit_id", "operator_id"):
        open_rows = UnitOperator.objects.filter(end_date__isnull=True).order_by(field, "-start_date", "-id")
        kept = set()
        for assignment in open_rows:
            key = getattr(assignment, field)
            if key not in kept:
                kept.add(key)  # the most recent one stays open
                continue
            # An assignment that (wrongly) starts in the future cannot end before it starts
            assignment.end_date = max(today, assignment.start_date)
            assignment.save(update_fields=["end_date"])
            closed += 1
    return closed


def forwards(apps, schema_editor):
    UnitOperator = apps.get_model("fleet", "UnitOperator")
    close_duplicate_open_assignments(UnitOperator, timezone.localdate())


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0045_placa_estado_texto_final"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
