"""Shared helpers for the API tests: users of every role, a unit, and a JSON client."""

import datetime
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group
from django.test import Client, TestCase

from accounts.models import PhoneCode, Sex, User
from accounts.roles import MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE, ROLES
from fleet.models import SparePart, UnitModel
from locations.models import Address

from .inegi_fake import patch_inegi

PASSWORD = "Clave12345x"


def today():
    # The server validates dates against Mexico City time, not UTC
    return datetime.datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()


def make_user(enrollment_id, role_name):
    role, _ = Group.objects.get_or_create(name=role_name)
    address = Address.objects.create(
        state="Coahuila de Zaragoza", municipality="Saltillo", neighborhood="Centro", street="Calle Uno", exterior_number="1"
    )
    return User.objects.create_user(
        enrollment_id,
        PASSWORD,
        role=role,
        first_name=enrollment_id,
        paternal_surname="Prueba",
        maternal_surname="Test",
        email=f"{enrollment_id.lower()}@example.com",
        phone_code=PhoneCode.objects.get(iso="MX"),
        phone_number="8441234567",
        sex=Sex.objects.first(),
        address=address,
    )


class ApiClient(Client):
    """Django test client with JSON helpers."""

    def get_json(self, path, **params):
        return self.get(path, params)

    def post_json(self, path, data=None):
        return self.post(path, data or {}, content_type="application/json")

    def put_json(self, path, data=None):
        return self.put(path, data or {}, content_type="application/json")


class ApiTestCase(TestCase):
    """One user per role (and a second operator), all with the same password."""

    @classmethod
    def setUpTestData(cls):
        for name in ROLES:
            Group.objects.get_or_create(name=name)
        cls.manager = make_user("G1", MANAGER_ROLE)
        cls.mechanic = make_user("M1", MECHANIC_ROLE)
        cls.mechanic2 = make_user("M2", MECHANIC_ROLE)
        cls.operator = make_user("O1", OPERATOR_ROLE)
        cls.operator2 = make_user("O2", OPERATOR_ROLE)

    def client_for(self, user):
        client = ApiClient()
        client.force_login(user)
        return client

    def setUp(self):
        patch_inegi(self)
        self.g = self.client_for(self.manager)
        self.m = self.client_for(self.mechanic)
        self.o = self.client_for(self.operator)

    # -- data helpers (through the API, like the screens do) --------------------------------
    def make_unit(self, number="T-100", operators=None, mileage=1000):
        response = self.g.post_json(
            "/api/unidades/",
            {
                "economic_number": number,
                "unit_model_id": UnitModel.objects.first().pk,
                "mileage": str(mileage),
                "plate": {
                    "identifier": f"PL{number.replace('-', '')}",
                    "state": "Coahuila de Zaragoza",
                    "start_date": today(),
                },
                "add_operators": [
                    {"operator_id": u.pk, "start_date": today()} for u in (operators or [self.operator])
                ],
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["unit"]

    def make_part(self, name, stock=0, min_stock=0):
        response = self.g.post_json(
            "/api/refacciones/",
            {"name": name, "unit_price": "10", "min_stock": min_stock, "initial_stock": stock},
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["spare_part"]

    def make_report(self, unit):
        response = self.o.post_json(
            "/api/reportes-fallas/",
            {"unit_id": unit["id"], "date": today(), "location": "Autopista", "description": "Falla"},
        )
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["report"]

    def report_status(self, report_id):
        return self.g.get_json(f"/api/reportes-fallas/{report_id}/").json()["report"]["status"]["label"]
