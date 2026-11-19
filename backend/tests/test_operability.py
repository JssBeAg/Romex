"""A unit that is not fit to operate does not appear in the checklist form and takes no new checklist."""

from .base import ApiTestCase, today


class OperabilityTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = self.make_unit("OP-1")  # of O1
        self.other = self.make_unit("OP-2", operator=self.operator2)  # an operator has one unit at most
        self.o2 = self.client_for(self.operator2)
        self.report = self.make_report(self.unit)
        r = self.g.post_json(
            f"/api/reportes-fallas/{self.report['id']}/mecanicos/",
            {"mechanic_id": self.mechanic.pk, "start_date": today()},
        )
        self.assertEqual(r.status_code, 201, r.content)

    # -- helpers --------------------------------------------------------------------------
    def diagnose(self, operable, requires_repair=True):
        r = self.m.post_json("/api/diagnosticos/", {
            "fault_report_id": self.report["id"], "severity_id": 2, "date": today(),
            "detailed_cause": "Balatas", "requires_repair": requires_repair, "unit_operable": operable,
        })
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["diagnosis"]["id"]

    def maintenance(self, diagnosis_id, completed=False):
        r = self.m.post_json("/api/mantenimientos/", {
            "service_type_id": 2, "diagnosis_id": diagnosis_id, "service_mileage": "1500", "total_cost": "100",
            "date": today(), "observations": "", "operator_ids": [], "spare_parts": [],
            "repair_completed": completed,
        })
        self.assertEqual(r.status_code, 201, r.content)

    def checklist_data(self, unit):
        return {
            "unit_id": unit["id"], "date": today(), "recorded_mileage": "1200", "tire_pressure": "32",
            "tire_tread_depth": "8", "lights_ok": True, "fluids_ok": True, "no_cracks": True,
            "trip_description": "Salida a ruta",
        }

    def catalog(self, client=None):
        return (client or self.o).get_json("/api/checklists/catalogos/").json()

    def labels(self, units):
        return sorted(u["label"].split(" ")[0] for u in units)

    # -- tests ----------------------------------------------------------------------------
    def test_the_assigned_unit_is_offered_while_nothing_is_wrong(self):
        data = self.catalog()
        self.assertEqual([u["id"] for u in data["units"]], [self.unit["id"]])
        self.assertEqual(data["not_operable"], [])
        self.assertEqual(len(self.catalog(self.g)["units"]), 2)  # the manager sees every active unit

    def test_a_unit_diagnosed_as_not_operable_leaves_the_form_and_is_listed_apart(self):
        self.diagnose(operable=False)
        data = self.catalog()
        self.assertEqual(data["units"], [])
        self.assertEqual([u["id"] for u in data["not_operable"]], [self.unit["id"]])
        # the unit of another operator is not affected
        self.assertEqual([u["id"] for u in self.catalog(self.o2)["units"]], [self.other["id"]])

    def test_it_also_leaves_the_form_of_the_manager(self):
        self.diagnose(operable=False)
        data = self.catalog(self.g)
        self.assertNotIn(self.unit["id"], [u["id"] for u in data["units"]])
        self.assertIn(self.unit["id"], [u["id"] for u in data["not_operable"]])

    def test_a_diagnosis_that_says_it_can_operate_does_not_hide_it(self):
        self.diagnose(operable=True)
        self.assertIn(self.unit["id"], [u["id"] for u in self.catalog()["units"]])

    def test_a_checklist_for_it_is_refused_with_a_message(self):
        self.diagnose(operable=False)
        r = self.o.post_json("/api/checklists/", self.checklist_data(self.unit))
        self.assertEqual(r.status_code, 400, r.content)
        self.assertIn("no está apta para operar", r.json()["errors"]["unit_id"][0])
        # validation only (what the form does while typing) says the same and saves nothing
        r = self.o.post_json("/api/checklists/?validar=1", self.checklist_data(self.unit))
        self.assertIn("unit_id", r.json()["errors"])

    def test_another_unit_still_takes_checklists(self):
        self.diagnose(operable=False)
        r = self.o2.post_json("/api/checklists/", self.checklist_data(self.other))
        self.assertEqual(r.status_code, 201, r.content)

    def test_it_is_fit_again_when_the_repair_is_finished(self):
        diagnosis_id = self.diagnose(operable=False)
        self.maintenance(diagnosis_id)  # in repair: still not fit
        self.assertNotIn(self.unit["id"], [u["id"] for u in self.catalog()["units"]])
        self.maintenance(diagnosis_id, completed=True)  # repaired
        self.assertIn(self.unit["id"], [u["id"] for u in self.catalog()["units"]])
        self.assertEqual(self.o.post_json("/api/checklists/", self.checklist_data(self.unit)).status_code, 201)

    def test_it_is_fit_again_when_the_diagnosis_is_deleted_or_corrected(self):
        diagnosis_id = self.diagnose(operable=False)
        self.assertNotIn(self.unit["id"], [u["id"] for u in self.catalog()["units"]])
        self.assertEqual(self.m.delete(f"/api/diagnosticos/{diagnosis_id}/").status_code, 200)
        self.assertIn(self.unit["id"], [u["id"] for u in self.catalog()["units"]])

    def test_an_old_checklist_can_still_be_edited_after_the_unit_stopped_being_fit(self):
        created = self.o.post_json("/api/checklists/", self.checklist_data(self.unit)).json()["checklist"]
        self.diagnose(operable=False)
        data = self.checklist_data(self.unit)
        data["trip_description"] = "Salida a ruta corregida"
        r = self.o.put_json(f"/api/checklists/{created['id']}/", data)
        self.assertEqual(r.status_code, 200, r.content)

    def test_an_old_checklist_cannot_be_moved_to_a_unit_that_is_not_fit(self):
        # O2 checks OP-2, then is moved to OP-1 (which O1 leaves), and OP-1 is found not fit
        created = self.o2.post_json("/api/checklists/", self.checklist_data(self.other)).json()["checklist"]
        self.assertEqual(self.change_operator(self.other["id"], end_date=today()).status_code, 200)
        r = self.change_operator(self.unit["id"], end_date=today(), new_operator=self.operator2)
        self.assertEqual(r.status_code, 200, r.content)
        self.diagnose(operable=False)
        r = self.o2.put_json(f"/api/checklists/{created['id']}/", self.checklist_data(self.unit))
        self.assertEqual(r.status_code, 400)
        self.assertIn("unit_id", r.json()["errors"])
