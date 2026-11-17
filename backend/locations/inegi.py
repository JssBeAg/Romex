"""
Client of the INEGI web service "Catálogo Único de Claves Geoestadísticas" (wscatgeo).

The states and municipalities of Mexico are no longer stored in the database: they are asked
to INEGI each time a form needs them (a short in-memory cache avoids asking again and again).
Addresses and license plates only keep the chosen names as text.

    GET {INEGI_API_URL}/mgee/         -> {"datos": [{"cve_ent": "01", "nomgeo": "Aguascalientes", ...}]}
    GET {INEGI_API_URL}/mgem/<cve>    -> {"datos": [{"cve_mun": "001", "nomgeo": "Aguascalientes", ...}]}

When INEGI does not answer, `InegiUnavailable` is raised and the screens say so.
"""

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_SECONDS = 60 * 60
# Names may come under any of these keys (the service has changed its field names over time)
NAME_KEYS = ("nomgeo", "nom_agee", "nom_agem", "nom_ent", "nom_mun")
STATE_KEY_KEYS = ("cve_ent", "cve_agee")

UNAVAILABLE_MESSAGE = "No se pudo consultar el catálogo del INEGI. Intenta de nuevo en unos minutos."


class InegiUnavailable(Exception):
    """INEGI did not answer or answered something that is not the catalog."""


def _get(path):
    url = f"{settings.INEGI_API_URL.rstrip('/')}/{path}"
    try:
        with urllib.request.urlopen(url, timeout=settings.INEGI_TIMEOUT) as response:  # noqa: S310
            payload = json.load(response)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        logger.warning("INEGI request failed: %s (%s)", url, exc)
        raise InegiUnavailable(str(exc)) from exc
    rows = payload.get("datos") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise InegiUnavailable("Respuesta inesperada del INEGI")
    return rows


def _first(row, keys):
    for key in keys:
        if row.get(key):
            return str(row[key]).strip()
    return ""


def _cached(key, loader):
    value = cache.get(key)
    if value is None:
        value = loader()
        cache.set(key, value, CACHE_SECONDS)
    return value


def states():
    """[{"key": "01", "name": "Aguascalientes"}, ...] sorted by name."""

    def load():
        rows = [
            {"key": _first(r, STATE_KEY_KEYS), "name": _first(r, NAME_KEYS)}
            for r in _get("mgee/")
        ]
        rows = [r for r in rows if r["key"] and r["name"]]
        if not rows:
            raise InegiUnavailable("El INEGI no devolvió estados")
        return sorted(rows, key=lambda r: r["name"])

    return _cached("inegi:states", load)


def state_names():
    return [s["name"] for s in states()]


def municipality_names(state_name):
    """Names of the municipalities of a state ([] when the state is not one of INEGI's)."""
    match = next((s for s in states() if s["name"] == state_name), None)
    if match is None:
        return []

    def load():
        names = {_first(r, NAME_KEYS) for r in _get(f"mgem/{match['key']}")}
        return sorted(n for n in names if n)

    return _cached(f"inegi:municipalities:{match['key']}", load)


def check_state(name):
    """Whether the name is one of INEGI's states. Raises InegiUnavailable."""
    return name in state_names()


def check_municipality(state_name, name):
    """Whether the name is a municipality of that state. Raises InegiUnavailable."""
    return name in municipality_names(state_name)
