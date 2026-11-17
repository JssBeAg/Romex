"""Options for the state and municipality dropdowns, taken from INEGI's web service."""

from django.http import JsonResponse
from django.views.decorators.http import require_GET

from accounts.permissions import manager_required

from . import inegi


def unavailable():
    return JsonResponse({"error": inegi.UNAVAILABLE_MESSAGE}, status=503)


@manager_required
@require_GET
def states(request):
    try:
        return JsonResponse({"options": inegi.state_names()})
    except inegi.InegiUnavailable:
        return unavailable()


@manager_required
@require_GET
def municipalities(request):
    state = request.GET.get("estado", "").strip()
    if not state:
        return JsonResponse({"options": []})
    try:
        return JsonResponse({"options": inegi.municipality_names(state)})
    except inegi.InegiUnavailable:
        return unavailable()
