"""A fault report from the operator's report to the mechanic's repair, and what it triggers."""

from notifications.models import Notification

from .base import ApiTestCase, today


class ReportWorkflowTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = self.make_unit("W-1")
        self.report = self.make_report(self.unit)

    def assign(self, mechanic=None, report_id=None):
        return self.g.post_json(
            f"/api/reportes-fallas/{report_id or self.report['id']}/mecanicos/",
            {"mechanic_id": (mechanic or self.mechanic).pk, "start_date": today()},
        )

    def diagnose(self, requires_repair=True):
        return self.m.post_json(
            "/api/diagnosticos/",
            {
                "fault_report_id": self.report["id"], "severity_id": 2, "date": today(),
                "description": "x", "detailed_cause": "Balatas", "requires_repair": requires_repair,
                "unit_operable": False,
            },
        )

    def maintenance(self, diagnosis_id, **over):
        data = {
            "service_type_id": 2, "diagnosis_id": diagnosis_id, "service_mileage": "1500",
            "total_cost": "100", "date": today(), "observations": "", "operator_ids": [], "spare_parts": [],
        }
        data.update(over)
        return self.m.post_json("/api/mantenimientos/", data)

    def test_new_report_is_pending_and_managers_are_notified(self):
        self.assertEqual(self.report["status"]["label"], "Pendiente")
        self.assertTrue(Notification.objects.filter(user=self.manager, kind=Notification.REPORT_NEW).exists())
        # Whoever caused the event does not notify themselves
        self.assertFalse(Notification.objects.filter(user=self.operator, kind=Notification.REPORT_NEW).exists())

    def test_operator_only_reports_units_assigned_to_them(self):
        other = self.make_unit("W-2", operator=self.operator2)
        r = self.o.post_json(
            "/api/reportes-fallas/",
            {"unit_id": other["id"], "date": today(), "location": "x", "description": "y"},
        )
        self.assertEqual(r.status_code, 400)

    def test_status_is_calculated_through_the_whole_flow(self):
        self.assertEqual(self.assign().status_code, 201)
        self.assertEqual(self.report_status(self.report["id"]), "Asignado")
        self.assertTrue(Notification.objects.filter(user=self.mechanic, kind=Notification.REPORT_ASSIGNED).exists())

        r = self.diagnose()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.report_status(self.report["id"]), "Diagnosticado")
        diagnosis_id = r.json()["diagnosis"]["id"]

        r = self.maintenance(diagnosis_id)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.report_status(self.report["id"]), "En reparación")

        r = self.maintenance(diagnosis_id, repair_completed=True)
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.report_status(self.report["id"]), "Reparado")

        # The reporter hears about the changes; the managers about the closing
        self.assertTrue(Notification.objects.filter(user=self.operator, kind=Notification.REPORT_STATUS).exists())
        self.assertTrue(Notification.objects.filter(user=self.manager, kind=Notification.REPORT_STATUS).exists())

    def test_history_of_statuses_is_kept(self):
        self.assign()
        history = self.g.get_json(f"/api/reportes-fallas/{self.report['id']}/").json()["report"]["status_history"]
        self.assertEqual([h["status"] for h in history], ["Pendiente", "Asignado"])
        self.assertIn("G1", history[-1]["changed_by"])

    def test_no_repair_needed_closes_the_report(self):
        self.assign()
        self.assertEqual(self.diagnose(requires_repair=False).status_code, 201)
        self.assertEqual(self.report_status(self.report["id"]), "Sin reparación necesaria")

    def test_repaired_report_takes_no_more_maintenances(self):
        self.assign()
        did = self.diagnose().json()["diagnosis"]["id"]
        self.assertEqual(self.maintenance(did, repair_completed=True).status_code, 201)
        r = self.maintenance(did)
        self.assertEqual(r.status_code, 400)
        self.assertIn("diagnosis_id", r.json()["errors"])

    def test_unassigned_mechanic_cannot_diagnose(self):
        self.assign(self.mechanic)
        m2 = self.client_for(self.mechanic2)
        r = m2.post_json(
            "/api/diagnosticos/",
            {"fault_report_id": self.report["id"], "severity_id": 2, "date": today(), "detailed_cause": "x",
             "requires_repair": True, "unit_operable": True, "description": "x"},
        )
        self.assertEqual(r.status_code, 400)

    def test_unit_with_open_reports_cannot_be_deactivated(self):
        detail = self.g.get_json(f"/api/unidades/{self.unit['id']}/").json()["unit"]
        r = self.g.put_json(
            f"/api/unidades/{self.unit['id']}/",
            {"economic_number": detail["economic_number"], "unit_model_id": detail["unit_model"]["id"],
             "mileage": str(detail["mileage"]), "is_active": False},
        )
        self.assertEqual(r.status_code, 400, r.content)

    def test_pdf_sheets_of_a_report_and_diagnosis(self):
        self.assign()
        did = self.diagnose().json()["diagnosis"]["id"]
        for path in (f"/api/reportes-fallas/{self.report['id']}/", f"/api/diagnosticos/{did}/"):
            r = self.g.get_json(path, format="pdf")
            self.assertEqual(r.status_code, 200, path)
            self.assertTrue(r.content.startswith(b"%PDF"), path)
