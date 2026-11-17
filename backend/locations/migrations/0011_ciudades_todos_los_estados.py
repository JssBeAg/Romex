from django.db import migrations

from ._datos_ciudades import CITIES_BY_STATE
from ._datos_mexico import COUNTRY


def load_cities(apps, schema_editor):
    """
    All the cities (municipios, INEGI) of the 32 states. It only adds what is missing, so the
    38 cities of Coahuila (and anything an administrator added) stay as they are, and running
    it twice changes nothing.
    """
    Country = apps.get_model("locations", "Country")
    State = apps.get_model("locations", "State")
    City = apps.get_model("locations", "City")

    country, _ = Country.objects.get_or_create(name=COUNTRY)
    for state_name, names in CITIES_BY_STATE.items():
        state, _ = State.objects.get_or_create(country=country, name=state_name)
        existing = set(City.objects.filter(state=state).values_list("name", flat=True))
        City.objects.bulk_create(City(state=state, name=name) for name in names if name not in existing)


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0010_datos_calles"),
    ]

    operations = [
        # Reverse: nothing is removed (cities may already have colonias and addresses)
        migrations.RunPython(load_cities, migrations.RunPython.noop),
    ]
