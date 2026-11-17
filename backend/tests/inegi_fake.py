"""INEGI's web service replaced by a small catalog, so no test needs the internet."""

from unittest import mock

from django.core.cache import cache

from locations import inegi
from locations.management.commands.inegi_falso import municipality_rows, state_rows


def fake_get(path):
    path = path.strip("/")
    if path == "mgee":
        return state_rows()
    if path.startswith("mgem/"):
        return municipality_rows(path.split("/")[1])
    raise inegi.InegiUnavailable(path)


def patch_inegi(test):
    """Use the fake catalog (and an empty cache) during the test; returns the mock."""
    cache.clear()
    patcher = mock.patch.object(inegi, "_get", side_effect=fake_get)
    test.addCleanup(cache.clear)
    test.addCleanup(patcher.stop)
    return patcher.start()
