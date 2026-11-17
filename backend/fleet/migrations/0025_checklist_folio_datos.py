from django.db import migrations


def fill_folios(apps, schema_editor):
    """Existing checklists get consecutive folios per operator, oldest first."""
    Checklist = apps.get_model("fleet", "Checklist")
    counters = {}
    for row in Checklist.objects.filter(folio__isnull=True).order_by("id"):
        counters[row.completed_by_id] = counters.get(row.completed_by_id, 0) + 1
        row.folio = counters[row.completed_by_id]
        row.save(update_fields=["folio"])


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0024_checklist_folio"),
    ]

    operations = [
        migrations.RunPython(fill_folios, migrations.RunPython.noop),
    ]
