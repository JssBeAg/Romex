"""
Regenerates the parts of the documentation that come from the code itself:

  docs/modelo-datos.md      tables, columns, constraints and an ER diagram (Mermaid)
  docs/referencia-rutas.md  every API route and the first line of its documentation

Run it after changing models or urls:  python manage.py generar_docs
(the folder is docs/ at the root of the project, or the one given with --salida).
"""

import datetime
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models
from django.urls import URLPattern, URLResolver, get_resolver

APPS = ["accounts", "locations", "fleet", "audit", "notifications"]
APP_TITLES = {
    "accounts": "Cuentas y trabajadores",
    "locations": "Ubicaciones (domicilios)",
    "fleet": "Flota: unidades, reportes, diagnósticos, mantenimientos, inventario",
    "audit": "Bitácora de auditoría",
    "notifications": "Notificaciones",
}


def field_type(field):
    if field.is_relation:
        target = field.related_model._meta.db_table
        return f"FK → {target}" if not isinstance(field, models.OneToOneField) else f"1:1 → {target}"
    name = type(field).__name__.replace("Field", "")
    if getattr(field, "max_length", None):
        name += f"({field.max_length})"
    if isinstance(field, models.DecimalField):
        name += f"({field.max_digits},{field.decimal_places})"
    return name


def constraints_of(model):
    lines = []
    for c in model._meta.constraints:
        if isinstance(c, models.UniqueConstraint):
            where = " (parcial)" if c.condition is not None else ""
            lines.append(f"`{c.name}`: único en ({', '.join(c.fields)}){where}")
        elif isinstance(c, models.CheckConstraint):
            lines.append(f"`{c.name}`: restricción CHECK")
        else:
            lines.append(f"`{c.name}`")
    for fields in model._meta.unique_together:
        lines.append(f"único en ({', '.join(fields)})")
    return lines


def model_doc(model):
    meta = model._meta
    out = [f"### `{meta.db_table}`", ""]
    description = (model.__doc__ or "").strip().split("\n\n")[0].replace("\n", " ")
    if description and not description.startswith(model.__name__ + "("):
        out += [description, ""]
    out += ["| Columna | Tipo | Notas |", "|---|---|---|"]
    for f in meta.concrete_fields:
        notes = []
        if f.primary_key:
            notes.append("clave primaria")
        if f.unique and not f.primary_key:
            notes.append("único")
        if f.null:
            notes.append("acepta nulo")
        if f.is_relation:
            on = getattr(f.remote_field, "on_delete", None)
            if on is not None:
                notes.append(f"al borrar: {on.__name__}")
        if f.has_default() and not callable(f.default):
            notes.append(f"por defecto: {f.default!r}")
        label = str(f.verbose_name)
        if label and label != f.name.replace("_", " "):
            notes.append(label)
        out.append(f"| `{f.column}` | {field_type(f)} | {'; '.join(notes)} |")
    cons = constraints_of(meta.model)
    if cons:
        out += ["", "Restricciones:", ""] + [f"- {c}" for c in cons]
    out.append("")
    return out


def er_diagram():
    lines = ["```mermaid", "erDiagram"]
    seen = set()
    for label in APPS:
        for model in apps.get_app_config(label).get_models():
            for f in model._meta.concrete_fields:
                if f.is_relation and f.related_model is not None:
                    a, b = f.related_model._meta.db_table, model._meta.db_table
                    key = (a, b, f.column)
                    if key in seen:
                        continue
                    seen.add(key)
                    arrow = "||--o|" if isinstance(f, models.OneToOneField) else "||--o{"
                    lines.append(f"    {a} {arrow} {b} : \"{f.column}\"")
    lines.append("```")
    return lines


def walk(patterns, prefix=""):
    for p in patterns:
        if isinstance(p, URLResolver):
            yield from walk(p.url_patterns, prefix + str(p.pattern))
        elif isinstance(p, URLPattern):
            yield prefix + str(p.pattern), p.callback


class Command(BaseCommand):
    help = "Regenera docs/modelo-datos.md y docs/referencia-rutas.md a partir del código."

    def add_arguments(self, parser):
        parser.add_argument("--salida", default=None, help="Carpeta de salida (por defecto docs/ en la raíz).")

    def handle(self, *args, **options):
        out_dir = Path(options["salida"]) if options["salida"] else Path(settings.BASE_DIR).parent / "docs"
        out_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.date.today().isoformat()

        lines = [
            "# Modelo de datos",
            "",
            f"_Generado automáticamente con `python manage.py generar_docs` ({today}). No lo edites a mano._",
            "",
            "Convenciones: tablas, columnas y restricciones en español; claves foráneas con prefijo `id_`.",
            "",
            "## Diagrama entidad-relación",
            "",
        ] + er_diagram() + [""]
        for label in APPS:
            lines += [f"## {APP_TITLES[label]}", ""]
            for model in sorted(apps.get_app_config(label).get_models(), key=lambda m: m._meta.db_table):
                lines += model_doc(model)
        (out_dir / "modelo-datos.md").write_text("\n".join(lines), encoding="utf-8")

        routes = []
        for path, callback in walk(get_resolver().url_patterns):
            if not path.startswith("api/"):
                continue
            doc = (callback.__doc__ or "").strip().split("\n")[0]
            routes.append((path.replace("<int:", "<").replace("<str:", "<"), f"{callback.__module__.split('.')[-1]}.{callback.__name__}", doc))
        routes.sort()
        rlines = [
            "# Referencia de rutas de la API",
            "",
            f"_Generado automáticamente con `python manage.py generar_docs` ({today}). No lo edites a mano._",
            "",
            "Todas las rutas cuelgan de `/api/`. Detalle de uso y ejemplos en [api.md](api.md).",
            "",
            "| Ruta | Vista | Descripción |",
            "|---|---|---|",
        ]
        for path, view, doc in routes:
            rlines.append(f"| `/{path}` | `{view}` | {doc} |")
        (out_dir / "referencia-rutas.md").write_text("\n".join(rlines) + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Documentación generada en {out_dir}"))
