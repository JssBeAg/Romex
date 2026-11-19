"""
The kardex shows the physical work done on the unit: parts, mechanics, cause, observations,
each in its own field of the section «Mantenimientos», and the parts added up in «Refacciones».
"""

from .base import ApiTestCase, today


class KardexPhysicalTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = self.make_unit("K-1")
        self.part = self.make_part("Balata", stock=10)
        self.report = self.make_report(self.unit)
        self.g.post_json(
            f"/api/reportes-fallas/{self.report['id']}/mecanicos/",
            {"mechanic_id": self.mechanic.pk, "start_date": today()},
        )
        d = self.m.post_json(
            "/api/diagnosticos/",
            {"fault_report_id": self.report["id"], "severity_id": 2, "date": today(), "description": "x",
             "detailed_cause": "Balatas gastadas", "requires_repair": True, "unit_operable": False},
        )
        self.did = d.json()["diagnosis"]["id"]

    def section(self, name, **params):
        r = self.g.get_json(f"/api/kardex/{self.unit['id']}/{name}/", **params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def corrective(self):
        r = self.m.post_json(
            "/api/mantenimientos/",
            {"service_type_id": 2, "diagnosis_id": self.did, "service_mileage": "1500", "total_cost": "100",
             "date": today(), "observations": "Se rectificaron discos", "repair_completed": True,
             "operator_ids": [self.mechanic.pk], "spare_parts": [{"id": self.part["id"], "quantity": 4}]},
        )
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["maintenance"]

    def test_a_corrective_maintenance_has_parts_people_cause_and_repair_in_separate_fields(self):
        created = self.corrective()
        (row,) = self.section("mantenimientos")["maintenances"]
        self.assertEqual(row["id"], created["id"])
        self.assertEqual(row["service_type"], "Correctivo")
        self.assertEqual(row["mileage"], 1500)
        self.assertEqual(row["cost"], "100.00")
        self.assertEqual(row["parts"], [{"label": "Balata", "quantity": 4}])
        self.assertEqual(len(row["people"]), 1)
        self.assertIn("(M1)", row["people"][0])
        self.assertEqual(row["cause"], "Balatas gastadas")
        self.assertEqual(row["failure"], "Falla")  # the description of the report
        self.assertIs(row["repair_completed"], True)
        self.assertEqual(row["observations"], "Se rectificaron discos")
        self.assertEqual(row["report"]["id"], self.report["id"])
        self.assertEqual(row["diagnosis"]["id"], self.did)
        self.assertTrue(row["diagnosis"]["label"].startswith("Diagnóstico M1-"))
        # No text put together for display
        for value in row.values():
            self.assertNotIn("\n", str(value))

    def test_parts_used_summary(self):
        self.corrective()
        used = self.section("refacciones")["parts"]
        self.assertEqual([(p["label"], p["pieces"], p["times"], p["last_date"]) for p in used], [("Balata", 4, 1, today())])

    def test_a_maintenance_without_parts_has_an_empty_list(self):
        self.m.post_json("/api/mantenimientos/", {
            "service_type_id": 1, "unit_id": self.unit["id"], "service_mileage": "1200", "total_cost": "5",
            "date": today(), "operator_ids": [], "spare_parts": []})
        self.assertEqual(self.section("refacciones")["parts"], [])
        (row,) = self.section("mantenimientos")["maintenances"]
        self.assertEqual(row["parts"], [])
        self.assertIsNone(row["repair_completed"])  # preventive: no repair to finish
        self.assertIsNone(row["cause"])
        self.assertIsNone(row["report"])

    def test_the_fault_carries_its_diagnosis_in_fields(self):
        (row,) = self.section("fallas")["faults"]
        self.assertEqual(row["id"], self.report["id"])
        self.assertEqual(row["description"], "Falla")
        self.assertEqual(row["status"], "Diagnosticado")
        self.assertEqual([m.split(" (")[-1] for m in row["mechanics"]], ["M1)"])
        diagnosis = row["diagnosis"]
        self.assertEqual(diagnosis["cause"], "Balatas gastadas")
        self.assertIs(diagnosis["unit_operable"], False)
        self.assertIs(diagnosis["requires_repair"], True)
        self.assertTrue(diagnosis["severity"])

    def test_pdf_builds_with_parts_and_changes(self):
        self.corrective()
        r = self.g.get_json(f"/api/kardex/{self.unit['id']}/", format="pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))
