"""Phone codes and the alternative contacts of a worker (second phone, second email...)."""

from django.db import IntegrityError, transaction

from accounts.contacts import MAX_PHONE_DIGITS, clean_number, default_label
from accounts.models import MAX_CONTACTS, PhoneCode, Sex, User, WorkerContact
from audit.models import AuditLog

from .base import ApiTestCase


def mx():
    return PhoneCode.objects.get(iso="MX")


def us():
    return PhoneCode.objects.get(iso="US")


class PhoneCodeCatalogTest(ApiTestCase):
    def test_world_catalog_is_loaded_with_a_default_subset_active(self):
        self.assertGreater(PhoneCode.objects.count(), 200)
        self.assertTrue(PhoneCode.objects.get(iso="MX").is_active)
        self.assertFalse(PhoneCode.objects.get(iso="JP").is_active)
        self.assertEqual(mx().code, "52")
        self.assertEqual(str(mx()), "México (+52)")

    def test_a_code_can_be_shared_by_several_countries(self):
        self.assertEqual(PhoneCode.objects.filter(code="1").count() > 1, True)
        self.assertEqual(us().code, PhoneCode.objects.get(iso="CA").code)

    def test_catalog_endpoint_only_offers_active_codes_and_the_limit(self):
        data = self.g.get_json("/api/trabajadores/catalogos/").json()
        isos = {c["iso"] for c in data["phone_codes"]}
        self.assertIn("MX", isos)
        self.assertNotIn("JP", isos)
        self.assertEqual(data["max_contacts"], MAX_CONTACTS)
        labels = [c["label"] for c in data["phone_codes"]]
        self.assertIn("México (+52)", labels)

    def test_catalog_is_manager_only(self):
        self.assertEqual(self.o.get_json("/api/trabajadores/catalogos/").status_code, 403)

    def test_code_must_be_digits_in_the_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            PhoneCode.objects.create(iso="ZZ", country_name="Zeta", code="+9")

    def test_deactivating_a_code_does_not_break_workers_that_use_it(self):
        peru = PhoneCode.objects.get(iso="PE")
        self.operator.phone_code = peru
        self.operator.save()
        peru.is_active = False
        peru.save()
        detail = self.g.get_json(f"/api/trabajadores/{self.operator.pk}/").json()["worker"]
        self.assertEqual(detail["phone_code"]["iso"], "PE")
        # Saving the worker again keeps the code it already had...
        r = self.g.put_json(f"/api/trabajadores/{self.operator.pk}/", WorkerContactApiBase.payload_from(detail))
        self.assertEqual(r.status_code, 200, r.content)
        # ...but a worker cannot be moved to an inactive code
        data = WorkerContactApiBase.payload_from(detail)
        data["phone_code_id"] = PhoneCode.objects.get(iso="JP").pk
        r = self.g.put_json(f"/api/trabajadores/{self.operator.pk}/", data)
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone_code_id", r.json()["errors"])

    def test_a_code_in_use_cannot_be_deleted(self):
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            mx().delete()


class WorkerContactApiBase(ApiTestCase):
    @staticmethod
    def payload_from(detail, **over):
        data = {
            "enrollment_id": detail["enrollment_id"],
            "first_name": detail["first_name"],
            "paternal_surname": detail["paternal_surname"],
            "maternal_surname": detail["maternal_surname"],
            "email": detail["email"],
            "phone_code_id": detail["phone_code"]["id"],
            "phone_number": detail["phone_number"],
            "sex_id": detail["sex"]["id"],
            "role_id": detail["role"]["id"],
            "is_active": True,
            "password": "",
            "address": {
                "state": "Coahuila de Zaragoza", "municipality": "Saltillo", "neighborhood": "Centro", "street": "Calle Uno",
                "exterior_number": "1",
                "interior_number": "",
            },
        }
        data.update(over)
        return data

    def detail(self, user=None):
        return self.g.get_json(f"/api/trabajadores/{(user or self.operator).pk}/").json()["worker"]

    def save(self, contacts=None, user=None, query="", **over):
        user = user or self.operator
        data = self.payload_from(self.detail(user), **over)
        if contacts is not None:
            data["contacts"] = contacts
        return self.g.put_json(f"/api/trabajadores/{user.pk}/{query}", data)

    def phone(self, value="8442223344", code=None, **extra):
        return {"kind": "telefono", "phone_code_id": (code or mx()).pk, "value": value, **extra}

    def email(self, value="otro@example.com", **extra):
        return {"kind": "correo", "value": value, **extra}


class PrincipalPhoneTest(WorkerContactApiBase):
    def create_payload(self, **over):
        roles = {r["label"]: r["id"] for r in self.g.get("/api/trabajadores/catalogos/").json()["roles"]}
        data = {
            "enrollment_id": "NP1", "first_name": "Nuevo", "paternal_surname": "P", "maternal_surname": "M",
            "email": "np1@example.com", "phone_code_id": mx().pk, "phone_number": "8441112233",
            "sex_id": Sex.objects.first().pk, "role_id": roles["Operador"], "is_active": True,
            "password": "Temporal12345x",
            "address": {"state": "Coahuila de Zaragoza", "municipality": "Saltillo", "neighborhood": "Centro", "street": "Calle Uno", "exterior_number": "5", "interior_number": ""},
        }
        data.update(over)
        return data

    def test_create_with_code_and_formatted_display(self):
        r = self.g.post_json("/api/trabajadores/", self.create_payload(phone_number="844 111-2233"))
        self.assertEqual(r.status_code, 201, r.content)
        worker = r.json()["worker"]
        self.assertEqual(worker["phone_number"], "8441112233")  # separators are dropped
        self.assertEqual(worker["phone_display"], "+52 8441112233")
        self.assertEqual(worker["phone_code"]["iso"], "MX")
        self.assertEqual(worker["contacts"], [])

    def test_code_is_required(self):
        r = self.g.post_json("/api/trabajadores/", self.create_payload(phone_code_id=None))
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone_code_id", r.json()["errors"])

    def test_unknown_or_inactive_code_is_rejected(self):
        for bad in (999999, "abc", PhoneCode.objects.get(iso="JP").pk):
            r = self.g.post_json("/api/trabajadores/", self.create_payload(phone_code_id=bad))
            self.assertEqual(r.status_code, 400, bad)
            self.assertIn("phone_code_id", r.json()["errors"])

    def test_number_must_be_digits_only_and_not_too_short(self):
        for bad in ("abc12345", "+528441112233", "123", "84411a2233", ""):
            r = self.g.post_json("/api/trabajadores/", self.create_payload(phone_number=bad))
            self.assertEqual(r.status_code, 400, bad)
            self.assertIn("phone_number", r.json()["errors"], bad)

    def test_code_plus_number_cannot_exceed_15_digits(self):
        # +52 and 13 digits = 15 -> fine; 14 digits -> 16 -> rejected
        ok = self.g.post_json("/api/trabajadores/?validar=1", self.create_payload(phone_number="1" * 13))
        self.assertNotIn("phone_number", ok.json()["errors"])
        bad = self.g.post_json("/api/trabajadores/?validar=1", self.create_payload(phone_number="1" * 14))
        self.assertIn("phone_number", bad.json()["errors"])
        self.assertEqual(MAX_PHONE_DIGITS, 15)

    def test_live_validation_reports_the_phone_without_saving(self):
        r = self.g.post_json("/api/trabajadores/?validar=1", self.create_payload(phone_number="12"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("phone_number", r.json()["errors"])
        self.assertFalse(User.objects.filter(enrollment_id="NP1").exists())

    def test_clean_number_helper(self):
        self.assertEqual(clean_number(" (844) 123-4567 "), "8441234567")
        self.assertEqual(clean_number("844.123.4567"), "8441234567")
        self.assertEqual(clean_number(None), "")

    def test_database_rejects_a_number_without_code(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=self.operator.pk).update(phone_code=None)

    def test_user_manager_requires_the_code(self):
        from accounts.models import User as U

        with self.assertRaises(ValueError):
            U.objects.create_user(
                "X9", "Clave12345x", role=self.operator.role, first_name="a",
                paternal_surname="b", maternal_surname="c", email="x@x.co",
                phone_number="8441234567", sex=Sex.objects.first(), address=self.operator2.address,
            )

    def test_phone_code_change_is_audited(self):
        self.assertEqual(self.save(phone_code_id=us().pk).status_code, 200)
        entry = AuditLog.objects.filter(action=AuditLog.UPDATE, table_name="usuarios").order_by("-id").first()
        self.assertEqual(entry.changes["Código telefónico"], ["México (+52)", "Estados Unidos (+1)"])


class WorkerContactsTest(WorkerContactApiBase):
    def test_add_a_second_phone_with_label_and_person(self):
        r = self.save([self.phone(label="Número 2", contact_name="Ana (esposa)", code=us(), value="2125550101")])
        self.assertEqual(r.status_code, 200, r.content)
        contacts = r.json()["worker"]["contacts"]
        self.assertEqual(len(contacts), 1)
        self.assertEqual(contacts[0]["label"], "Número 2")
        self.assertEqual(contacts[0]["contact_name"], "Ana (esposa)")
        self.assertEqual(contacts[0]["display"], "+1 2125550101")
        self.assertEqual(contacts[0]["kind"], "telefono")
        self.assertEqual(WorkerContact.objects.get().user, self.operator)

    def test_label_defaults_to_numero_2_and_correo_2(self):
        r = self.save([self.phone(), self.phone("8443334455"), self.email()])
        labels = [c["label"] for c in r.json()["worker"]["contacts"]]
        self.assertEqual(labels, ["Número 2", "Número 3", "Correo 2"])
        self.assertEqual(default_label("telefono", 0), "Número 2")

    def test_email_contact_is_stored_lowercase_and_without_code(self):
        r = self.save([self.email("Otro@Example.COM")])
        contact = r.json()["worker"]["contacts"][0]
        self.assertEqual(contact["value"], "otro@example.com")
        self.assertIsNone(contact["phone_code_id"])

    def test_maximum_of_three(self):
        rows = [self.phone(f"84422233{i}0") for i in range(MAX_CONTACTS + 1)]
        r = self.save(rows)
        self.assertEqual(r.status_code, 400)
        self.assertIn("contacts", r.json()["errors"])
        self.assertEqual(WorkerContact.objects.count(), 0)
        ok = self.save(rows[:MAX_CONTACTS])
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(WorkerContact.objects.count(), MAX_CONTACTS)

    def test_limit_is_also_enforced_by_the_model_clean(self):
        from django.core.exceptions import ValidationError

        for i in range(MAX_CONTACTS):
            WorkerContact.objects.create(
                user=self.operator, kind="telefono", phone_code=mx(), value=f"844111222{i}", order=i
            )
        extra = WorkerContact(user=self.operator, kind="telefono", phone_code=mx(), value="8449990000")
        with self.assertRaises(ValidationError):
            extra.full_clean()

    def test_invalid_rows_are_reported_with_their_label(self):
        r = self.save([self.phone("12ab", label="Número 2"), {"kind": "otro"}, self.email("no-es-correo")])
        self.assertEqual(r.status_code, 400)
        messages = r.json()["errors"]["contacts"]
        self.assertTrue(any(m.startswith("Número 2:") for m in messages), messages)
        self.assertTrue(any("teléfono o un correo" in m for m in messages), messages)
        self.assertTrue(any("correo no es válido" in m for m in messages), messages)

    def test_phone_contact_needs_an_active_code_and_correo_needs_none(self):
        r = self.save([{"kind": "telefono", "value": "8442223344"}])
        self.assertEqual(r.status_code, 400)
        r = self.save([self.phone(code=PhoneCode.objects.get(iso="JP"))])
        self.assertEqual(r.status_code, 400)

    def test_contact_total_digits_limit(self):
        r = self.save([self.phone("1" * 14)])
        self.assertEqual(r.status_code, 400)

    def test_duplicates_are_rejected(self):
        # same as the principal phone
        detail = self.detail()
        r = self.save([self.phone(detail["phone_number"])])
        self.assertEqual(r.status_code, 400)
        self.assertIn("repite el teléfono principal", r.json()["errors"]["contacts"][0])
        # same as the principal email (case-insensitive)
        r = self.save([self.email(detail["email"].upper())])
        self.assertEqual(r.status_code, 400)
        self.assertIn("repite el correo principal", r.json()["errors"]["contacts"][0])
        # repeated between contacts
        r = self.save([self.phone("8445556677"), self.phone("8445556677")])
        self.assertEqual(r.status_code, 400)
        # same digits with another country code is another phone
        r = self.save([self.phone(detail["phone_number"], code=us())])
        self.assertEqual(r.status_code, 200, r.content)

    def test_absent_contacts_leave_them_untouched_and_empty_list_clears_them(self):
        self.assertEqual(self.save([self.phone()]).status_code, 200)
        r = self.save(contacts=None, first_name="Otro")
        self.assertEqual(len(r.json()["worker"]["contacts"]), 1)
        r = self.save([])
        self.assertEqual(r.json()["worker"]["contacts"], [])
        self.assertEqual(WorkerContact.objects.count(), 0)

    def test_sync_updates_by_id_creates_and_deletes(self):
        first = self.save([self.phone("8441110000"), self.phone("8442220000")]).json()["worker"]["contacts"]
        keep, drop = first
        rows = [
            {**keep, "contact_name": "Mamá"},  # same id, edited
            self.email("nuevo@example.com"),  # new
        ]
        r = self.save(rows)
        self.assertEqual(r.status_code, 200, r.content)
        contacts = r.json()["worker"]["contacts"]
        self.assertEqual([c["id"] for c in contacts][0], keep["id"])
        self.assertEqual(contacts[0]["contact_name"], "Mamá")
        self.assertFalse(WorkerContact.objects.filter(pk=drop["id"]).exists())
        self.assertEqual(len(contacts), 2)

    def test_reordering_is_kept(self):
        a, b = self.save([self.phone("8441110000"), self.phone("8442220000")]).json()["worker"]["contacts"]
        r = self.save([b, a])
        self.assertEqual([c["id"] for c in r.json()["worker"]["contacts"]], [b["id"], a["id"]])

    def test_cannot_touch_the_contact_of_another_worker(self):
        other = self.save([self.phone("8441110000")], user=self.operator2).json()["worker"]["contacts"][0]
        r = self.save([{**other}], user=self.operator)
        self.assertEqual(r.status_code, 400)
        self.assertIn("ya no existe", r.json()["errors"]["contacts"][0])
        self.assertTrue(WorkerContact.objects.filter(pk=other["id"], user=self.operator2).exists())

    def test_live_validation_does_not_save(self):
        r = self.save([self.phone()], query="?validar=1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["errors"], {})
        self.assertEqual(WorkerContact.objects.count(), 0)

    def test_contacts_on_creation(self):
        roles = {r["label"]: r["id"] for r in self.g.get("/api/trabajadores/catalogos/").json()["roles"]}
        r = self.g.post_json("/api/trabajadores/", {
            "enrollment_id": "NC1", "first_name": "Nuevo", "paternal_surname": "P", "maternal_surname": "M",
            "email": "nc1@example.com", "phone_code_id": mx().pk, "phone_number": "8441112233",
            "sex_id": Sex.objects.first().pk, "role_id": roles["Operador"], "is_active": True,
            "password": "Temporal12345x",
            "address": {"state": "Coahuila de Zaragoza", "municipality": "Saltillo", "neighborhood": "Centro", "street": "Calle Uno", "exterior_number": "5", "interior_number": ""},
            "contacts": [self.phone("8449998877", label="Número 2")],
        })
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(len(r.json()["worker"]["contacts"]), 1)

    def test_invalid_contacts_block_the_creation_of_the_worker(self):
        roles = {r["label"]: r["id"] for r in self.g.get("/api/trabajadores/catalogos/").json()["roles"]}
        r = self.g.post_json("/api/trabajadores/", {
            "enrollment_id": "NC2", "first_name": "Nuevo", "paternal_surname": "P", "maternal_surname": "M",
            "email": "nc2@example.com", "phone_code_id": mx().pk, "phone_number": "8441112233",
            "sex_id": Sex.objects.first().pk, "role_id": roles["Operador"], "is_active": True,
            "password": "Temporal12345x",
            "address": {"state": "Coahuila de Zaragoza", "municipality": "Saltillo", "neighborhood": "Centro", "street": "Calle Uno", "exterior_number": "5", "interior_number": ""},
            "contacts": [self.phone("zzzz")],
        })
        self.assertEqual(r.status_code, 400)
        self.assertFalse(User.objects.filter(enrollment_id="NC2").exists())

    def test_deleting_the_worker_deletes_the_contacts(self):
        roles = {r["label"]: r["id"] for r in self.g.get("/api/trabajadores/catalogos/").json()["roles"]}
        created = self.g.post_json("/api/trabajadores/", {
            "enrollment_id": "NC3", "first_name": "Nuevo", "paternal_surname": "P", "maternal_surname": "M",
            "email": "nc3@example.com", "phone_code_id": mx().pk, "phone_number": "8441112233",
            "sex_id": Sex.objects.first().pk, "role_id": roles["Operador"], "is_active": True,
            "password": "Temporal12345x",
            "address": {"state": "Coahuila de Zaragoza", "municipality": "Saltillo", "neighborhood": "Centro", "street": "Calle Uno", "exterior_number": "5", "interior_number": ""},
            "contacts": [self.phone("8449998877")],
        }).json()["worker"]
        self.assertEqual(WorkerContact.objects.filter(user_id=created["id"]).count(), 1)
        self.assertEqual(self.g.delete(f"/api/trabajadores/{created['id']}/").status_code, 200)
        self.assertEqual(WorkerContact.objects.filter(user_id=created["id"]).count(), 0)

    def test_database_constraint_phones_need_code_and_emails_must_not_have_one(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            WorkerContact.objects.create(user=self.operator, kind="telefono", value="8441110000")
        with self.assertRaises(IntegrityError), transaction.atomic():
            WorkerContact.objects.create(
                user=self.operator, kind="correo", phone_code=mx(), value="a@b.co"
            )

    def test_changes_are_audited_with_a_readable_name(self):
        self.save([self.phone(label="Número 2")])
        entry = AuditLog.objects.filter(action=AuditLog.CREATE, table_name="contactos_trabajador").first()
        self.assertIsNotNone(entry)
        self.assertIn("Número 2", entry.record)
        contact = WorkerContact.objects.get()
        self.save([])
        self.assertTrue(
            AuditLog.objects.filter(
                action=AuditLog.DELETE, table_name="contactos_trabajador", record_id=contact.pk
            ).exists()
        )

    def test_listing_pdf_shows_phone_with_code(self):
        r = self.g.get_json("/api/trabajadores/", format="pdf")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(r.content.startswith(b"%PDF"))
        # the same column is built from phone_display (code included)
        self.assertEqual(self.detail()["phone_display"], "+52 8441234567")

    def test_only_the_manager_can_read_or_change_contacts(self):
        self.assertEqual(self.o.get_json(f"/api/trabajadores/{self.operator.pk}/").status_code, 403)
        data = self.payload_from(self.detail())
        data["contacts"] = [self.phone()]
        self.assertEqual(self.o.put_json(f"/api/trabajadores/{self.operator.pk}/", data).status_code, 403)
        self.assertEqual(WorkerContact.objects.count(), 0)
