"""States and municipalities come from INEGI's web service, not from tables."""

from unittest import mock

from django.core.cache import cache
from django.db import connection

from locations import inegi
from locations.inegi import InegiUnavailable

from .base import ApiTestCase
from .test_address_text import AddressTextTest


class InegiCatalogTest(ApiTestCase):
    def test_states_are_served_from_inegi(self):
        r = self.g.get_json("/api/ubicaciones/estados/")
        self.assertEqual(r.status_code, 200)
        options = r.json()["options"]
        self.assertEqual(len(options), 32)
        self.assertIn("Jalisco", options)
        self.assertEqual(options, sorted(options))

    def test_municipalities_depend_on_the_state(self):
        r = self.g.get_json("/api/ubicaciones/municipios/", estado="Jalisco")
        self.assertIn("Zapopan", r.json()["options"])
        r = self.g.get_json("/api/ubicaciones/municipios/", estado="Coahuila de Zaragoza")
        self.assertIn("Saltillo", r.json()["options"])
        self.assertNotIn("Zapopan", r.json()["options"])
        self.assertEqual(self.g.get_json("/api/ubicaciones/municipios/").json()["options"], [])
        self.assertEqual(self.g.get_json("/api/ubicaciones/municipios/", estado="Atlantis").json()["options"], [])

    def test_only_the_manager_can_ask(self):
        self.assertEqual(self.o.get_json("/api/ubicaciones/estados/").status_code, 403)
        self.assertEqual(self.m.get_json("/api/ubicaciones/municipios/", estado="Jalisco").status_code, 403)

    def test_answers_are_cached_so_inegi_is_not_asked_every_time(self):
        mocked = inegi._get
        cache.clear()
        self.g.get_json("/api/ubicaciones/estados/")
        self.g.get_json("/api/ubicaciones/estados/")
        self.assertEqual(mocked.call_count, 1)

    def test_when_inegi_does_not_answer_the_api_says_so(self):
        with mock.patch.object(inegi, "_get", side_effect=InegiUnavailable("x")):
            cache.clear()
            r = self.g.get_json("/api/ubicaciones/estados/")
            self.assertEqual(r.status_code, 503)
            self.assertIn("INEGI", r.json()["error"])

    def test_the_parser_accepts_the_field_names_of_the_service(self):
        rows = [{"cve_ent": "01", "nomgeo": "Aguascalientes"}, {"cve_agee": "02", "nom_agee": "Baja California"}]
        with mock.patch.object(inegi, "_get", return_value=rows):
            cache.clear()
            self.assertEqual(inegi.state_names(), ["Aguascalientes", "Baja California"])

    def test_the_catalog_tables_are_gone(self):
        tables = connection.introspection.table_names()
        for name in ("paises", "estados", "ciudades"):
            self.assertNotIn(name, tables)


class InegiDownTest(ApiTestCase):
    """Saving needs INEGI, except when the address keeps the same place it already had."""

    def payload(self, **address):
        return AddressTextTest.payload(self, **address)

    def test_a_new_address_cannot_be_saved_while_inegi_is_down(self):
        with mock.patch.object(inegi, "_get", side_effect=InegiUnavailable("x")):
            cache.clear()
            r = self.g.post_json("/api/trabajadores/", self.payload())
        self.assertEqual(r.status_code, 400)
        self.assertIn("INEGI", r.json()["errors"]["state"][0])

    def test_an_existing_address_keeps_saving_when_the_place_does_not_change(self):
        created = self.g.post_json("/api/trabajadores/", self.payload()).json()["worker"]
        data = self.payload(street="Otra calle")
        data["password"] = ""
        with mock.patch.object(inegi, "_get", side_effect=InegiUnavailable("x")):
            cache.clear()
            r = self.g.put_json(f"/api/trabajadores/{created['id']}/", data)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["worker"]["address"]["street"], "Otra calle")


class PlateStateTest(ApiTestCase):
    def test_the_plate_keeps_the_state_name_and_it_must_be_inegis(self):
        unit = self.make_unit("P-1")
        self.assertEqual(self.g.get_json(f"/api/unidades/{unit['id']}/").json()["unit"]["current_plate"]["state"],
                         "Coahuila de Zaragoza")
        r = self.g.post_json("/api/unidades/", {
            "economic_number": "P-2", "unit_model_id": 1, "mileage": "1",
            "plate": {"identifier": "ZZ1", "state": "Atlantis", "start_date": "2026-01-01"},
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn("plate_state", r.json()["errors"])
