"""
Exclusive operator assignment with history: a unit has at most one operator with an open
assignment, and an operator at most one open unit. Ending sets an end date (rows are kept), a
change of operator ends and opens in one transaction, and only the operator who has the unit open
can report its failures or check it.
"""

import datetime
import importlib
from unittest import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from accounts.roles import OPERATOR_ROLE
from audit.models import AuditLog
from fleet.admin import UnitOperatorAdmin
from fleet.models import Unit, UnitOperator

from .base import ApiTestCase, make_user, today

data_migration = importlib.import_module("fleet.migrations.0046_operador_exclusivo_datos")


def days_ago(n):
    return (datetime.date.fromisoformat(today()) - datetime.timedelta(days=n)).isoformat()


class ExclusiveAssignmentApiTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.operator3 = make_user("O3", OPERATOR_ROLE)
        self.unit = self.make_unit("EX-1")  # O1 has it
        self.free_unit = self.make_unit("EX-2", operator=None)

    def open_rows(self, **filters):
        return UnitOperator.objects.filter(end_date__isnull=True, **filters)

    # -- a second open assignment ---------------------------------------------------------
    def test_a_unit_with_an_operator_cannot_get_a_second_one(self):
        r = self.change_operator(self.unit["id"], new_operator=self.operator2)
        self.assertEqual(r.status_code, 400)
        (message,) = r.json()["errors"]["operator"]
        self.assertIn("La unidad EX-1 ya está asignada a", message)
        self.assertIn("(O1)", message)
        self.assertIn("Primero termina esa asignación", message)
        self.assertEqual(self.open_rows(unit_id=self.unit["id"]).count(), 1)

    def test_validation_only_says_the_same_and_saves_nothing(self):
        r = self.change_operator(self.unit["id"], new_operator=self.operator2, validate=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("ya está asignada", r.json()["errors"]["operator"][0])
        self.assertFalse(self.open_rows(operator=self.operator2).exists())

    def test_an_operator_with_a_unit_cannot_get_another_one(self):
        r = self.change_operator(self.free_unit["id"], new_operator=self.operator)
        self.assertEqual(r.status_code, 400)
        (message,) = r.json()["errors"]["operator"]
        self.assertIn("(O1) ya tiene asignada la unidad EX-1", message)
        self.assertFalse(self.open_rows(unit_id=self.free_unit["id"]).exists())

    def test_a_new_unit_cannot_take_an_operator_who_has_another(self):
        r = self.g.post_json("/api/unidades/", {
            "economic_number": "EX-3", "unit_model_id": Unit.objects.get(pk=self.unit["id"]).unit_model_id,
            "mileage": "10", "plate": {"identifier": "PLEX3", "state": "Coahuila de Zaragoza", "start_date": today()},
            "new_operator": {"operator_id": self.operator.pk, "start_date": today()},
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn("ya tiene asignada la unidad EX-1", r.json()["errors"]["operator"][0])
        self.assertFalse(Unit.objects.filter(economic_number="EX-3").exists())

    def test_a_free_operator_on_a_free_unit_is_fine(self):
        r = self.change_operator(self.free_unit["id"], new_operator=self.operator2)
        self.assertEqual(r.status_code, 200, r.content)
        current = r.json()["unit"]["current_operator"]
        self.assertEqual(current["operator"]["id"], self.operator2.pk)
        self.assertIsNone(current["end_date"])

    # -- ending -----------------------------------------------------------------------------
    def test_ending_sets_the_end_date_and_keeps_the_row(self):
        r = self.change_operator(self.unit["id"], end_date=today())
        self.assertEqual(r.status_code, 200, r.content)
        unit = r.json()["unit"]
        self.assertIsNone(unit["current_operator"])
        (row,) = unit["operators"]
        self.assertEqual(row["end_date"], today())
        self.assertEqual(UnitOperator.objects.filter(unit_id=self.unit["id"]).count(), 1)

    def test_ending_with_wrong_dates_fails(self):
        tomorrow = (datetime.date.fromisoformat(today()) + datetime.timedelta(days=1)).isoformat()
        cases = {
            tomorrow: "no puede ser futura",
            days_ago(1): "no puede ser anterior al inicio",  # it started today
            "no-es-fecha": "fecha de fin válida",
        }
        for end_date, expected in cases.items():
            r = self.change_operator(self.unit["id"], end_date=end_date)
            self.assertEqual(r.status_code, 400, end_date)
            self.assertIn(expected, r.json()["errors"]["operator"][0], end_date)
        self.assertEqual(self.open_rows(unit_id=self.unit["id"]).count(), 1)

    def test_an_assignment_that_already_ended_cannot_be_ended_again(self):
        assignment_id = self.g.get_json(f"/api/unidades/{self.unit['id']}/").json()["unit"]["current_operator"]["id"]
        self.assertEqual(self.change_operator(self.unit["id"], end_date=today()).status_code, 200)
        unit = self.g.get_json(f"/api/unidades/{self.unit['id']}/").json()["unit"]
        r = self.g.put_json(f"/api/unidades/{self.unit['id']}/", {
            "economic_number": unit["economic_number"], "unit_model_id": unit["unit_model"]["id"],
            "mileage": str(unit["mileage"]), "end_operator": {"assignment_id": assignment_id, "end_date": today()},
        })
        self.assertEqual(r.status_code, 400)
        self.assertIn("no existe o ya terminó", r.json()["errors"]["operator"][0])

    # -- change of operator -------------------------------------------------------------------
    def test_a_change_of_operator_ends_the_old_one_and_opens_the_new_one(self):
        r = self.change_operator(self.unit["id"], end_date=today(), new_operator=self.operator2)
        self.assertEqual(r.status_code, 200, r.content)
        unit = r.json()["unit"]
        self.assertEqual(unit["current_operator"]["operator"]["id"], self.operator2.pk)
        old = UnitOperator.objects.get(unit_id=self.unit["id"], operator=self.operator)
        self.assertEqual(old.end_date.isoformat(), today())
        self.assertEqual(self.open_rows(unit_id=self.unit["id"]).get().operator, self.operator2)
        # the old operator is free again
        self.assertEqual(self.change_operator(self.free_unit["id"], new_operator=self.operator).status_code, 200)

    def test_a_change_of_operator_is_all_or_nothing(self):
        with mock.patch.object(UnitOperator.objects, "create", side_effect=IntegrityError("simulada")):
            r = self.change_operator(self.unit["id"], end_date=today(), new_operator=self.operator2)
        self.assertEqual(r.status_code, 400)
        self.assertIn("operator", r.json()["errors"])
        # the end of the old assignment was rolled back with it
        self.assertEqual(self.open_rows(unit_id=self.unit["id"]).get().operator, self.operator)

    def test_the_new_operator_cannot_start_before_the_old_one_ends(self):
        UnitOperator.objects.filter(unit_id=self.unit["id"]).update(start_date=days_ago(10))
        r = self.change_operator(
            self.unit["id"], end_date=days_ago(2), new_operator=self.operator2, start_date=days_ago(5)
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("no puede empezar antes de que termine el anterior", r.json()["errors"]["operator"][0])

    def test_the_new_operator_must_still_be_free(self):
        self.change_operator(self.free_unit["id"], new_operator=self.operator2)
        r = self.change_operator(self.unit["id"], end_date=today(), new_operator=self.operator2)
        self.assertEqual(r.status_code, 400)
        self.assertIn("(O2) ya tiene asignada la unidad EX-2", r.json()["errors"]["operator"][0])
        self.assertEqual(self.open_rows(unit_id=self.unit["id"]).get().operator, self.operator)

    # -- deactivating -----------------------------------------------------------------------
    def test_a_unit_with_an_operator_cannot_be_deactivated(self):
        unit = self.g.get_json(f"/api/unidades/{self.unit['id']}/").json()["unit"]
        data = {"economic_number": "EX-1", "unit_model_id": unit["unit_model"]["id"], "mileage": "1000", "is_active": False}
        r = self.g.put_json(f"/api/unidades/{self.unit['id']}/", data)
        self.assertEqual(r.status_code, 400)
        self.assertIn("Quita primero al operador", r.json()["errors"]["is_active"][0])
        # ending the assignment in the same save is enough
        data["end_operator"] = {"assignment_id": unit["current_operator"]["id"], "end_date": today()}
        self.assertEqual(self.g.put_json(f"/api/unidades/{self.unit['id']}/", data).status_code, 200)

    # -- form options -------------------------------------------------------------------------
    def test_the_form_offers_only_operators_without_a_unit_plus_the_current_one(self):
        def offered(**params):
            options = self.g.get_json("/api/unidades/catalogos/", **params).json()["operators"]
            return {o["id"]: o["current"] for o in options}

        self.assertEqual(offered(), {self.operator2.pk: False, self.operator3.pk: False})
        self.assertEqual(
            offered(unidad=self.unit["id"]),
            {self.operator.pk: True, self.operator2.pk: False, self.operator3.pk: False},
        )

    # -- audit log ----------------------------------------------------------------------------
    def test_the_change_of_operator_goes_into_the_audit_log(self):
        before = AuditLog.objects.filter(table_name="unidades_operadores").count()
        self.change_operator(self.unit["id"], end_date=today(), new_operator=self.operator2)
        lines = AuditLog.objects.filter(table_name="unidades_operadores").order_by("id")[before:]
        self.assertEqual([line.action for line in lines], [AuditLog.UPDATE, AuditLog.CREATE])
        self.assertIn("fin", " ".join(lines[0].changes).lower())


class ReportingNeedsTheOpenAssignmentTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = self.make_unit("RP-1")  # O1 has it
        self.o2 = self.client_for(self.operator2)

    def report(self, client):
        return client.post_json(
            "/api/reportes-fallas/",
            {"unit_id": self.unit["id"], "date": today(), "location": "x", "description": "y"},
        )

    def report_units(self, client):
        return [u["id"] for u in client.get_json("/api/reportes-fallas/catalogos/").json()["units"]]

    def test_an_operator_without_an_open_assignment_cannot_report(self):
        r = self.report(self.o2)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["errors"]["unit_id"], ["Esa unidad no está asignada a ti."])
        self.assertEqual(self.report_units(self.o2), [])

    def test_after_a_change_of_operator_only_the_new_one_can_report(self):
        self.assertEqual(self.report(self.o).status_code, 201)
        self.change_operator(self.unit["id"], end_date=today(), new_operator=self.operator2)
        r = self.report(self.o)  # the assignment of O1 is closed now
        self.assertEqual(r.status_code, 400)
        self.assertIn("unit_id", r.json()["errors"])
        self.assertEqual(self.report_units(self.o), [])
        self.assertEqual(self.report(self.o2).status_code, 201)
        self.assertEqual(self.report_units(self.o2), [self.unit["id"]])

    def test_the_old_operator_can_still_correct_a_pending_report_of_that_unit(self):
        created = self.report(self.o).json()["report"]
        self.change_operator(self.unit["id"], end_date=today())
        r = self.o.put_json(f"/api/reportes-fallas/{created['id']}/", {
            "unit_id": self.unit["id"], "date": today(), "location": "x", "description": "corregida",
        })
        self.assertEqual(r.status_code, 200, r.content)  # past records are not rewritten

    def test_checklists_follow_the_same_rule(self):
        self.change_operator(self.unit["id"], end_date=today(), new_operator=self.operator2)
        data = {
            "unit_id": self.unit["id"], "date": today(), "recorded_mileage": "1200", "tire_pressure": "32",
            "tire_tread_depth": "8", "lights_ok": True, "fluids_ok": True, "no_cracks": True,
            "trip_description": "Salida",
        }
        self.assertEqual(self.o.post_json("/api/checklists/", data).status_code, 400)
        self.assertEqual(self.o2.post_json("/api/checklists/", data).status_code, 201)
        self.assertEqual(self.o.get_json("/api/checklists/catalogos/").json()["units"], [])


class KardexOperatorHistoryTest(ApiTestCase):
    def test_the_kardex_shows_who_had_the_unit_and_when(self):
        unit = self.make_unit("KO-1")
        UnitOperator.objects.filter(unit_id=unit["id"]).update(start_date=days_ago(10))
        self.change_operator(unit["id"], end_date=today(), new_operator=self.operator2)
        events = self.g.get_json(f"/api/kardex/{unit['id']}/linea-de-tiempo/", tipo="operator").json()["events"]
        self.assertEqual(
            [(e["date"], e["title"]) for e in events],
            [
                (today(), "Asignada a O2 Prueba Test (O2)"),  # the one who arrives, above
                (today(), "Operador O1 Prueba Test (O1) dejó la unidad"),
                (days_ago(10), "Asignada a O1 Prueba Test (O1)"),
            ],
        )
        self.assertEqual(events[1]["detail"], f"Desde {days_ago(10)} hasta {today()}.")
        self.assertEqual(events[0]["detail"], f"Desde {today()} (actual).")
        # and the section «Operadores y mecánicos» has the periods in columns
        people = self.g.get_json(f"/api/kardex/{unit['id']}/operadores/", rol="operador").json()["people"]
        self.assertEqual(
            [(p["person"], p["start_date"], p["end_date"]) for p in people],
            [("O2 Prueba Test (O2)", today(), None), ("O1 Prueba Test (O1)", days_ago(10), today())],
        )
        # the PDF of the kardex is still generated
        r = self.g.get(f"/api/kardex/{unit['id']}/?format=pdf")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")


class DatabaseAndAdminRulesTest(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.unit = Unit.objects.get(pk=self.make_unit("DB-1")["id"])  # O1 has it
        self.other = Unit.objects.get(pk=self.make_unit("DB-2", operator=None)["id"])

    def test_the_database_refuses_a_second_open_assignment_for_a_unit(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            UnitOperator.objects.create(unit=self.unit, operator=self.operator2, start_date=today())

    def test_the_database_refuses_a_second_open_unit_for_an_operator(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            UnitOperator.objects.create(unit=self.other, operator=self.operator, start_date=today())

    def test_closed_assignments_do_not_count(self):
        UnitOperator.objects.filter(unit=self.unit).update(end_date=today())
        UnitOperator.objects.create(unit=self.unit, operator=self.operator2, start_date=today())
        UnitOperator.objects.create(unit=self.other, operator=self.operator, start_date=today())

    def test_the_admin_panel_explains_the_same_rules(self):
        second = UnitOperator(unit=self.unit, operator=self.operator2, start_date=datetime.date.fromisoformat(today()))
        with self.assertRaisesMessage(ValidationError, "ya está asignada a"):
            second.full_clean()
        busy = UnitOperator(unit=self.other, operator=self.operator, start_date=datetime.date.fromisoformat(today()))
        with self.assertRaisesMessage(ValidationError, "ya tiene asignada la unidad DB-1"):
            busy.full_clean()
        future = UnitOperator(
            unit=self.other, operator=self.operator2,
            start_date=datetime.date.fromisoformat(today()) + datetime.timedelta(days=1),
        )
        with self.assertRaisesMessage(ValidationError, "no puede ser futura"):
            future.full_clean()
        # editing the open assignment itself is not a conflict with itself
        UnitOperator.objects.get(unit=self.unit).full_clean()

    def test_the_admin_panel_cannot_delete_assignments(self):
        self.assertFalse(UnitOperatorAdmin(UnitOperator, None).has_delete_permission(None))


class DataMigrationTest(ApiTestCase):
    """The data step of the migration, run on duplicates (the constraints are dropped inside the test)."""

    def setUp(self):
        super().setUp()
        self.operator3 = make_user("O3", OPERATOR_ROLE)
        self.unit_a = Unit.objects.get(pk=self.make_unit("MG-1", operator=None)["id"])
        model = self.unit_a.unit_model
        self.unit_b = Unit.objects.create(economic_number="MG-2", unit_model=model, mileage=0)
        self.unit_c = Unit.objects.create(economic_number="MG-3", unit_model=model, mileage=0)
        # Without the new constraints, as a database from before this change
        with connection.schema_editor() as editor:
            for constraint in UnitOperator._meta.constraints:
                if constraint.name in ("un_operador_abierto_por_unidad", "una_unidad_abierta_por_operador"):
                    editor.remove_constraint(UnitOperator, constraint)

    def add(self, unit, operator, start):
        return UnitOperator.objects.create(unit=unit, operator=operator, start_date=days_ago(start))

    def test_it_keeps_the_most_recent_open_and_closes_the_rest_today(self):
        old = self.add(self.unit_a, self.operator, 20)
        new = self.add(self.unit_a, self.operator2, 5)  # the latest start: stays
        many = [self.add(u, self.operator3, d) for u, d in ((self.unit_b, 30), (self.unit_c, 3))]
        closed_before = self.add(self.unit_b, self.operator, 40)
        closed_before.end_date = datetime.date.fromisoformat(days_ago(35))
        closed_before.save()
        rows = UnitOperator.objects.count()
        today_date = datetime.date.fromisoformat(today())

        closed = data_migration.close_duplicate_open_assignments(UnitOperator, today_date)

        self.assertEqual(closed, 2)
        self.assertEqual(UnitOperator.objects.count(), rows)  # no row lost
        for row in (old, new, *many, closed_before):
            row.refresh_from_db()
        self.assertEqual(old.end_date, today_date)
        self.assertIsNone(new.end_date)
        self.assertEqual(many[0].end_date, today_date)  # O3: MG-2 since 30 days, MG-3 since 3
        self.assertIsNone(many[1].end_date)
        self.assertEqual(closed_before.end_date.isoformat(), days_ago(35))  # untouched
        # At most one open per unit and per operator now
        open_rows = UnitOperator.objects.filter(end_date__isnull=True)
        self.assertEqual(len({r.unit_id for r in open_rows}), open_rows.count())
        self.assertEqual(len({r.operator_id for r in open_rows}), open_rows.count())
        # Idempotent
        self.assertEqual(data_migration.close_duplicate_open_assignments(UnitOperator, today_date), 0)

    def test_on_a_tie_the_newest_row_stays_open(self):
        first = self.add(self.unit_a, self.operator, 7)
        second = self.add(self.unit_a, self.operator2, 7)
        data_migration.close_duplicate_open_assignments(UnitOperator, datetime.date.fromisoformat(today()))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertIsNotNone(first.end_date)
        self.assertIsNone(second.end_date)
