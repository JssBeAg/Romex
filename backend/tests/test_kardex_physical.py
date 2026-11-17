"""The kardex shows the physical work done on the unit: parts, mechanics, cause, observations."""

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

    def kardex(self):
        return self.g.get_json(f"/api/kardex/{self.unit['id']}/").json()

    def corrective(self):
        r = self.m.post_json(
            "/api/mantenimientos/",
            {"service_type_id": 2, "diagnosis_id": self.did, "service_mileage": "1500", "total_cost": "100",
             "date": today(), "observations": "Se rectificaron discos", "repair_completed": True,
             "operator_ids": [self.mechanic.pk], "spare_parts": [{"id": self.part["id"], "quantity": 4}]},
        )
        self.assertEqual(r.status_code, 201, r.content)

    def test_maintenance_event_shows_parts_people_and_cause(self):
        self.corrective()
        event = next(e for e in self.kardex()["events"] if e["type"] == "maintenance")
        for text in ("Balata × 4", "Balatas gastadas", "Falla", "Reparación terminada: sí", "M1",
                     "Se rectificaron discos"):
            self.assertIn(text, event["detail"])

    def test_parts_used_summary(self):
        self.corrective()
        used = self.kardex()["parts_used"]
        self.assertEqual([(p["label"], p["pieces"], p["times"]) for p in used], [("Balata", 4, 1)])

    def test_maintenance_without_parts_says_so(self):
        self.m.post_json("/api/mantenimientos/", {
            "service_type_id": 1, "unit_id": self.unit["id"], "service_mileage": "1200", "total_cost": "5",
            "date": today(), "operator_ids": [], "spare_parts": []})
        data = self.kardex()
        self.assertEqual(data["parts_used"], [])
        event = next(e for e in data["events"] if e["type"] == "maintenance")
        self.assertIn("Sin refacciones", event["detail"])

    def test_pdf_builds_with_parts_and_changes(self):
        self.corrective()
        r = self.g.get_json(f"/api/kardex/{self.unit['id']}/", format="pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))
