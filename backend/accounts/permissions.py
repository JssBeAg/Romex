from functools import wraps

from django.http import JsonResponse

from .roles import MANAGER_ROLE


def roles_required(*allowed_roles):
    """Only logged-in users whose role is one of the given roles can use the view."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({"error": "No has iniciado sesión"}, status=401)
            role = request.user.role
            if role is None or role.name not in allowed_roles:
                return JsonResponse({"error": "No tienes acceso a esta sección"}, status=403)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


manager_required = roles_required(MANAGER_ROLE)


def validation_only(request):
    """
    True when the form asks only to be checked (?validar=1): the view returns the errors it
    found, and saves nothing. The forms use it to warn about a field while it is being typed.
    """
    return request.GET.get("validar") == "1"
