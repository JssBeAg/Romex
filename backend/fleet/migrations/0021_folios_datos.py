from django.db import migrations


def fill_folios(apps, schema_editor):
    """
    Existing records get consecutive folios per author, oldest first. For maintenances the
    registering mechanic is taken to be the first operator listed.
    """
    FaultReport = apps.get_model("fleet", "FaultReport")
    FaultDiagnosis = apps.get_model("fleet", "FaultDiagnosis")
    Maintenance = apps.get_model("fleet", "Maintenance")
    MaintenanceOperator = apps.get_model("fleet", "MaintenanceOperator")

    for maintenance in Maintenance.objects.filter(registered_by__isnull=True):
        link = MaintenanceOperator.objects.filter(maintenance=maintenance).order_by("id").first()
        if link is None:
            raise RuntimeError(
                f"El mantenimiento {maintenance.pk} no tiene participantes y no se puede saber "
                "quién lo registró. Elimínalo o reinicia la base de datos "
                "(docker compose down -v) y vuelve a migrar."
            )
        maintenance.registered_by_id = link.user_id
        maintenance.save(update_fields=["registered_by"])

    for model, author in (
        (FaultReport, "reported_by_id"),
        (FaultDiagnosis, "diagnosed_by_id"),
        (Maintenance, "registered_by_id"),
    ):
        counters = {}
        for row in model.objects.filter(folio__isnull=True).order_by("id"):
            author_id = getattr(row, author)
            counters[author_id] = counters.get(author_id, 0) + 1
            row.folio = counters[author_id]
            row.save(update_fields=["folio"])


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0020_folios"),
    ]

    operations = [
        migrations.RunPython(fill_folios, migrations.RunPython.noop),
    ]
