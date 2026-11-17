"""
Roles of the system. A role is a Django group.

What each role can do is decided in the API views (see permissions.py), not with
Django's permission tables.

Run `python manage.py sync_roles` after changing this file to create missing roles
(docker-compose already runs it on every start).
"""

ADMIN_ROLE = "Administrador"  # also assigned automatically by `createsuperuser`
MANAGER_ROLE = "Gerente"  # the only role that can manage workers and units
MECHANIC_ROLE = "Mecánico"
OPERATOR_ROLE = "Operador"  # the only role that can create fault reports

ROLES = [ADMIN_ROLE, MANAGER_ROLE, MECHANIC_ROLE, OPERATOR_ROLE]
