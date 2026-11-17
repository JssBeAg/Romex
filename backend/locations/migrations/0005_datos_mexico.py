from django.db import migrations

from ._datos_mexico import COAHUILA_CITIES, COUNTRY, SALTILLO_NEIGHBORHOODS, STATES

COAHUILA = "Coahuila de Zaragoza"
SALTILLO = "Saltillo"


def load_locations(apps, schema_editor):
    """México, its 32 states, the cities of Coahuila and the neighborhoods of Saltillo."""
    Country = apps.get_model("locations", "Country")
    State = apps.get_model("locations", "State")
    City = apps.get_model("locations", "City")
    Neighborhood = apps.get_model("locations", "Neighborhood")

    country, _ = Country.objects.get_or_create(name=COUNTRY)
    for name in STATES:
        State.objects.get_or_create(country=country, name=name)

    coahuila = State.objects.get(country=country, name=COAHUILA)
    for name in COAHUILA_CITIES:
        City.objects.get_or_create(state=coahuila, name=name)

    saltillo = City.objects.get(state=coahuila, name=SALTILLO)
    for name in SALTILLO_NEIGHBORHOODS:
        Neighborhood.objects.get_or_create(city=saltillo, name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("locations", "0004_nombres_obligatorios"),
    ]

    operations = [
        migrations.RunPython(load_locations, migrations.RunPython.noop),
    ]
