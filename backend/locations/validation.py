"""Checks of a state and a municipality against INEGI's catalog."""

from . import inegi

REQUIRED = "Este campo es obligatorio."
INVALID = "Elige una opción válida."


def check_state(state, current=""):
    """Error message for a state name, or None. A name that was already saved is accepted."""
    if not state:
        return REQUIRED
    if state == current:
        return None
    try:
        return None if inegi.check_state(state) else INVALID
    except inegi.InegiUnavailable:
        return inegi.UNAVAILABLE_MESSAGE


def check_address_place(state, municipality, current_state="", current_municipality=""):
    """
    Errors of the state and the municipality: {"state": msg, "municipality": msg} (only the ones
    that fail). Names the address already has are accepted without asking INEGI again, so an old
    address can still be saved when INEGI does not answer or renamed something.
    """
    errors = {}
    message = check_state(state, current_state)
    if message:
        errors["state"] = message
    if not municipality:
        errors["municipality"] = REQUIRED
    elif "state" not in errors and not (
        state == current_state and municipality == current_municipality
    ):
        try:
            if not inegi.check_municipality(state, municipality):
                errors["municipality"] = INVALID
        except inegi.InegiUnavailable:
            errors["municipality"] = inegi.UNAVAILABLE_MESSAGE
    return errors
