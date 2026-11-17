"""Folios: a consecutive number per author and kind of record (reports, diagnoses, maintenances)."""
from django.contrib.auth import get_user_model
from django.db.models import Max


def next_folio(model, author_field, author):
    """
    The next folio for this author in this model (1, 2, 3...). Call it inside a transaction:
    the author's row is locked so two simultaneous saves cannot get the same number.
    """
    get_user_model().objects.select_for_update().get(pk=author.pk)
    last = model.objects.filter(**{author_field: author}).aggregate(last=Max("folio"))["last"]
    return (last or 0) + 1


def folio_code(author, folio):
    """How a folio is shown: the author's enrollment ID and the number, e.g. O1-0003."""
    return f"{author.enrollment_id}-{folio:04d}"
