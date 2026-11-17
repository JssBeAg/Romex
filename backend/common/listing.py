"""
Shared behaviour of the list endpoints: ordering, date range, pagination and PDF export.

Every list accepts (all optional):
  order=<column>   sort by one of the columns the list allows; "-<column>" for descending
  date_from, date_to (YYYY-MM-DD)  on lists of records with a date
  page, page_size  page of the results (page_size up to 100)
  format=pdf       the whole filtered list (no pages) as a PDF file

The list answers {<key>: [...], "pagination": {page, pages, page_size, total}}.
"""

import datetime

from django.core.paginator import Paginator
from django.http import JsonResponse

from . import pdf

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def parse_date(text):
    try:
        return datetime.date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def wants_pdf(request):
    return request.GET.get("format") == "pdf"


def date_range(queryset, request, field="date"):
    """Keeps the rows whose date is inside date_from..date_to (invalid dates are ignored)."""
    start = parse_date(request.GET.get("date_from", ""))
    end = parse_date(request.GET.get("date_to", ""))
    if start:
        queryset = queryset.filter(**{f"{field}__gte": start})
    if end:
        queryset = queryset.filter(**{f"{field}__lte": end})
    return queryset


def order_by(queryset, request, sorts, default):
    """
    `sorts` maps a column name to the ORM fields it sorts by; `default` is the column used
    (as "name" or "-name") when the request asks for nothing valid. The primary key is always
    the last criterion so that pages never repeat or skip rows.
    """
    raw = request.GET.get("order", "").strip()
    name = raw.lstrip("-")
    if name not in sorts:
        raw = default
        name = default.lstrip("-")
    descending = raw.startswith("-")
    fields = [("-" + f if descending else f) for f in sorts[name]]
    return queryset.order_by(*fields, "-pk" if descending else "pk")


def page_numbers(request):
    def number(name, default, low, high):
        try:
            return min(high, max(low, int(request.GET.get(name, default))))
        except (TypeError, ValueError):
            return default

    return number("page", 1, 1, 10**9), number("page_size", DEFAULT_PAGE_SIZE, 1, MAX_PAGE_SIZE)


def filter_lines(*pairs):
    """("Estatus", "Pendiente") pairs -> "Estatus: Pendiente" lines, leaving out the empty ones."""
    return [f"{pair[0]}: {pair[1]}" for pair in pairs if pair and pair[1] not in (None, "", [])]


def dates_line(request):
    start = parse_date(request.GET.get("date_from", ""))
    end = parse_date(request.GET.get("date_to", ""))
    if not (start or end):
        return None
    fmt = lambda d: d.strftime("%d/%m/%Y")
    return ("Periodo", f"{fmt(start) if start else 'inicio'} al {fmt(end) if end else 'hoy'}")


def list_response(
    request,
    queryset,
    *,
    key,
    serialize,
    sorts,
    default,
    export=None,
    extra=None,
):
    """
    The JSON page of a list, or its PDF when format=pdf.

    export = {"title": ..., "filters": [lines], "columns": [(header, weight, getter)]}
    where getter takes the serialized row and returns the text of the cell.
    """
    queryset = order_by(queryset, request, sorts, default)

    if wants_pdf(request) and export is not None:
        rows = [serialize(obj) for obj in queryset]
        return pdf.list_pdf(
            request.user,
            export["title"],
            export.get("filters", []),
            [(header, weight) for header, weight, _ in export["columns"]],
            [[getter(row) for _, _, getter in export["columns"]] for row in rows],
            landscape_mode=export.get("landscape", True),
        )

    page_number, page_size = page_numbers(request)
    paginator = Paginator(queryset, page_size)
    page = paginator.get_page(page_number)
    return JsonResponse(
        {
            **(extra or {}),
            key: [serialize(obj) for obj in page.object_list],
            "pagination": {
                "page": page.number,
                "pages": paginator.num_pages,
                "page_size": page_size,
                "total": paginator.count,
            },
        }
    )
