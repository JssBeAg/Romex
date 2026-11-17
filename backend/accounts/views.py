import json

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from . import security
from .models import User
from .permissions import validation_only
from .photos import photo_url


def serialize_user(user):
    """Public data about the logged-in user. The enrollment ID is Django's username."""
    return {
        "id": user.id,
        "enrollment_id": user.get_username(),
        "first_name": user.first_name,
        "paternal_surname": user.paternal_surname,
        "maternal_surname": user.maternal_surname,
        "role": user.role.name if user.role else None,
        "is_staff": user.is_staff,
        "must_change_password": user.must_change_password,
        "photo_url": photo_url(user),
    }


@require_GET
@ensure_csrf_cookie
def csrf(request):
    """Gives the frontend a CSRF token to send in the X-CSRFToken header."""
    return JsonResponse({"csrfToken": get_token(request)})


@require_POST
def login_view(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    enrollment_id = str(data.get("enrollment_id", "")).strip()
    password = data.get("password", "")

    if not enrollment_id or not password:
        return JsonResponse(
            {"error": "Enrollment ID and password are required"}, status=400
        )

    # A locked account cannot log in, not even with the right password
    candidate = User.objects.filter(enrollment_id=enrollment_id, is_active=True).first()
    if candidate is not None and candidate.is_locked:
        minutes = security.minutes_left(candidate)
        return JsonResponse(
            {
                "error": f"Cuenta bloqueada por demasiados intentos fallidos. Intenta de nuevo en {minutes} min.",
                "locked": True,
                "minutes": minutes,
            },
            status=423,
        )

    # authenticate() returns None for wrong credentials and for inactive users
    user = authenticate(request, username=enrollment_id, password=password)
    if user is None:
        security.register_failed_login(enrollment_id)
        return JsonResponse({"error": "Invalid enrollment ID or password"}, status=401)

    security.clear_failed_logins(user)
    login(request, user)
    return JsonResponse({"user": serialize_user(user)})


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_GET
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Not authenticated"}, status=401)
    return JsonResponse({"user": serialize_user(request.user)})


@require_POST
def change_password_view(request):
    """The logged-in user chooses a new password (also the forced change of the first login)."""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "No has iniciado sesión"}, status=401)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON no válido"}, status=400)

    errors = security.validate_new_password(
        request.user,
        data.get("current_password", ""),
        data.get("new_password", ""),
        data.get("confirm_password", ""),
    )
    if validation_only(request):
        return JsonResponse({"errors": errors})
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    security.change_password(request.user, data["new_password"])
    # Changing the password would otherwise end this session
    update_session_auth_hash(request, request.user)
    return JsonResponse({"user": serialize_user(request.user)})
