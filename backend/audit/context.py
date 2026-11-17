"""The request that is being served, so the signals know who is making a change."""

from contextvars import ContextVar

_request = ContextVar("audit_request", default=None)


def set_request(request):
    return _request.set(request)


def reset_request(token):
    _request.reset(token)


def current_request():
    return _request.get()


def current_user():
    """The logged-in user of the current request, or None (shell, commands, seeds)."""
    request = _request.get()
    user = getattr(request, "user", None)
    return user if user is not None and user.is_authenticated else None


def current_ip():
    request = _request.get()
    return request.META.get("REMOTE_ADDR") or None if request is not None else None
