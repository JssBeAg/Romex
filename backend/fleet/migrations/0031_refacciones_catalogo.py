from django.db import migrations
from django.db.models.functions import Lower

from ._datos_refacciones import SPARE_PARTS


def load_spare_parts(apps, schema_editor):
    SparePart = apps.get_model("fleet", "SparePart")
    for name, description in SPARE_PARTS:
        # Not case sensitive, like the unique constraint
        if not SparePart.objects.annotate(lower_name=Lower("name")).filter(lower_name=name.lower()).exists():
            SparePart.objects.create(name=name, description=description)


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0030_refacciones_nombre_obligatorio"),
    ]

    operations = [
        migrations.RunPython(load_spare_parts, migrations.RunPython.noop),
    ]
