from fleet.models import UnitModel
from notifications.models import Notification
from notifications.service import sync_preventive

from .base import ApiTestCase, today


class PreventiveTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = self.make_unit("P-1", mileage=1000)

    def rows_for_unit(self, plan_name="Cambio de aceite y filtros"):
        rows = self.g.get_json("/api/preventivo/vencimientos/").json()["rows"]
        return [r for r in rows if r["unit"]["label"] == "P-1" and r["plan"]["name"] == plan_name]

    def service(self, mileage, plan_id=None):
        data = {
            "service_type_id": 1, "unit_id": self.unit["id"], "service_mileage": str(mileage),
            "total_cost": "10", "date": today(), "operator_ids": [], "spare_parts": [],
        }
        if plan_id:
            data["plan_id"] = plan_id
        r = self.m.post_json("/api/mantenimientos/", data)
        self.assertEqual(r.status_code, 201, r.content)

    def plan_id(self, name="Cambio de aceite y filtros"):
        plans = self.g.get_json("/api/preventivo/planes/").json()["plans"]
        return next(p["id"] for p in plans if p["name"] == name)

    def test_no_history_then_up_to_date_then_overdue(self):
        self.assertEqual(self.rows_for_unit()[0]["status"], "sin_historial")
        self.service(1000, self.plan_id())
        row = self.rows_for_unit()[0]
        self.assertEqual(row["status"], "al_corriente")
        self.assertEqual(row["next_km"], 11000)
        # The unit keeps working: another service (not of the plan) shows it has gone further
        self.service(11500)
        row = self.rows_for_unit()[0]
        self.assertEqual(row["status"], "vencido")
        self.assertEqual(row["remaining_km"], -500)

    def test_upcoming_when_less_than_ten_percent_is_left(self):
        self.service(1000, self.plan_id())
        self.service(10500)  # 500 km left of 10 000
        self.assertEqual(self.rows_for_unit()[0]["status"], "proximo")

    def test_inactive_unit_and_inactive_plan_are_left_out(self):
        pid = self.plan_id()
        plan = self.g.get_json(f"/api/preventivo/planes/{pid}/").json()["plan"]
        r = self.g.put_json(
            f"/api/preventivo/planes/{pid}/",
            {"name": plan["name"], "every_km": plan["every_km"], "every_days": plan["every_days"], "is_active": False},
        )
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(self.rows_for_unit(), [])

    def test_plan_needs_an_interval(self):
        r = self.g.post_json("/api/preventivo/planes/", {"name": "Sin intervalo"})
        self.assertEqual(r.status_code, 400)

    def test_plan_for_one_model_only_applies_to_it(self):
        other = UnitModel.objects.exclude(pk=UnitModel.objects.first().pk).first()
        r = self.g.post_json(
            "/api/preventivo/planes/",
            {"name": "Solo otro modelo", "every_km": 5000, "unit_model_id": other.pk},
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(self.rows_for_unit("Solo otro modelo"), [])

    def test_overdue_creates_one_notification_for_managers(self):
        self.service(1000, self.plan_id())
        self.service(11500)
        sync_preventive()
        sync_preventive()  # a second poll does not repeat it
        found = Notification.objects.filter(user=self.manager, kind=Notification.PREVENTIVE, message__contains="P-1")
        self.assertEqual(found.count(), 1)
        self.assertIn("vencido", found.first().message)

    def test_pdf(self):
        r = self.g.get_json("/api/preventivo/vencimientos/", format="pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_only_managers_see_it(self):
        self.assertEqual(self.o.get("/api/preventivo/vencimientos/").status_code, 403)
