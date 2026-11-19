"""
The kardex organised by subject: each section is a list of its own (only its subject and only that
unit), with search, date range, its own filters, order, pagination and PDF.
"""

import datetime

from django.db import connection
from django.test.utils import CaptureQueriesContext

from .base import ApiTestCase, today


def days_ago(n):
    return (datetime.date.fromisoformat(today()) - datetime.timedelta(days=n)).isoformat()


class KardexSectionsTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = self.make_unit("KS-1")  # O1
        self.other = self.make_unit("KS-2", operator=self.operator2)
        self.o2 = self.client_for(self.operator2)

    # -- helpers --------------------------------------------------------------------------
    def section(self, name, unit=None, **params):
        r = self.g.get_json(f"/api/kardex/{(unit or self.unit)['id']}/{name}/", **params)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def total(self, name, **params):
        return self.section(name, **params)["pagination"]["total"]

    def preventive(self, unit=None, date=None, cost="10", mileage="1200", observations=""):
        r = self.m.post_json("/api/mantenimientos/", {
            "service_type_id": 1, "unit_id": (unit or self.unit)["id"], "service_mileage": mileage,
            "total_cost": cost, "date": date or today(), "observations": observations,
            "operator_ids": [], "spare_parts": []})
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["maintenance"]

    def corrective(self, completed):
        report = self.make_report(self.unit)
        self.g.post_json(f"/api/reportes-fallas/{report['id']}/mecanicos/", {"mechanic_id": self.mechanic.pk, "start_date": today()})
        d = self.m.post_json("/api/diagnosticos/", {
            "fault_report_id": report["id"], "severity_id": 2, "date": today(), "detailed_cause": "Frenos",
            "requires_repair": True, "unit_operable": True}).json()["diagnosis"]
        r = self.m.post_json("/api/mantenimientos/", {
            "service_type_id": 2, "diagnosis_id": d["id"], "service_mileage": "1500", "total_cost": "300",
            "date": today(), "operator_ids": [], "spare_parts": [], "repair_completed": completed})
        self.assertEqual(r.status_code, 201, r.content)
        return report

    def checklist(self, client, unit, lights=True, date=None):
        r = client.post_json("/api/checklists/", {
            "unit_id": unit["id"], "date": date or today(), "recorded_mileage": "1200", "tire_pressure": "32",
            "tire_tread_depth": "8", "lights_ok": lights, "fluids_ok": True, "no_cracks": True,
            "trip_description": "Ruta norte"})
        self.assertEqual(r.status_code, 201, r.content)

    # -- each section, only its subject and only that unit --------------------------------
    def test_every_section_shows_only_its_unit(self):
        self.preventive()
        self.preventive(unit=self.other)
        self.make_report(self.unit)
        self.o2.post_json("/api/reportes-fallas/", {"unit_id": self.other["id"], "date": today(), "location": "x", "description": "otra"})
        self.checklist(self.o, self.unit)
        self.checklist(self.o2, self.other)
        for name in ("mantenimientos", "fallas", "checklists"):
            self.assertEqual(self.total(name), 1, name)
            self.assertEqual(self.section(name, unit=self.other)["pagination"]["total"], 1, name)
        people = self.section("operadores")["people"]
        self.assertEqual([p["person"] for p in people], ["O1 Prueba Test (O1)"])

    def test_an_unknown_unit_is_404(self):
        for name in ("mantenimientos", "fallas", "checklists", "refacciones", "operadores", "cambios", "linea-de-tiempo"):
            self.assertEqual(self.g.get(f"/api/kardex/99999/{name}/").status_code, 404, name)

    # -- maintenances ---------------------------------------------------------------------
    def test_maintenances_filter_by_type_repair_dates_and_text(self):
        self.preventive(date=days_ago(40), observations="Cambio de aceite sintético")
        self.corrective(completed=True)
        self.corrective(completed=False)
        self.assertEqual(self.total("mantenimientos"), 3)
        self.assertEqual(self.total("mantenimientos", tipo="preventivo"), 1)
        self.assertEqual(self.total("mantenimientos", tipo="correctivo"), 2)
        self.assertEqual(self.total("mantenimientos", terminada="si"), 1)
        self.assertEqual(self.total("mantenimientos", terminada="no"), 1)  # a preventive one is not "unfinished"
        self.assertEqual(self.total("mantenimientos", date_to=days_ago(30)), 1)
        self.assertEqual(self.total("mantenimientos", date_from=days_ago(30)), 2)
        self.assertEqual(self.total("mantenimientos", q="sintético"), 1)
        self.assertEqual(self.total("mantenimientos", q="frenos"), 2)  # the cause of the diagnosis

    def test_maintenances_are_newest_first_ordered_and_paged(self):
        for days, cost in ((3, "50"), (1, "10"), (2, "90")):
            self.preventive(date=days_ago(days), cost=cost)
        rows = self.section("mantenimientos")["maintenances"]
        self.assertEqual([r["date"] for r in rows], [days_ago(1), days_ago(2), days_ago(3)])
        rows = self.section("mantenimientos", order="-cost")["maintenances"]
        self.assertEqual([r["cost"] for r in rows], ["90.00", "50.00", "10.00"])
        page = self.section("mantenimientos", page_size=2, page=2)
        self.assertEqual(page["pagination"], {"page": 2, "pages": 2, "page_size": 2, "total": 3})
        self.assertEqual([r["date"] for r in page["maintenances"]], [days_ago(3)])

    def test_maintenances_do_not_query_once_per_row(self):
        self.corrective(completed=True)

        def queries():
            with CaptureQueriesContext(connection) as context:
                self.section("mantenimientos")
            return len(context.captured_queries)

        few = queries()
        for _ in range(3):
            self.corrective(completed=False)
        self.assertEqual(queries(), few)

    # -- faults, checklists, people, timeline ---------------------------------------------
    def test_faults_filter_by_status(self):
        self.corrective(completed=True)  # Reparado
        self.make_report(self.unit)  # Pendiente
        data = self.section("fallas")
        statuses = {s["label"]: s["id"] for s in data["statuses"]}
        self.assertEqual(self.total("fallas", estatus=statuses["Pendiente"]), 1)
        self.assertEqual(self.total("fallas", estatus=statuses["Reparado"]), 1)
        repaired = self.section("fallas", estatus=statuses["Reparado"])["faults"][0]
        self.assertEqual(repaired["diagnosis"]["cause"], "Frenos")
        self.assertIsNone(self.section("fallas", estatus=statuses["Pendiente"])["faults"][0]["diagnosis"])

    def test_checklists_say_what_failed(self):
        self.checklist(self.o, self.unit)
        self.checklist(self.o, self.unit, lights=False)
        self.assertEqual(self.total("checklists", resultado="ok"), 1)
        (bad,) = self.section("checklists", resultado="fallas")["checklists"]
        self.assertFalse(bad["ok"])
        self.assertEqual(bad["failed_items"], ["Luces"])
        self.assertIn("(O1)", bad["operator"])

    def test_people_has_operators_and_mechanics(self):
        report = self.corrective(completed=False)
        people = self.section("operadores")["people"]
        self.assertEqual(sorted(p["role"] for p in people), ["Mecánico", "Operador"])
        (mechanic,) = self.section("operadores", rol="mecanico")["people"]
        self.assertEqual(mechanic["report"]["id"], report["id"])
        self.assertEqual(self.total("operadores", rol="operador"), 1)
        self.assertEqual(self.total("operadores", q="M1"), 1)
        self.assertEqual(self.total("operadores", date_to=days_ago(1)), 0)  # both started today

    def test_the_timeline_filters_by_type(self):
        self.preventive()
        self.make_report(self.unit)
        data = self.section("linea-de-tiempo")
        types = {e["type"] for e in data["events"]}
        self.assertTrue({"maintenance", "report", "operator", "plate"} <= types)
        self.assertIn({"id": "maintenance", "label": "Mantenimiento"}, data["types"])
        only = self.section("linea-de-tiempo", tipo="maintenance")["events"]
        self.assertEqual([e["type_label"] for e in only], ["Mantenimiento"])
        for e in data["events"]:
            self.assertNotIn("\n", e["detail"])  # one line each

    # -- PDF --------------------------------------------------------------------------------
    def test_each_section_and_the_whole_kardex_make_a_pdf(self):
        self.corrective(completed=True)
        self.checklist(self.o, self.unit)
        long_text = "Observación muy larga & con <símbolos> " * 80
        self.preventive(observations=long_text)
        for name in ("mantenimientos", "fallas", "checklists", "refacciones", "operadores", "cambios", "linea-de-tiempo"):
            r = self.g.get(f"/api/kardex/{self.unit['id']}/{name}/?format=pdf&q=a")
            self.assertEqual(r.status_code, 200, name)
            self.assertTrue(r.content.startswith(b"%PDF-"), name)
            self.assertIn(".pdf", r["Content-Disposition"])
        r = self.g.get(f"/api/kardex/{self.unit['id']}/?format=pdf")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF-"))
