"""
PDF files of the system (lists and record sheets), made with ReportLab.

Every file has the same look: a red band with the name of the system, the title, the filters
that were applied, a table or sections, and a footer with who exported it, when, and the page.
Only characters of the Latin-1 alphabet are used (the standard fonts do not have more).
"""

import datetime
import io
import re

from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape, portrait
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

RED = colors.HexColor("#bd152c")
INK = colors.HexColor("#2d2926")
GREY = colors.HexColor("#6b6560")
LINE = colors.HexColor("#d9d4cf")
ZEBRA = colors.HexColor("#f6f3f0")

_base = getSampleStyleSheet()
TITLE = ParagraphStyle("t", parent=_base["Title"], fontName="Helvetica-Bold", fontSize=16, textColor=INK, alignment=0, spaceAfter=2)
FILTER = ParagraphStyle("f", parent=_base["Normal"], fontSize=8.5, textColor=GREY, leading=11)
HEADING = ParagraphStyle("h", parent=_base["Heading2"], fontName="Helvetica-Bold", fontSize=11.5, textColor=RED, spaceBefore=10, spaceAfter=4)
CELL = ParagraphStyle("c", parent=_base["Normal"], fontSize=8, leading=10, textColor=INK)
CELL_HEAD = ParagraphStyle("ch", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
BODY = ParagraphStyle("b", parent=_base["Normal"], fontSize=9.5, leading=13, textColor=INK)
LABEL = ParagraphStyle("l", parent=CELL, fontName="Helvetica-Bold", fontSize=8.5, textColor=GREY)

MARGIN = 14 * mm


def clean(value):
    """Text safe for the standard fonts and for Paragraph's mini-markup."""
    if value is None:
        return "-"
    text = str(value)
    if isinstance(value, bool):
        text = "Sí" if value else "No"
    text = text.replace("—", "-").replace("–", "-").replace("·", "-").replace("≤", "<=").replace("→", "->")
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text.encode("latin-1", "replace").decode("latin-1")


def slug(text):
    text = text.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def who(user):
    name = user.get_full_name() or user.get_username()
    return f"{name} ({user.get_username()})"


def _footer(user, title):
    stamp = timezone.localtime().strftime("%d/%m/%Y %H:%M")

    def draw(canvas, doc):
        width, height = doc.pagesize
        canvas.saveState()
        canvas.setFillColor(RED)
        canvas.rect(0, height - 9 * mm, width, 9 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(MARGIN, height - 6.2 * mm, "ROMEX Logística".encode("latin-1").decode("latin-1"))
        canvas.setFont("Helvetica", 8.5)
        canvas.drawRightString(width - MARGIN, height - 6.2 * mm, clean(title))
        canvas.setStrokeColor(LINE)
        canvas.line(MARGIN, 11 * mm, width - MARGIN, 11 * mm)
        canvas.setFillColor(GREY)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(MARGIN, 7 * mm, clean(f"Exportado por {who(user)} el {stamp}"))
        canvas.drawRightString(width - MARGIN, 7 * mm, f"Página {doc.page}")
        canvas.restoreState()

    return draw


def _build(user, title, story, landscape_mode):
    buffer = io.BytesIO()
    size = landscape(A4) if landscape_mode else portrait(A4)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=size,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title=title,
        author="ROMEX",
    )
    draw = _footer(user, title)
    doc.build(story, onFirstPage=draw, onLaterPages=draw)
    return buffer.getvalue(), size


def _response(content, title, user):
    from audit.signals import log_export

    log_export(user, title)
    response = HttpResponse(content, content_type="application/pdf")
    stamp = datetime.date.today().isoformat()
    response["Content-Disposition"] = f'attachment; filename="romex_{slug(title)}_{stamp}.pdf"'
    return response


def _header_block(title, filters):
    story = [Paragraph(clean(title), TITLE)]
    if filters:
        story.append(Paragraph(clean(" | ".join(filters)), FILTER))
    story.append(Spacer(1, 4 * mm))
    return story


def _table(columns, rows, available_width):
    total = sum(weight for _, weight in columns) or 1
    widths = [available_width * weight / total for _, weight in columns]
    data = [[Paragraph(clean(header), CELL_HEAD) for header, _ in columns]]
    for row in rows:
        data.append([Paragraph(clean(cell).replace("\n", "<br/>"), CELL) for cell in row])
    # splitInRow: a row taller than a page (a very long text) continues on the next page
    # instead of making the whole PDF fail
    table = Table(data, colWidths=widths, repeatRows=1, splitInRow=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for index in range(2, len(data), 2):
        style.append(("BACKGROUND", (0, index), (-1, index), ZEBRA))
    table.setStyle(TableStyle(style))
    return table


def list_pdf(user, title, filters, columns, rows, landscape_mode=True):
    """A PDF with a table: `columns` is [(header, relative width)], `rows` a list of lists."""
    size = landscape(A4) if landscape_mode else portrait(A4)
    story = _header_block(title, filters)
    if rows:
        story.append(_table(columns, rows, size[0] - 2 * MARGIN - 12))
    else:
        story.append(Paragraph("No hay registros con estos filtros.", BODY))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph(clean(f"Total: {len(rows)} registro(s)"), FILTER))
    content, _ = _build(user, title, story, landscape_mode)
    return _response(content, title, user)


def sheet_pdf(user, title, subtitle, sections, landscape_mode=False):
    """
    A PDF with the sheet of one record. `sections` is a list of dicts:
      {"heading": "Datos", "pairs": [(label, value), ...]}        label/value grid
      {"heading": "Historial", "columns": [(header, weight)], "rows": [[...]]}   table
      {"heading": "Notas", "text": "..."}                         paragraph
    """
    size = landscape(A4) if landscape_mode else portrait(A4)
    width = size[0] - 2 * MARGIN - 12  # the frame has 6 pt of padding on each side
    story = _header_block(title, [subtitle] if subtitle else [])
    for section in sections:
        block = [Paragraph(clean(section["heading"]), HEADING)]
        if "pairs" in section:
            data = []
            pairs = section["pairs"]
            for index in range(0, len(pairs), 2):
                row = []
                for label, value in pairs[index : index + 2]:
                    row += [Paragraph(clean(label), LABEL), Paragraph(clean(value), CELL)]
                while len(row) < 4:
                    row.append("")
                data.append(row)
            table = Table(data, colWidths=[width * 0.18, width * 0.32, width * 0.18, width * 0.32])
            table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, LINE),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            block.append(table)
        elif "columns" in section:
            if section["rows"]:
                block.append(_table(section["columns"], section["rows"], width))
            else:
                block.append(Paragraph(clean(section.get("empty", "Sin registros.")), BODY))
        else:
            block.append(Paragraph(clean(section.get("text") or "-").replace("\n", "<br/>"), BODY))
        story.append(KeepTogether(block[:2]) if len(block) > 1 else block[0])
        story.extend(block[2:])
    content, _ = _build(user, title, story, landscape_mode)
    return _response(content, title, user)
