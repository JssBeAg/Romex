"""The address: state and municipality (INEGI names) and colonia and street as free text."""

from django.db import connection

from locations.models import Address

from .base import ApiTestCase
from .test_contacts import mx


class AddressTextTest(ApiTestCase):
    def payload(self, **address):
        roles = {r["label"]: r["id"] for r in self.g.get("/api/trabajadores/catalogos/").json()["roles"]}
        from accounts.models import Sex

        data = {
            "enrollment_id": "DT1", "first_name": "Dora", "paternal_surname": "P", "maternal_surname": "M",
            "email": "dt1@example.com", "phone_code_id": mx().pk, "phone_number": "8441112233",
            "sex_id": Sex.objects.first().pk, "role_id": roles["Operador"], "is_active": True,
            "password": "Temporal12345x",
            "address": {
                "state": "Coahuila de Zaragoza", "municipality": "Saltillo", "neighborhood": "Las Flores",
                "street": "Av. Siempre Viva", "exterior_number": "742", "interior_number": "",
            },
        }
        data["address"].update(address)
        return data

    def test_colonia_and_street_are_saved_as_typed_and_returned(self):
        r = self.g.post_json("/api/trabajadores/", self.payload(neighborhood="  Mi colonia nueva ", street="Calle 5 de Mayo"))
        self.assertEqual(r.status_code, 201, r.content)
        address = r.json()["worker"]["address"]
        self.assertEqual(address["neighborhood"], "Mi colonia nueva")
        self.assertEqual(address["street"], "Calle 5 de Mayo")
        self.assertNotIn("street_id", address)
        self.assertNotIn("neighborhood_id", address)

    def test_any_state_and_municipality_of_inegi_work(self):
        r = self.g.post_json("/api/trabajadores/", self.payload(state="Jalisco", municipality="Zapopan"))
        self.assertEqual(r.status_code, 201, r.content)
        address = r.json()["worker"]["address"]
        self.assertEqual((address["state"], address["municipality"]), ("Jalisco", "Zapopan"))

    def test_missing_place_colonia_or_street_are_reported_each(self):
        r = self.g.post_json(
            "/api/trabajadores/", self.payload(state="", municipality="", neighborhood="  ", street="")
        )
        self.assertEqual(r.status_code, 400)
        errors = r.json()["errors"]
        self.assertEqual(errors["state"], ["Este campo es obligatorio."])
        self.assertEqual(errors["municipality"], ["Este campo es obligatorio."])
        self.assertIn("neighborhood", errors)
        self.assertIn("street", errors)

    def test_a_state_or_municipality_that_inegi_does_not_have_is_refused(self):
        r = self.g.post_json("/api/trabajadores/", self.payload(state="Atlantis"))
        self.assertIn("state", r.json()["errors"])
        r = self.g.post_json("/api/trabajadores/", self.payload(state="Jalisco", municipality="Saltillo"))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["errors"]["municipality"], ["Elige una opción válida."])

    def test_too_long_text_is_a_field_error_not_a_crash(self):
        r = self.g.post_json("/api/trabajadores/", self.payload(street="x" * 151))
        self.assertEqual(r.status_code, 400)
        self.assertIn("street", r.json()["errors"])

    def test_validation_only_does_not_save(self):
        r = self.g.post_json("/api/trabajadores/?validar=1", self.payload())
        self.assertEqual(r.json()["errors"], {})
        self.assertFalse(Address.objects.filter(street="Av. Siempre Viva").exists())

    def test_editing_changes_the_text(self):
        created = self.g.post_json("/api/trabajadores/", self.payload()).json()["worker"]
        data = self.payload(neighborhood="Otra colonia", street="Otra calle")
        data["password"] = ""
        r = self.g.put_json(f"/api/trabajadores/{created['id']}/", data)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["worker"]["address"]["street"], "Otra calle")

    def test_the_colonias_and_calles_tables_are_gone_and_domicilios_has_the_text(self):
        tables = connection.introspection.table_names()
        self.assertNotIn("colonias", tables)
        self.assertNotIn("calles", tables)
        with connection.cursor() as cursor:
            columns = {c.name for c in connection.introspection.get_table_description(cursor, "domicilios")}
        self.assertTrue({"estado", "municipio", "colonia", "calle"} <= columns)
        self.assertFalse({"id_ciudad"} & columns)
        self.assertNotIn("id_calle", columns)
