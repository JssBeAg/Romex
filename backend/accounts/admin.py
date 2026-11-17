from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import (
    AdminPasswordChangeForm,
    BaseUserCreationForm,
    UserChangeForm,
)
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import JsonResponse
from django.urls import path, reverse

from locations import inegi
from locations.models import Address

from .models import MAX_CONTACTS, PhoneCode, User, WorkerContact


def role_field():
    """Required dropdown with the roles."""
    return forms.ModelChoiceField(
        queryset=Group.objects.order_by("name"),
        label="Rol",
        required=True,
    )


def place_choices(names, current=""):
    """Dropdown choices from a list of names; the name already saved is kept even if INEGI lacks it."""
    names = list(names)
    if current and current not in names:
        names.append(current)
    return [("", "---------")] + [(name, name) for name in names]


class AddressFieldsMixin(forms.Form):
    """
    Address fields inside the user form: state -> municipality (the options come from INEGI's
    web service; the municipalities depend on the state), the colonia and the street as free
    text, plus the exterior and interior numbers. The country is always Mexico.
    """

    # Not required by the fields themselves: a superuser may leave the profile incomplete.
    # `clean` requires them for everybody else.
    state = forms.ChoiceField(label="Estado", required=False)
    municipality = forms.ChoiceField(label="Municipio", required=False)
    neighborhood = forms.CharField(label="Colonia", max_length=150, required=False)
    street = forms.CharField(label="Calle", max_length=150, required=False)
    exterior_number = forms.CharField(label="Número exterior", max_length=20, required=False)
    interior_number = forms.CharField(label="Número interior", max_length=20, required=False)

    class Media:
        js = ["romex/address_cascade.js"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # When editing, start from the user's current address
        instance = getattr(self, "instance", None)
        if instance is not None and instance.pk and instance.address_id:
            address = instance.address
            self.initial.update(
                state=address.state,
                municipality=address.municipality,
                neighborhood=address.neighborhood,
                street=address.street,
                exterior_number=address.exterior_number,
                interior_number=address.interior_number,
            )

        # The municipalities offered are those of the state chosen (submitted, or the initial one)
        state = (self.data.get(self.add_prefix("state")) if self.is_bound else self.initial.get("state")) or ""
        self.inegi_down = False
        try:
            state_names = inegi.state_names()
            municipality_names = inegi.municipality_names(state) if state else []
        except inegi.InegiUnavailable:
            self.inegi_down = True
            state_names, municipality_names = [], []
        self.fields["state"].choices = place_choices(state_names, self.initial.get("state", ""))
        self.fields["municipality"].choices = place_choices(
            municipality_names, self.initial.get("municipality", "") if state == self.initial.get("state") else ""
        )
        self.fields["state"].widget.attrs["data-options-url"] = reverse("admin:accounts_user_location_options")

    # Fields every user needs except a superuser
    REQUIRED_PROFILE_FIELDS = (
        "email",
        "phone_code",
        "phone_number",
        "sex",
        "state",
        "municipality",
        "neighborhood",
        "street",
        "exterior_number",
    )

    def is_superuser_form(self):
        """Whether the user being saved is a superuser (only the edit form can say so)."""
        return bool(self.cleaned_data.get("is_superuser"))

    def clean(self):
        cleaned = super().clean()
        if not self.is_superuser_form():
            for name in self.REQUIRED_PROFILE_FIELDS:
                if name in self.fields and not cleaned.get(name) and name not in self.errors:
                    self.add_error(name, "Este campo es obligatorio.")
        return cleaned


class UserCreationForm(AddressFieldsMixin, BaseUserCreationForm):
    """Add form: everything required is asked on this first screen. Always password login."""

    role = role_field()

    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = (
            "enrollment_id",
            "first_name",
            "paternal_surname",
            "maternal_surname",
            "email",
            "phone_code",
            "phone_number",
            "sex",
        )
        field_classes = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # México (+52) is the usual one: the new user starts with it chosen
        mexico = PhoneCode.objects.filter(iso="MX", is_active=True).first()
        if mexico is not None:
            self.fields["phone_code"].initial = mexico.pk


class UserEditForm(AddressFieldsMixin, UserChangeForm):
    role = role_field()

    class Meta(UserChangeForm.Meta):
        model = User
        field_classes = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["role"].initial = self.instance.role


class PasswordChangeForm(AdminPasswordChangeForm):
    """Change-password form without the "password-based authentication" option."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("usable_password", None)
        self.fields["password1"].required = True
        self.fields["password2"].required = True


class PlainSelectsMixin:
    """
    A dropdown of a catalog that is only chosen from, with no add / change / delete / view
    buttons next to it (Django adds them when the catalog is also registered in the admin).
    """

    plain_selects = ("phone_code",)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in self.plain_selects and isinstance(field.widget, RelatedFieldWidgetWrapper):
            field.widget = field.widget.widget
        return field


class WorkerContactInline(PlainSelectsMixin, admin.TabularInline):
    """Alternative ways to reach the worker (at most MAX_CONTACTS)."""

    model = WorkerContact
    extra = 0
    max_num = MAX_CONTACTS
    fields = ("kind", "label", "phone_code", "value", "contact_name", "order")
    verbose_name = "contacto adicional"
    verbose_name_plural = f"contactos adicionales (máximo {MAX_CONTACTS})"


@admin.register(PhoneCode)
class PhoneCodeAdmin(admin.ModelAdmin):
    """Dialing codes: the list is loaded by a migration; here countries are switched on or off."""

    list_display = ("country_name", "iso", "code", "is_active")
    list_filter = ("is_active",)
    list_editable = ("is_active",)
    search_fields = ("country_name", "iso", "code")
    ordering = ("country_name",)


@admin.register(User)
class UserAdmin(PlainSelectsMixin, DjangoUserAdmin):
    inlines = [WorkerContactInline]
    add_form = UserCreationForm
    form = UserEditForm
    change_password_form = PasswordChangeForm
    # The role is a plain dropdown (the Rol field); there are no permission lists to pick from
    filter_horizontal = ()

    fieldsets = (
        (None, {"fields": ("enrollment_id", "password")}),
        (
            "Información personal",
            {
                "fields": (
                    "first_name",
                    "paternal_surname",
                    "maternal_surname",
                    "phone_code",
                    "phone_number",
                    "sex",
                    "email",
                )
            },
        ),
        ("Rol", {"fields": ("role",)}),
        (
            "Domicilio",
            {
                "fields": (
                    "state",
                    "municipality",
                    "neighborhood",
                    "street",
                    "exterior_number",
                    "interior_number",
                )
            },
        ),
        (
            "Permisos",
            {"fields": ("is_active", "is_staff", "is_superuser")},
        ),
        ("Fechas importantes", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "enrollment_id",
                    "first_name",
                    "paternal_surname",
                    "maternal_surname",
                    "email",
                    "phone_code",
                    "phone_number",
                    "sex",
                    "role",
                ),
            },
        ),
        (
            "Domicilio",
            {
                "fields": (
                    "state",
                    "municipality",
                    "neighborhood",
                    "street",
                    "exterior_number",
                    "interior_number",
                )
            },
        ),
        ("Contraseña", {"fields": ("password1", "password2")}),
    )
    list_display = (
        "enrollment_id",
        "first_name",
        "paternal_surname",
        "maternal_surname",
        "role_name",
        "is_active",
    )
    list_filter = ("role", "is_active", "is_staff")
    search_fields = (
        "enrollment_id",
        "first_name",
        "paternal_surname",
        "maternal_surname",
        "email",
    )
    ordering = ("enrollment_id",)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("role")

    @admin.display(description="Rol", ordering="role__name")
    def role_name(self, obj):
        return obj.role.name if obj.role else "-"

    def get_urls(self):
        # Must come before the default routes, which would read it as an object id
        return [
            path(
                "location-options/",
                self.admin_site.admin_view(self.location_options),
                name="accounts_user_location_options",
            ),
        ] + super().get_urls()

    def location_options(self, request):
        """Municipalities of the chosen state, for the cascading dropdown."""
        if not (self.has_add_permission(request) or self.has_change_permission(request)):
            raise PermissionDenied
        try:
            options = inegi.municipality_names(request.GET.get("state", ""))
        except inegi.InegiUnavailable:
            return JsonResponse({"error": inegi.UNAVAILABLE_MESSAGE}, status=503)
        return JsonResponse({"options": options})

    def response_add(self, request, obj, post_url_continue=None):
        # Django's UserAdmin sends you to the edit page after adding; go to the list instead
        return admin.ModelAdmin.response_add(self, request, obj, post_url_continue)

    def save_model(self, request, obj, form, change):
        # Create or update the user's address from the address fields of the form
        data = form.cleaned_data
        with transaction.atomic():
            # A superuser may still have no address: only save one when it was filled in
            if data.get("state") and data.get("municipality"):
                address = obj.address if obj.address_id else Address()
                address.state = data["state"]
                address.municipality = data["municipality"]
                address.neighborhood = data["neighborhood"]
                address.street = data["street"]
                address.exterior_number = data["exterior_number"]
                address.interior_number = data["interior_number"]
                address.save()
                obj.address = address
            super().save_model(request, obj, form, change)
