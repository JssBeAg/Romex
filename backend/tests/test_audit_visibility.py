"""What the manager sees in the audit trail (not the administrators' sessions) and the admin panel's plain dropdowns."""

import re

from accounts.models import PhoneCode, User
from accounts.security import MAX_FAILED_ATTEMPTS
from audit.models import AuditLog
from notifications.models import Notification

from .base import PASSWORD, ApiClient, ApiTestCase


class AuditVisibilityTest(ApiTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = User.objects.create_superuser(
            "ADM1", PASSWORD, first_name="Ada", paternal_surname="Admin", maternal_surname="Sistema"
        )

    def visible(self, **params):
        return self.g.get_json("/api/bitacora/", page_size=100, **params).json()

    def seen_actions(self, enrollment_id):
        data = self.visible(q=enrollment_id)
        return {e["action"] for e in data["entries"] if e["enrollment_id"] == enrollment_id}

    def admin_session(self):
        c = ApiClient()
        self.assertEqual(c.post_json("/api/auth/login/", {"enrollment_id": "ADM1", "password": PASSWORD}).status_code, 200)
        c.post_json("/api/auth/logout/")

    # -- administrator sessions are hidden ------------------------------------------------
    def test_admin_login_and_logout_are_recorded_but_hidden_from_the_manager(self):
        self.admin_session()
        stored = set(AuditLog.objects.filter(user_enrollment_id="ADM1").values_list("action", flat=True))
        self.assertTrue({AuditLog.LOGIN, AuditLog.LOGOUT} <= stored)  # still in the database
        self.assertEqual(self.seen_actions("ADM1"), set())
        self.assertEqual(self.visible(user_id=self.admin.pk)["total"], 0)

    def test_failed_logins_on_an_admin_matricula_are_hidden_but_other_failures_are_not(self):
        ApiClient().post_json("/api/auth/login/", {"enrollment_id": "ADM1", "password": "mala"})
        ApiClient().post_json("/api/auth/login/", {"enrollment_id": "NOEXISTE", "password": "mala"})
        self.assertEqual(self.seen_actions("ADM1"), set())
        self.assertEqual(self.seen_actions("NOEXISTE"), {AuditLog.LOGIN_FAILED})

    def test_admin_lock_is_hidden_and_does_not_notify_managers(self):
        for _ in range(MAX_FAILED_ATTEMPTS):
            ApiClient().post_json("/api/auth/login/", {"enrollment_id": "ADM1", "password": "mala"})
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ACCOUNT_LOCKED, user_enrollment_id="ADM1").exists())
        self.assertEqual(self.seen_actions("ADM1"), set())
        self.assertFalse(Notification.objects.filter(kind=Notification.ACCOUNT_LOCKED).exists())

    def test_worker_lock_still_notifies_and_is_visible(self):
        for _ in range(MAX_FAILED_ATTEMPTS):
            ApiClient().post_json("/api/auth/login/", {"enrollment_id": "O1", "password": "mala"})
        self.assertIn(AuditLog.ACCOUNT_LOCKED, self.seen_actions("O1"))
        self.assertTrue(Notification.objects.filter(kind=Notification.ACCOUNT_LOCKED, user=self.manager).exists())

    def test_admin_password_change_and_exports_are_hidden(self):
        AuditLog.objects.create(action=AuditLog.PASSWORD_CHANGED, user=self.admin, user_enrollment_id="ADM1", user_role="Administrador")
        AuditLog.objects.create(action=AuditLog.EXPORT, user=self.admin, user_enrollment_id="ADM1", record="Trabajadores")
        self.assertEqual(self.seen_actions("ADM1"), set())

    def test_workers_and_managers_sessions_stay_visible(self):
        c = ApiClient()
        c.post_json("/api/auth/login/", {"enrollment_id": "O1", "password": PASSWORD})
        c.post_json("/api/auth/logout/")
        self.assertTrue({AuditLog.LOGIN, AuditLog.LOGOUT} <= self.seen_actions("O1"))
        self.assertIn(AuditLog.LOGIN, self.seen_actions("G1"))  # the manager's own login (the test client's)

    # -- what the administrator changes in the operation stays visible ---------------------
    def test_admin_changes_on_operation_data_are_still_shown(self):
        AuditLog.objects.create(
            action=AuditLog.UPDATE, user=self.admin, user_enrollment_id="ADM1", user_role="Administrador",
            table_name="unidades", record_id=1, record="E-1", changes={"Kilometraje": ["1", "2"]},
        )
        self.assertEqual(self.seen_actions("ADM1"), {AuditLog.UPDATE})

    # -- the administrator accounts and admin-only tables ----------------------------------
    def test_changes_to_an_admin_account_are_hidden_but_those_of_workers_are_shown(self):
        User.objects.filter(pk=self.admin.pk).first()
        admin = User.objects.get(pk=self.admin.pk)
        admin.first_name = "Cambiada"
        admin.save()
        self.assertTrue(AuditLog.objects.filter(table_name="usuarios", record_id=self.admin.pk).exists())
        operator = User.objects.get(pk=self.operator.pk)
        operator.first_name = "Distinto"
        operator.save()
        data = self.visible(table="usuarios")
        ids = {e["record_id"] for e in data["entries"]}
        self.assertNotIn(self.admin.pk, ids)
        self.assertIn(self.operator.pk, ids)

    def test_phone_code_catalog_changes_are_admin_only(self):
        code = PhoneCode.objects.get(iso="JP")
        code.is_active = True
        code.save()
        self.assertTrue(AuditLog.objects.filter(table_name="codigos_telefonicos").exists())
        self.assertEqual(self.visible(table="codigos_telefonicos")["total"], 0)
        self.assertNotIn("codigos_telefonicos", {t["id"] for t in self.g.get_json("/api/bitacora/catalogos/").json()["tables"]})

    def test_filter_options_do_not_list_administrators(self):
        self.admin_session()
        AuditLog.objects.create(action=AuditLog.UPDATE, user=self.admin, user_enrollment_id="ADM1", table_name="unidades", record="E-1")
        labels = [u["label"] for u in self.g.get_json("/api/bitacora/catalogos/").json()["users"]]
        self.assertFalse(any("ADM1" in label for label in labels), labels)
        self.assertTrue(any("G1" in label for label in labels), labels)

    def test_pdf_and_still_manager_only(self):
        self.admin_session()
        self.assertEqual(self.g.get_json("/api/bitacora/", format="pdf").status_code, 200)
        self.assertEqual(self.o.get("/api/bitacora/").status_code, 403)

    def test_the_administrator_still_sees_everything_in_the_admin_panel(self):
        self.admin_session()
        c = ApiClient()
        c.force_login(self.admin)
        page = c.get("/admin/audit/auditlog/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("ADM1", page.content.decode())


class AdminPanelWidgetsTest(ApiTestCase):
    """The phone-code dropdown is a plain one: no add / change / delete / view buttons beside it."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.admin = User.objects.create_superuser(
            "ADM2", PASSWORD, first_name="Ada", paternal_surname="Admin", maternal_surname="Sistema"
        )

    def page(self, path):
        c = ApiClient()
        c.force_login(self.admin)
        r = c.get(path)
        self.assertEqual(r.status_code, 200, path)
        return r.content.decode()

    def related_buttons(self, html, field):
        return re.findall(rf"(?:add|change|delete|view)_id_[\w-]*{field}", html)

    def test_add_user_page_has_no_buttons_beside_the_phone_code(self):
        html = self.page("/admin/accounts/user/add/")
        self.assertIn('name="phone_code"', html)  # the dropdown is there
        self.assertEqual(self.related_buttons(html, "phone_code"), [])

    def test_edit_user_page_and_the_contacts_have_none_either(self):
        html = self.page(f"/admin/accounts/user/{self.operator.pk}/change/")
        self.assertIn('name="phone_code"', html)
        self.assertIn("contacts-__prefix__-phone_code", html)  # the contacts' dropdown (inline)
        self.assertEqual(self.related_buttons(html, "phone_code"), [])

    def test_the_role_has_no_view_button_either(self):
        for url in ("/admin/accounts/user/add/",):
            html = self.page(url)
            self.assertNotIn("view_id_role", html)
            self.assertNotIn("add_id_role", html)
            self.assertEqual(self.related_buttons(html, "role"), [])

    def test_new_user_starts_with_mexico_plus_52_chosen(self):
        from accounts.models import PhoneCode

        html = self.page("/admin/accounts/user/add/")
        mexico = PhoneCode.objects.get(iso="MX")
        self.assertRegex(html, rf'<option value="{mexico.pk}" selected>')

    def test_the_address_of_the_admin_form_has_text_colonia_and_street(self):
        html = self.page("/admin/accounts/user/add/")
        self.assertRegex(html, r'<input type="text" name="neighborhood"')
        self.assertRegex(html, r'<input type="text" name="street"')
        self.assertNotIn('<select name="neighborhood"', html)
        self.assertNotIn('<select name="street"', html)

    def test_admin_saves_a_user_with_text_colonia_and_street(self):
        from accounts.models import PhoneCode, Sex
        from django.contrib.auth.models import Group
        c = ApiClient()
        c.force_login(self.admin)
        r = c.post("/admin/accounts/user/add/", {
            "enrollment_id": "ADM-T1", "first_name": "Ana", "paternal_surname": "P", "maternal_surname": "M",
            "email": "adm-t1@example.com", "phone_code": PhoneCode.objects.get(iso="MX").pk,
            "phone_number": "8441234567", "sex": Sex.objects.first().pk,
            "role": Group.objects.exclude(name="Administrador").first().pk,
            "password1": "Clave12345xyz", "password2": "Clave12345xyz",
            "state": "Jalisco", "municipality": "Zapopan",
            "neighborhood": "Colonia libre", "street": "Calle libre", "exterior_number": "9",
            "interior_number": "",
            "contacts-TOTAL_FORMS": "0", "contacts-INITIAL_FORMS": "0",
            "contacts-MIN_NUM_FORMS": "0", "contacts-MAX_NUM_FORMS": "3",
        })
        self.assertEqual(r.status_code, 302, r.content.decode()[:3000])
        user = User.objects.get(enrollment_id="ADM-T1")
        self.assertEqual(
            (user.address.state, user.address.municipality, user.address.neighborhood, user.address.street),
            ("Jalisco", "Zapopan", "Colonia libre", "Calle libre"),
        )
