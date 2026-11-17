from django.db import migrations

from ._datos_camiones import BRANDS_AND_MODELS


def load_brands_and_models(apps, schema_editor):
    Brand = apps.get_model("fleet", "Brand")
    UnitModel = apps.get_model("fleet", "UnitModel")
    for brand_name, model_names in BRANDS_AND_MODELS.items():
        brand, _ = Brand.objects.get_or_create(name=brand_name)
        for model_name in model_names:
            UnitModel.objects.get_or_create(brand=brand, name=model_name)


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0014_nombres_marcas_modelos_obligatorios"),
    ]

    operations = [
        migrations.RunPython(load_brands_and_models, migrations.RunPython.noop),
    ]
