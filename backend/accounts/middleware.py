from django.http import JsonResponse

# What a user who must change the password may still call
ALLOWED_PATHS = (
    "/api/auth/",
    "/api/health/",
)


class ForcePasswordChangeMiddleware:
    """
    While a user has `must_change_password`, the API only answers the auth endpoints (login,
    logout, me, change password). The frontend sends them to the change-password screen; this
    makes the rule hold even if someone calls the API directly.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and getattr(user, "must_change_password", False)
            and request.path.startswith("/api/")
            and not request.path.startswith(ALLOWED_PATHS)
        ):
            return JsonResponse(
                {
                    "error": "Debes cambiar tu contraseña antes de continuar.",
                    "must_change_password": True,
                },
                status=403,
            )
        return self.get_response(request)
