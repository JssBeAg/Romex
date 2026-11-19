"""
The kardex of a unit lists the times its own data was corrected or changed: in the section
«Cambios de datos» (one row per field, in columns) and in the general timeline.
"""

from .base import ApiTestCase, today


class KardexChangesTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        # Without an operator: a unit with one cannot be deactivated (and these tests deactivate it)
        self.unit = self.make_unit("KC-1", operator=None, mileage=1000)

    def edit(self, **over):
        detail = self.g.get_json(f"/api/unidades/{self.unit['id']}/").json()["unit"]
        data = {
            "economic_number": detail["economic_number"], "unit_model_id": detail["unit_model"]["id"],
            "mileage": str(detail["mileage"]), "is_active": detail["is_active"],
        }
        data.update(over)
        r = self.g.put_json(f"/api/unidades/{self.unit['id']}/", data)
        self.assertEqual(r.status_code, 200, r.content)

    def kardex(self, client=None):
        r = (client or self.g).get_json(f"/api/kardex/{self.unit['id']}/")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def changes(self):
        """The change events of the general timeline (one per save)."""
        r = self.g.get_json(f"/api/kardex/{self.unit['id']}/linea-de-tiempo/", tipo="change")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["events"]

    def change_rows(self, **params):
        """The section «Cambios de datos» (one row per field changed)."""
        r = self.g.get_json(f"/api/kardex/{self.unit['id']}/cambios/", **params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_a_new_unit_has_no_changes(self):
        self.assertEqual(self.changes(), [])

    def test_a_correction_shows_what_it_said_before_and_after_who_and_when(self):
        self.edit(mileage="1500", economic_number="KC-1A")
        (event,) = self.changes()
        self.assertEqual(event["date"], today())
        self.assertIn("G1", event["title"])  # who did it
        self.assertIn("Kilometraje: 1000 → 1500", event["detail"])
        self.assertIn("KC-1A", event["detail"])
        self.assertRegex(event["detail"], r"^\d{2}:\d{2}\. ")  # the time of the day
        self.assertIsNone(event["link"])

    def test_a_save_that_changes_nothing_adds_nothing(self):
        self.edit()
        self.assertEqual(self.changes(), [])

    def test_deactivating_and_reactivating_are_both_listed_newest_first(self):
        self.edit(is_active=False)
        self.edit(is_active=True)
        events = self.changes()
        self.assertEqual(len(events), 2)
        self.assertIn("No → Sí", events[0]["detail"])  # the later one first
        self.assertIn("Sí → No", events[1]["detail"])

    def test_changes_of_another_unit_are_not_mixed_in(self):
        other = self.make_unit("KC-2", operator=None)
        self.edit(mileage="1100")
        detail = self.g.get_json(f"/api/unidades/{other['id']}/").json()["unit"]
        r = self.g.put_json(f"/api/unidades/{other['id']}/", {
            "economic_number": detail["economic_number"], "unit_model_id": detail["unit_model"]["id"],
            "mileage": "9999", "is_active": True,
        })
        self.assertEqual(r.status_code, 200)
        (event,) = self.changes()
        self.assertNotIn("9999", event["detail"])

    def test_the_pdf_of_the_kardex_carries_them(self):
        self.edit(mileage="1500")
        r = self.g.get(f"/api/kardex/{self.unit['id']}/?format=pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF-"))

    def test_the_section_has_one_row_per_field_in_columns(self):
        self.edit(mileage="1500", economic_number="KC-1A")
        data = self.change_rows()
        rows = sorted(data["changes"], key=lambda r: r["field"])
        self.assertEqual([(r["field"], r["old"], r["new"]) for r in rows],
                         [("Kilometraje", "1000", "1500"), ("Número económico", "KC-1", "KC-1A")])
        self.assertTrue(all("G1" in r["user"] and r["date"] == today() for r in rows))
        self.assertRegex(rows[0]["moment"], r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
        self.assertEqual(data["users"], [{"id": self.manager.pk, "label": rows[0]["user"]}])

    def test_the_section_filters_by_user_dates_and_text(self):
        self.edit(mileage="1500")
        self.edit(is_active=False)
        self.assertEqual(self.change_rows()["pagination"]["total"], 2)
        self.assertEqual(self.change_rows(q="kilometraje")["pagination"]["total"], 1)
        self.assertEqual(self.change_rows(usuario=self.mechanic.pk)["pagination"]["total"], 0)
        self.assertEqual(self.change_rows(usuario=self.manager.pk)["pagination"]["total"], 2)
        self.assertEqual(self.change_rows(date_to="2000-01-01")["pagination"]["total"], 0)
        self.assertEqual(self.change_rows(order="field")["changes"][0]["field"], "Activa")
        r = self.g.get(f"/api/kardex/{self.unit['id']}/cambios/?format=pdf&q=kilometraje")
        self.assertTrue(r.content.startswith(b"%PDF-"))

    def test_mechanics_and_operators_still_cannot_open_the_kardex(self):
        self.edit(mileage="1500")
        sections = ("", "linea-de-tiempo/", "mantenimientos/", "fallas/", "checklists/", "refacciones/", "operadores/", "cambios/")
        for client in (self.m, self.o):
            for section in sections:
                self.assertEqual(client.get(f"/api/kardex/{self.unit['id']}/{section}").status_code, 403, section)
