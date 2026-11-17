from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from accounts.roles import ROLES


class Command(BaseCommand):
    help = "Crea los roles definidos en accounts/roles.py (los que ya existen no se tocan)."

    def handle(self, *args, **options):
        for role_name in ROLES:
            _, created = Group.objects.get_or_create(name=role_name)
            self.stdout.write(f"Rol {role_name}: {'creado' if created else 'ya existía'}")
