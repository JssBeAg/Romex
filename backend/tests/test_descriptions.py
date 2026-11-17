"""The description of the report is seen in the diagnosis; the description of the diagnosis, in the maintenance."""

from fleet.models import FaultReport

from .base import ApiTestCase, today

REPORT_TEXT = "Se escucha un golpeteo al frenar"


class DescriptionsTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = self.make_unit("D-1")
        self.report = self.make_report(self.unit)
        FaultReport.objects.filter(pk=self.report["id"]).update(description=REPORT_TEXT)
        r = self.g.post_json(
            f"/api/reportes-fallas/{self.report['id']}/mecanicos/",
            {"mechanic_id": self.mechanic.pk, "start_date": today()},
        )
        self.assertEqual(r.status_code, 201, r.content)

    def diagnose(self):
        r = self.m.post_json("/api/diagnosticos/", {
            "fault_report_id": self.report["id"], "severity_id": 2, "date": today(),
            "detailed_cause": "Balatas", "requires_repair": True, "unit_operable": False,
        })
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["diagnosis"]["id"]

    def maintenance(self, **over):
        data = {
            "service_type_id": 2, "service_mileage": "1500", "total_cost": "100", "date": today(),
            "observations": "", "operator_ids": [], "spare_parts": [],
        }
        data.update(over)
        r = self.m.post_json("/api/mantenimientos/", data)
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["maintenance"]

    def test_the_diagnosis_form_catalog_carries_the_report_description(self):
        reports = self.m.get_json("/api/diagnosticos/catalogos/").json()["reports"]
        mine = [r for r in reports if r["id"] == self.report["id"]]
        self.assertEqual(mine[0]["description"], REPORT_TEXT)

    def test_the_diagnosis_carries_the_report_description_for_mechanic_and_manager(self):
        diagnosis_id = self.diagnose()
        for client in (self.m, self.g):
            data = client.get_json(f"/api/diagnosticos/{diagnosis_id}/").json()["diagnosis"]
            self.assertEqual(data["fault_report"]["description"], REPORT_TEXT)
        listed = self.g.get_json("/api/diagnosticos/").json()["diagnoses"][0]
        self.assertEqual(listed["fault_report"]["description"], REPORT_TEXT)

    def test_the_maintenance_form_catalog_carries_the_diagnosis_description(self):
        diagnosis_id = self.diagnose()
        diagnoses = self.m.get_json("/api/mantenimientos/catalogos/").json()["diagnoses"]
        mine = [d for d in diagnoses if d["id"] == diagnosis_id]
        self.assertEqual(mine[0]["detailed_cause"], "Balatas")

    def test_the_maintenance_carries_the_diagnosis_description(self):
        diagnosis_id = self.diagnose()
        maintenance_id = self.maintenance(diagnosis_id=diagnosis_id)["id"]
        for client in (self.m, self.g):
            data = client.get_json(f"/api/mantenimientos/{maintenance_id}/").json()["maintenance"]
            self.assertEqual(data["diagnosis"]["detailed_cause"], "Balatas")

    def test_a_preventive_maintenance_has_no_diagnosis_description(self):
        maintenance = self.maintenance(service_type_id=1, unit_id=self.unit["id"])
        self.assertIsNone(maintenance["diagnosis"])

    def test_the_pdf_sheets_still_build_with_the_new_sections(self):
        diagnosis_id = self.diagnose()
        maintenance_id = self.maintenance(diagnosis_id=diagnosis_id)["id"]
        for url in (f"/api/diagnosticos/{diagnosis_id}/?format=pdf", f"/api/mantenimientos/{maintenance_id}/?format=pdf"):
            r = self.g.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertEqual(r["Content-Type"], "application/pdf")
            self.assertTrue(r.content.startswith(b"%PDF-"))
