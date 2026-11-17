from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, Group
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, validate_email
from django.db import models
from django.utils import timezone

from locations.models import Address

from .roles import ADMIN_ROLE

# National number only (the country code lives in its own table): digits, 4 to 14 of them.
# Code + number may not exceed 15 digits (ITU E.164); see accounts/contacts.py.
phone_validator = RegexValidator(
    regex=r"^\d{4,14}$",
    message="Escribe solo números (de 4 a 14 dígitos), sin el código del país.",
)

# Alternative contacts a worker may have besides the principal phone and email
MAX_CONTACTS = 3


class Sex(models.Model):
    """Catalog of sexes (Hombre / Mujer). The rows are created by a migration."""

    name = models.CharField("nombre", max_length=20, unique=True, db_column="nombre")

    class Meta:
        db_table = "sexos"
        verbose_name = "sexo"
        verbose_name_plural = "sexos"

    def __str__(self):
        return self.name


class PhoneCode(models.Model):
    """
    International dialing code of a country (+52, +1, +51...). The rows come from a data
    migration; the administrator can switch countries on or off. Several countries share a
    code, so the code is not unique: each country is a row.
    """

    country_name = models.CharField("país", max_length=60, unique=True, db_column="pais")
    iso = models.CharField("ISO", max_length=2, unique=True, db_column="iso")
    code = models.CharField("código", max_length=4, db_column="codigo", help_text="Sin el signo +.")
    is_active = models.BooleanField(
        "activo",
        default=True,
        db_column="activo",
        help_text="Solo los activos aparecen al capturar un teléfono.",
    )

    class Meta:
        db_table = "codigos_telefonicos"
        verbose_name = "código telefónico"
        verbose_name_plural = "códigos telefónicos"
        ordering = ["country_name"]
        indexes = [models.Index(fields=["is_active"], name="codigos_tel_activo_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(code__regex=r"^[0-9]{1,4}$"),
                name="codigo_telefonico_solo_digitos",
            ),
        ]

    def __str__(self):
        return f"{self.country_name} (+{self.code})"


class UserManager(BaseUserManager):
    """Manager for a user that logs in with an enrollment ID instead of a username."""

    use_in_migrations = True

    @staticmethod
    def _use_instance_or_id(extra_fields, name, model, label, required):
        """Foreign key given as an instance or an id; only required for non-superusers."""
        value = extra_fields.pop(name, None)
        if value is None:
            value = extra_fields.pop(f"{name}_id", None)
        if value is None:
            if required:
                raise ValueError(f"The {label} is required")
            return
        extra_fields[name if isinstance(value, model) else f"{name}_id"] = value

    def _create_user(self, enrollment_id, password, role=None, **extra_fields):
        if not enrollment_id:
            raise ValueError("The enrollment ID is required")
        if role is None:
            raise ValueError("The role is required")
        # Only the initial superuser may be created without contact data, sex and address
        # (the database has a CHECK constraint with the same rule)
        required = not extra_fields.get("is_superuser", False)
        if required and not extra_fields.get("phone_number"):
            raise ValueError("The phone number is required")
        if extra_fields.get("phone_number") and not (
            extra_fields.get("phone_code") or extra_fields.get("phone_code_id")
        ):
            raise ValueError("The phone code is required")
        if required and not extra_fields.get("email"):
            raise ValueError("The email is required")
        if extra_fields.get("email"):
            extra_fields["email"] = self.normalize_email(extra_fields["email"])
        self._use_instance_or_id(extra_fields, "sex", Sex, "sex", required)
        self._use_instance_or_id(extra_fields, "address", Address, "address", required)
        user = self.model(enrollment_id=enrollment_id, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, enrollment_id, password=None, role=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(enrollment_id, password, role, **extra_fields)

    def create_superuser(self, enrollment_id, password=None, role=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("A superuser needs is_staff=True and is_superuser=True")
        # createsuperuser does not ask for a role: use (or create) the administrator role
        if role is None:
            role, _ = Group.objects.get_or_create(name=ADMIN_ROLE)
        return self._create_user(enrollment_id, password, role, **extra_fields)


class User(AbstractBaseUser):
    """
    Django's user (sessions, login...) with the enrollment ID as login.

    Each user has exactly one role: a row of auth_group (the roles table), linked by the
    id_rol column. Permissions are decided by role, not by Django's permission tables.
    """

    # --- Fields Django already provides, re-declared only to name their columns in Spanish ---
    password = models.CharField("contraseña", max_length=128, db_column="contrasena")
    last_login = models.DateTimeField(
        "último acceso", blank=True, null=True, db_column="ultimo_acceso"
    )
    is_superuser = models.BooleanField(
        "es superusuario",
        default=False,
        db_column="es_superusuario",
        help_text="Tiene todos los permisos sin que se le asignen uno por uno.",
    )
    is_staff = models.BooleanField(
        "es staff",
        default=False,
        db_column="es_staff",
        help_text="Indica si puede entrar al panel de administración.",
    )
    is_active = models.BooleanField(
        "activo",
        default=True,
        db_column="activo",
        help_text="Desmárcalo en lugar de borrar al usuario.",
    )
    date_joined = models.DateTimeField(
        "fecha de registro", default=timezone.now, db_column="fecha_registro"
    )
    # The user's only role (a row of auth_group). Roles cannot be deleted while users have them.
    role = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name="rol",
        db_column="id_rol",
    )

    # --- ROMEX fields ---
    enrollment_id = models.CharField(
        "matrícula",
        max_length=30,
        unique=True,
        db_column="matricula",
        error_messages={"unique": "Ya existe un usuario con esta matrícula."},
    )
    first_name = models.CharField("nombre(s)", max_length=150, db_column="nombres")
    paternal_surname = models.CharField(
        "apellido paterno", max_length=150, db_column="apellido_paterno"
    )
    maternal_surname = models.CharField(
        "apellido materno", max_length=150, db_column="apellido_materno"
    )
    # sex, email, phone number and address are required for everybody except superusers
    # (see the CHECK constraint in Meta); a superuser completes them later in the admin panel
    sex = models.ForeignKey(
        Sex,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name="sexo",
        db_column="id_sexo",
    )
    email = models.EmailField("correo electrónico", blank=True, db_column="correo")
    # Principal phone = country code (own table) + national number (digits only)
    phone_code = models.ForeignKey(
        PhoneCode,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="users",
        verbose_name="código telefónico",
        db_column="id_codigo_telefonico",
    )
    phone_number = models.CharField(
        "número telefónico",
        max_length=14,
        blank=True,
        validators=[phone_validator],
        db_column="telefono",
    )
    # Each user has their own address
    address = models.OneToOneField(
        Address,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="user",
        verbose_name="domicilio",
        db_column="id_domicilio",
    )

    # --- Profile photo (optional; without one the screens show the person's initials) ---
    photo = models.ImageField(
        "fotografía",
        upload_to="trabajadores/",
        max_length=255,
        blank=True,
        db_column="foto",
        help_text="Opcional. Se guarda recortada en cuadro y sin metadatos.",
    )

    # --- Account security ---
    must_change_password = models.BooleanField(
        "debe cambiar su contraseña",
        default=False,
        db_column="cambio_contrasena_obligatorio",
        help_text="Si está marcado, en el próximo ingreso tendrá que elegir una contraseña nueva.",
    )
    failed_attempts = models.PositiveSmallIntegerField(
        "intentos fallidos", default=0, db_column="intentos_fallidos"
    )
    locked_until = models.DateTimeField(
        "bloqueada hasta", null=True, blank=True, db_column="bloqueado_hasta"
    )
    password_changed_at = models.DateTimeField(
        "contraseña cambiada el", null=True, blank=True, db_column="contrasena_cambiada"
    )

    USERNAME_FIELD = "enrollment_id"
    # createsuperuser asks only for these (plus enrollment ID and password); the role is automatic
    REQUIRED_FIELDS = ["first_name", "paternal_surname", "maternal_surname"]

    objects = UserManager()

    class Meta:
        db_table = "usuarios"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(is_superuser=True)
                    | (
                        models.Q(sex__isnull=False)
                        & models.Q(address__isnull=False)
                        & ~models.Q(email="")
                        & ~models.Q(phone_number="")
                        & models.Q(phone_code__isnull=False)
                    )
                ),
                name="usuario_datos_completos_salvo_superusuario",
            ),
            # A number without its country code is meaningless, for anybody
            models.CheckConstraint(
                condition=models.Q(phone_number="") | models.Q(phone_code__isnull=False),
                name="usuario_telefono_requiere_codigo",
            ),
        ]

    @property
    def phone_display(self):
        """Principal phone as people read it: "+52 8441234567" (empty if there is none)."""
        if not (self.phone_number and self.phone_code_id):
            return self.phone_number
        return f"+{self.phone_code.code} {self.phone_number}"

    @property
    def is_locked(self):
        """True while the account is blocked for too many failed logins."""
        return self.locked_until is not None and self.locked_until > timezone.now()

    @property
    def profile_incomplete(self):
        """True when a superuser still lacks the data every other user must have."""
        return not (
            self.sex_id
            and self.address_id
            and self.email
            and self.phone_number
            and self.phone_code_id
        )

    # Permissions: only superusers (the administrators) are allowed everything in the admin panel;
    # everybody else is restricted by role in the API views (see permissions.py)
    def has_perm(self, perm, obj=None):
        return self.is_active and self.is_superuser

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(perm, obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        return self.is_active and self.is_superuser

    def get_full_name(self):
        parts = [self.first_name, self.paternal_surname, self.maternal_surname]
        return " ".join(part for part in parts if part)

    def get_short_name(self):
        return self.first_name

    def __str__(self):
        return self.enrollment_id


class WorkerContact(models.Model):
    """
    Another way to reach the SAME worker (a second phone, a second email...), besides the
    principal phone and email that live in "usuarios". At most MAX_CONTACTS per worker
    (enforced by the API and the admin; see accounts/contacts.py).
    """

    PHONE = "telefono"
    EMAIL = "correo"
    KINDS = [(PHONE, "Teléfono"), (EMAIL, "Correo electrónico")]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="contacts",
        verbose_name="trabajador",
        db_column="id_usuario",
    )
    kind = models.CharField("tipo", max_length=10, choices=KINDS, db_column="tipo")
    phone_code = models.ForeignKey(
        PhoneCode,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="contacts",
        verbose_name="código telefónico",
        db_column="id_codigo_telefonico",
    )
    # A national number (digits only) for phones, an address for emails
    value = models.CharField("valor", max_length=254, db_column="valor")
    label = models.CharField(
        "etiqueta", max_length=40, blank=True, db_column="etiqueta", help_text='Por ejemplo "Número 2".'
    )
    contact_name = models.CharField(
        "nombre de la persona",
        max_length=150,
        blank=True,
        db_column="nombre_contacto",
        help_text="Opcional: de quién es este número o correo (por ejemplo, un familiar).",
    )
    order = models.PositiveSmallIntegerField("orden", default=0, db_column="orden")

    class Meta:
        db_table = "contactos_trabajador"
        verbose_name = "contacto del trabajador"
        verbose_name_plural = "contactos del trabajador"
        ordering = ["user_id", "order", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(kind="telefono", phone_code__isnull=False)
                    | models.Q(kind="correo", phone_code__isnull=True)
                ),
                name="contacto_codigo_solo_telefonos",
            ),
        ]

    def __str__(self):
        return f"{self.label or self.get_kind_display()}: {self.display}"

    def clean(self):
        """Same rules the API applies (the admin panel goes through here)."""
        super().clean()
        if self.kind == self.PHONE:
            if not self.phone_code_id:
                raise ValidationError({"phone_code": "Elige el código del país."})
            phone_validator(self.value)
            if len(self.phone_code.code) + len(self.value) > 15:
                raise ValidationError(
                    {"value": "Con el código del país, el teléfono no puede pasar de 15 dígitos."}
                )
        elif self.kind == self.EMAIL:
            if self.phone_code_id:
                raise ValidationError({"phone_code": "Un correo no lleva código de país."})
            validate_email(self.value)
        if self.user_id and not self.pk:
            if WorkerContact.objects.filter(user_id=self.user_id).count() >= MAX_CONTACTS:
                raise ValidationError(f"Solo se permiten {MAX_CONTACTS} contactos adicionales.")

    @property
    def display(self):
        if self.kind == self.PHONE and self.phone_code_id:
            return f"+{self.phone_code.code} {self.value}"
        return self.value
