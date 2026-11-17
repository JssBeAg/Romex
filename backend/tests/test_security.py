import datetime

from django.conf import settings
from django.utils import timezone

from accounts.models import User
from accounts.security import LOCK_MINUTES, MAX_FAILED_ATTEMPTS
from audit.models import AuditLog
from notifications.models import Notification

from .base import PASSWORD, ApiClient, ApiTestCase


class LoginTest(ApiTestCase):
    def login(self, enrollment_id, password):
        return ApiClient().post_json(
            "/api/auth/login/", {"enrollment_id": enrollment_id, "password": password}
        )

    def test_login_ok_and_wrong_password(self):
        self.assertEqual(self.login("O1", PASSWORD).status_code, 200)
        self.assertEqual(self.login("O1", "mala").status_code, 401)
        self.assertEqual(self.login("NOEXISTE", PASSWORD).status_code, 401)

    def test_lock_after_too_many_failures(self):
        for _ in range(MAX_FAILED_ATTEMPTS):
            self.login("O2", "mala")
        user = User.objects.get(enrollment_id="O2")
        self.assertTrue(user.is_locked)
        # Even the right password is refused while locked
        self.assertEqual(self.login("O2", PASSWORD).status_code, 423)
        delta = user.locked_until - timezone.now()
        self.assertLessEqual(delta, datetime.timedelta(minutes=LOCK_MINUTES))
        self.assertGreater(delta, datetime.timedelta(minutes=LOCK_MINUTES - 1))

    def test_lock_notifies_managers_and_is_audited(self):
        for _ in range(MAX_FAILED_ATTEMPTS):
            self.login("O2", "mala")
        self.assertTrue(
            Notification.objects.filter(user=self.manager, kind=Notification.ACCOUNT_LOCKED).exists()
        )
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.ACCOUNT_LOCKED).exists())

    def test_lock_expires_and_success_resets_counter(self):
        for _ in range(MAX_FAILED_ATTEMPTS):
            self.login("O2", "mala")
        User.objects.filter(enrollment_id="O2").update(
            locked_until=timezone.now() - datetime.timedelta(minutes=1)
        )
        self.assertEqual(self.login("O2", PASSWORD).status_code, 200)
        user = User.objects.get(enrollment_id="O2")
        self.assertEqual(user.failed_attempts, 0)
        self.assertIsNone(user.locked_until)

    def test_documented_limits(self):
        # docs/seguridad.md promises 5 attempts and 15 minutes: change both together
        self.assertEqual(MAX_FAILED_ATTEMPTS, 5)
        self.assertEqual(LOCK_MINUTES, 15)

    def test_fifth_failure_locks_but_fourth_does_not(self):
        for _ in range(4):
            self.login("O2", "mala")
        self.assertFalse(User.objects.get(enrollment_id="O2").is_locked)
        self.login("O2", "mala")
        self.assertTrue(User.objects.get(enrollment_id="O2").is_locked)

    def test_few_failures_do_not_lock(self):
        for _ in range(MAX_FAILED_ATTEMPTS - 1):
            self.login("O2", "mala")
        self.assertEqual(self.login("O2", PASSWORD).status_code, 200)

    def test_session_expires_after_inactivity(self):
        self.assertEqual(settings.SESSION_COOKIE_AGE, 8 * 60 * 60)
        self.assertTrue(settings.SESSION_SAVE_EVERY_REQUEST)


class ChangePasswordTest(ApiTestCase):
    URL = "/api/auth/cambiar-contrasena/"

    def payload(self, **over):
        data = {"current_password": PASSWORD, "new_password": "NuevaClave9871z", "confirm_password": "NuevaClave9871z"}
        data.update(over)
        return data

    def test_wrong_current_password(self):
        r = self.o.post_json(self.URL, self.payload(current_password="otra"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("current_password", r.json()["errors"])

    def test_confirmation_must_match(self):
        r = self.o.post_json(self.URL, self.payload(confirm_password="distinta"))
        self.assertEqual(r.status_code, 400)

    def test_weak_and_reused_passwords_are_refused(self):
        for bad in ("12345678", "abc", PASSWORD, "O1"):
            r = self.o.post_json(self.URL, self.payload(new_password=bad, confirm_password=bad))
            self.assertEqual(r.status_code, 400, bad)

    def test_validation_only_does_not_change_anything(self):
        r = self.o.post_json(self.URL + "?validar=1", self.payload())
        self.assertEqual(r.json()["errors"], {})
        self.assertTrue(User.objects.get(enrollment_id="O1").check_password(PASSWORD))

    def test_change_works_and_is_audited(self):
        r = self.o.post_json(self.URL, self.payload())
        self.assertEqual(r.status_code, 200)
        user = User.objects.get(enrollment_id="O1")
        self.assertTrue(user.check_password("NuevaClave9871z"))
        self.assertFalse(user.must_change_password)
        self.assertTrue(AuditLog.objects.filter(action=AuditLog.PASSWORD_CHANGED).exists())
        # The session stays open
        self.assertEqual(self.o.get("/api/auth/me/").status_code, 200)

    def test_forced_change_blocks_the_api_until_done(self):
        User.objects.filter(enrollment_id="O1").update(must_change_password=True)
        r = self.o.get("/api/reportes-fallas/")
        self.assertEqual(r.status_code, 403)
        self.assertTrue(r.json()["must_change_password"])
        # /api/auth/ keeps working
        self.assertTrue(self.o.get("/api/auth/me/").json()["user"]["must_change_password"])
        self.assertEqual(self.o.post_json(self.URL, self.payload()).status_code, 200)
        self.assertEqual(self.o.get("/api/reportes-fallas/").status_code, 200)

    def worker_payload(self, **over):
        from accounts.models import PhoneCode, Sex

        roles = {r["label"]: r["id"] for r in self.g.get("/api/trabajadores/catalogos/").json()["roles"]}
        data = {
            "enrollment_id": "N1", "first_name": "Nuevo", "paternal_surname": "P", "maternal_surname": "M",
            "email": "n1@example.com", "phone_code_id": PhoneCode.objects.get(iso="MX").pk, "phone_number": "8441112233", "sex_id": Sex.objects.first().pk,
            "role_id": roles["Operador"], "is_active": True, "password": "Temporal12345x",
            "address": {"state": "Coahuila de Zaragoza", "municipality": "Saltillo", "neighborhood": "Centro", "street": "Calle Uno", "exterior_number": "5", "interior_number": ""},
        }
        data.update(over)
        return data

    def test_manager_created_worker_must_change_password(self):
        r = self.g.post_json("/api/trabajadores/", self.worker_payload())
        self.assertEqual(r.status_code, 201, r.content)
        self.assertTrue(User.objects.get(enrollment_id="N1").must_change_password)

    def test_password_reset_forces_change_and_saving_unlocks(self):
        user = self.operator2
        for _ in range(MAX_FAILED_ATTEMPTS):
            ApiClient().post_json("/api/auth/login/", {"enrollment_id": "O2", "password": "mala"})
        self.assertTrue(User.objects.get(pk=user.pk).is_locked)
        payload = self.worker_payload(enrollment_id="O2", first_name="O2", password="Otra12345xyz", email="o2@example.com")
        r = self.g.put_json(f"/api/trabajadores/{user.pk}/", payload)
        self.assertEqual(r.status_code, 200, r.content)
        fresh = User.objects.get(pk=user.pk)
        self.assertFalse(fresh.is_locked)
        self.assertTrue(fresh.must_change_password)
        self.assertTrue(fresh.check_password("Otra12345xyz"))
