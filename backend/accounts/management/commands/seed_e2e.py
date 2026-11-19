"""
Datos fijos para las pruebas de navegador (frontend/e2e). Se puede correr las veces que
se quiera: deja a cada usuario de prueba en su estado inicial (contraseña, bloqueo,
cambio obligatorio, fotografía) y crea las unidades de prueba si faltan.

    python manage.py seed_e2e

Solo corre con DJANGO_DEBUG=1 (o con --force): crea usuarios con una contraseña conocida.
"""

import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.utils import timezone

from accounts.models import PhoneCode, Sex, User, WorkerContact
from accounts.roles import MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE, ROLES
from fleet.models import FaultDiagnosis, ServiceType, Unit, UnitModel, UnitOperator
from locations.models import Address
from accounts.photos import remove_photo_file
from notifications.models import Notification

PASSWORD = "Clave12345x"
# matrícula, rol, debe cambiar la contraseña al entrar
USERS = [
    ("G1", MANAGER_ROLE, False),
    ("M1", MECHANIC_ROLE, False),
    ("O1", OPERATOR_ROLE, False),
    ("O2", OPERATOR_ROLE, False),
    ("O3", OPERATOR_ROLE, False),  # has E2E-3; the test of the change of operator takes it away
    ("O4", OPERATOR_ROLE, False),  # without a unit: the one who gets E2E-3
    ("L1", OPERATOR_ROLE, False),  # para probar el bloqueo
    ("F1", OPERATOR_ROLE, True),  # para probar el cambio obligatorio
]
# economic number, operator (None = no operator). An operator has one open unit at most.
UNITS = [("E2E-1", "O1"), ("E2E-2", "O2"), ("E2E-3", "O3"), ("E2E-4", None)]
# Units whose operators the browser tests change: put back as UNITS says on every run
RESET_OPERATORS = ["E2E-3", "E2E-4"]


class Command(BaseCommand):
    help = "Crea o restablece los usuarios y unidades de las pruebas de navegador."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Permite correrlo con DJANGO_DEBUG=0.")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("Solo corre con DJANGO_DEBUG=1 (crea usuarios con contraseña conocida).")
        for name in ROLES:
            Group.objects.get_or_create(name=name)

        # Never reset a real account that happens to use one of these enrollment ids: it would get a
        # known password and lose its photo, contacts and notifications. The test accounts are
        # recognised by the name and e-mail this command gives them.
        real = [
            u.enrollment_id
            for u in User.objects.filter(enrollment_id__in=[e for e, _, _ in USERS])
            if not (u.first_name == u.enrollment_id and u.email == f"{u.enrollment_id.lower()}@example.com")
        ]
        if real:
            raise CommandError(
                f"Ya hay cuentas reales con las matrículas {', '.join(sorted(real))}; no se tocan. "
                "Corre seed_e2e en una base aparte para las pruebas (ver docs/pruebas.md)."
            )

        for enrollment_id, role_name, must_change in USERS:
            user = User.objects.filter(enrollment_id=enrollment_id).first()
            if user is None:
                address = Address.objects.create(
                    state="Coahuila de Zaragoza", municipality="Saltillo", neighborhood="Centro", street="Calle Uno", exterior_number="1"
                )
                user = User.objects.create_user(
                    enrollment_id, PASSWORD,
                    role=Group.objects.get(name=role_name),
                    first_name=enrollment_id, paternal_surname="Prueba", maternal_surname="E2E",
                    email=f"{enrollment_id.lower()}@example.com", phone_code=PhoneCode.objects.get(iso="MX"), phone_number="8441234567",
                    sex=Sex.objects.first(), address=address,
                )
            user.set_password(PASSWORD)
            user.is_active = True
            user.save()
            # update() so these resets do not fill the audit log
            User.objects.filter(pk=user.pk).update(
                must_change_password=must_change, failed_attempts=0, locked_until=None
            )
            Notification.objects.filter(user=user).delete()
            # Contacts added by an earlier run (raw delete: nothing goes into the audit log)
            WorkerContact.objects.filter(user=user)._raw_delete(WorkerContact.objects.db)
            if user.photo:
                remove_photo_file(user)
                User.objects.filter(pk=user.pk).update(photo="")

        # Diagnoses an earlier run left on the test units: one that says "cannot operate" would keep the
        # unit out of the checklist form (raw delete: nothing goes into the audit log)
        old = FaultDiagnosis.objects.filter(fault_report__unit__economic_number__in=[n for n, _ in UNITS])
        FaultDiagnosis.objects.filter(pk__in=list(old.values_list("pk", flat=True)))._raw_delete(FaultDiagnosis.objects.db)

        manager = User.objects.get(enrollment_id="G1")
        client = Client(HTTP_HOST="localhost")
        client.force_login(manager)
        today = datetime.datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()
        for number, operator_id in UNITS:
            if Unit.objects.filter(economic_number=number).exists():
                continue
            response = client.post(
                "/api/unidades/",
                {
                    "economic_number": number,
                    "unit_model_id": UnitModel.objects.first().pk,
                    "mileage": "5000",
                    "plate": {
                        "identifier": f"PL{number.replace('-', '')}",
                        "state": "Coahuila de Zaragoza",
                        "start_date": today,
                    },
                    "new_operator": (
                        {"operator_id": User.objects.get(enrollment_id=operator_id).pk, "start_date": today}
                        if operator_id
                        else None
                    ),
                },
                content_type="application/json",
            )
            if response.status_code != 201:
                raise CommandError(f"No se pudo crear la unidad {number}: {response.content!r}")
        # The kardex test filters the maintenances of E2E-1: it needs one (preventive, created once)
        e2e1 = Unit.objects.get(economic_number="E2E-1")
        if not e2e1.maintenances.exists():
            mechanic_client = Client(HTTP_HOST="localhost")
            mechanic_client.force_login(User.objects.get(enrollment_id="M1"))
            start = datetime.date.fromisoformat(today) - datetime.timedelta(days=10)
            response = mechanic_client.post(
                "/api/mantenimientos/",
                {
                    "service_type_id": ServiceType.objects.get(name="Preventivo").pk,
                    "unit_id": e2e1.pk,
                    "service_mileage": "5100",
                    "total_cost": "850",
                    "date": start.isoformat(),
                    "observations": "Cambio de aceite y filtros (datos de prueba).",
                    "operator_ids": [],
                    "spare_parts": [],
                },
                content_type="application/json",
            )
            if response.status_code != 201:
                raise CommandError(f"No se pudo crear el mantenimiento de E2E-1: {response.content!r}")

        # The change-of-operator test leaves E2E-3 with O4: give it back to O3, with a clean history
        # (raw delete: nothing goes into the audit log). It starts 30 days ago so a change today
        # leaves a period in the history.
        operators_of = dict(UNITS)
        reset_units = Unit.objects.filter(economic_number__in=RESET_OPERATORS)
        reset_people = [operators_of[n] for n in RESET_OPERATORS if operators_of[n]] + ["O4"]
        old = UnitOperator.objects.filter(unit__in=reset_units) | UnitOperator.objects.filter(
            operator__enrollment_id__in=reset_people
        )
        UnitOperator.objects.filter(pk__in=list(old.values_list("pk", flat=True)))._raw_delete(UnitOperator.objects.db)
        start = datetime.date.fromisoformat(today) - datetime.timedelta(days=30)
        # bulk_create sends no signals: nothing goes into the audit log
        UnitOperator.objects.bulk_create(
            UnitOperator(
                unit=unit,
                operator=User.objects.get(enrollment_id=operators_of[unit.economic_number]),
                start_date=start,
            )
            for unit in reset_units
            if operators_of[unit.economic_number]
        )

        self.stdout.write(
            f"Listo: {len(USERS)} usuarios (contraseña {PASSWORD}) y {len(UNITS)} unidades de prueba."
        )
