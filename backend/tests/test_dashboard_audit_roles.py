import json

from audit.models import AuditLog

from .base import PASSWORD, ApiClient, ApiTestCase


class DashboardTest(ApiTestCase):
    def test_manager_gets_all_the_blocks(self):
        data = self.g.get_json("/api/dashboard/", months=6).json()
        for key in ("cards", "monthly", "report_statuses", "top_units_by_cost", "top_units_by_reports",
                    "top_parts", "mechanic_workload", "low_stock"):
            self.assertIn(key, data)
        self.assertEqual(len(data["monthly"]["labels"]), 6)
        for series in ("reports", "preventive", "corrective", "cost"):
            self.assertEqual(len(data["monthly"][series]), 6)

    def test_period_options(self):
        for months, expected in ((3, 3), (12, 12), (99, 6)):
            data = self.g.get_json("/api/dashboard/", months=months).json()
            self.assertEqual(len(data["monthly"]["labels"]), expected, months)

    def test_counts_reflect_the_data(self):
        unit = self.make_unit("D-1")
        self.make_report(unit)
        self.make_part("Escasa", stock=1, min_stock=5)
        text = json.dumps(self.g.get("/api/dashboard/").json())
        self.assertIn("Escasa", text)

    def test_pdf(self):
        r = self.g.get_json("/api/dashboard/", format="pdf", months=3)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content.startswith(b"%PDF"))

    def test_other_roles_are_refused(self):
        self.assertEqual(self.o.get("/api/dashboard/").status_code, 403)
        self.assertEqual(self.m.get("/api/dashboard/").status_code, 403)
        self.assertIn(ApiClient().get("/api/dashboard/").status_code, (401, 403))


class AuditTest(ApiTestCase):
    def test_changes_are_recorded_with_who_and_what(self):
        part = self.make_part("Auditada", stock=2)
        entry = AuditLog.objects.filter(record__contains="Auditada").order_by("id").first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.user_enrollment_id, "G1")
        self.assertEqual(entry.user_role, "Gerente")

        self.g.put_json(f"/api/refacciones/{part['id']}/", {"name": "Auditada", "unit_price": "99", "min_stock": 0})
        changed = AuditLog.objects.filter(record__contains="Auditada").order_by("-id").first()
        self.assertEqual(changed.action, AuditLog.UPDATE)
        # Each change is [previous value, new value]
        pairs = [v for v in changed.changes.values() if "99" in json.dumps(v)]
        self.assertEqual(len(pairs), 1)
        self.assertEqual(len(pairs[0]), 2)

    def test_passwords_never_reach_the_log(self):
        ApiClient().post_json("/api/auth/login/", {"enrollment_id": "O1", "password": PASSWORD})
        self.o.post_json(
            "/api/auth/cambiar-contrasena/",
            {"current_password": PASSWORD, "new_password": "NuevaClave9871z", "confirm_password": "NuevaClave9871z"},
        )
        dump = json.dumps(list(AuditLog.objects.values("changes", "record")), default=str)
        self.assertNotIn(PASSWORD, dump)
        self.assertNotIn("NuevaClave9871z", dump)
        self.assertNotIn("pbkdf2", dump)

    def test_login_and_logout_are_recorded(self):
        c = ApiClient()
        c.post_json("/api/auth/login/", {"enrollment_id": "O1", "password": PASSWORD})
        c.post_json("/api/auth/logout/")
        ApiClient().post_json("/api/auth/login/", {"enrollment_id": "O1", "password": "mala"})
        actions = set(AuditLog.objects.filter(user_enrollment_id="O1").values_list("action", flat=True))
        self.assertTrue({AuditLog.LOGIN, AuditLog.LOGOUT, AuditLog.LOGIN_FAILED} <= actions, actions)

    def test_only_managers_read_the_log_and_it_is_read_only(self):
        self.assertEqual(self.g.get("/api/bitacora/").status_code, 200)
        self.assertEqual(self.o.get("/api/bitacora/").status_code, 403)
        self.assertEqual(self.m.get("/api/bitacora/").status_code, 403)
        self.assertEqual(self.g.delete("/api/bitacora/").status_code, 405)

    def test_filters_and_pagination(self):
        for i in range(3):
            self.make_part(f"Auditoria {i}")
        data = self.g.get_json("/api/bitacora/", action="crear", page_size=2).json()
        self.assertLessEqual(len(data["entries"]), 2)
        self.assertIn("total", data)


class RolesTest(ApiTestCase):
    """Who can reach what."""

    def test_operator_cannot_manage(self):
        for path in ("/api/trabajadores/", "/api/bitacora/", "/api/unidades/", "/api/refacciones/", "/api/preventivo/planes/"):
            self.assertEqual(self.o.get(path).status_code, 403, path)
        self.assertEqual(self.o.post_json("/api/refacciones/", {"name": "x"}).status_code, 403)

    def test_mechanic_cannot_manage_or_report(self):
        for path in ("/api/trabajadores/", "/api/bitacora/"):
            self.assertEqual(self.m.get(path).status_code, 403, path)
        unit = self.make_unit("R-1")
        r = self.m.post_json("/api/reportes-fallas/", {"unit_id": unit["id"], "date": "2026-01-01", "location": "x", "description": "y"})
        self.assertEqual(r.status_code, 403)

    def test_manager_cannot_create_reports(self):
        unit = self.make_unit("R-2")
        r = self.g.post_json("/api/reportes-fallas/", {"unit_id": unit["id"], "date": "2026-01-01", "location": "x", "description": "y"})
        self.assertEqual(r.status_code, 403)

    def test_operator_sees_only_their_own_reports(self):
        unit = self.make_unit("R-3")
        self.make_report(unit)
        o2 = self.client_for(self.operator2)
        self.assertEqual(len(self.o.get("/api/reportes-fallas/").json()["reports"]), 1)
        self.assertEqual(len(o2.get("/api/reportes-fallas/").json()["reports"]), 0)

    def test_anonymous_gets_nothing(self):
        anon = ApiClient()
        for path in ("/api/unidades/", "/api/reportes-fallas/", "/api/auth/me/", "/api/trabajadores/"):
            self.assertIn(anon.get(path).status_code, (401, 403), path)

    def test_health_is_public(self):
        self.assertEqual(ApiClient().get("/api/health/").status_code, 200)

    def test_workers_list_filters(self):
        roles = {r["label"]: r["id"] for r in self.g.get("/api/trabajadores/catalogos/").json()["roles"]}
        data = self.g.get_json("/api/trabajadores/", role_id=roles["Mecánico"]).json()
        self.assertEqual(sorted(w["enrollment_id"] for w in data["workers"]), ["M1", "M2"])
