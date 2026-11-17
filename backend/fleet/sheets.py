"""
PDF sheets of one record (GET .../<id>/?format=pdf). They are built from the same dicts the
JSON API returns, so a person can only export what they are allowed to see.
"""

from common import pdf

YES_NO = lambda value: "Sí" if value else "No"


def report_sheet(user, report):
    sections = [
        {
            "heading": "Datos del reporte",
            "pairs": [
                ("Reporte", report["title"]),
                ("Fecha", report["date"]),
                ("Unidad", report["unit"]["label"]),
                ("Estatus", report["status"]["label"]),
                ("Ubicación", report["location"]),
                ("Reportó", report["reported_by"]["label"]),
            ],
        },
        {"heading": "Descripción de la falla", "text": report["description"]},
    ]
    if report["mechanics"]:
        sections.append(
            {
                "heading": "Mecánicos asignados",
                "columns": [("Mecánico", 3), ("Desde", 1), ("Hasta", 1)],
                "rows": [
                    [m["mechanic"]["label"], m["start_date"], m["end_date"] or "Vigente"]
                    for m in report["mechanics"]
                ],
            }
        )
    sections.append(
        {
            "heading": "Historial de estatus",
            "columns": [("Estatus", 2), ("Fecha y hora", 2), ("Cambió", 3)],
            "rows": [
                [h["status"], h["changed_at"][:16].replace("T", " "), h["changed_by"]]
                for h in report["status_history"]
            ],
        }
    )
    if report["evidence"]:
        sections.append(
            {
                "heading": "Evidencia",
                "text": "Fotos adjuntas: " + ", ".join(e["name"] for e in report["evidence"]),
            }
        )
    return pdf.sheet_pdf(user, report["title"], "Ficha de reporte de falla", sections)


def diagnosis_sheet(user, d):
    sections = [
        {
            "heading": "Datos del diagnóstico",
            "pairs": [
                ("Diagnóstico", d["title"]),
                ("Fecha", d["date"]),
                ("Unidad", d["unit"]["label"]),
                ("Gravedad", d["severity"]["label"]),
                ("Requiere reparación", YES_NO(d["requires_repair"])),
                ("Unidad operable", YES_NO(d["unit_operable"])),
                ("Mecánico", d["diagnosed_by"]["label"]),
                ("Mantenimientos", d["maintenances_count"]),
            ],
        },
        {"heading": "Reporte de falla", "text": d["fault_report"]["label"]},
        {"heading": "Descripción del reporte", "text": d["fault_report"]["description"]},
        {"heading": "Descripción del diagnóstico (causa detallada)", "text": d["detailed_cause"]},
    ]
    return pdf.sheet_pdf(user, d["title"], "Ficha de diagnóstico", sections)


def maintenance_sheet(user, m):
    sections = [
        {
            "heading": "Datos del mantenimiento",
            "pairs": [
                ("Mantenimiento", m["title"]),
                ("Fecha", m["date"]),
                ("Tipo", m["service_type"]["label"]),
                ("Unidad", m["unit"]["label"]),
                ("Kilometraje", m["service_mileage"]),
                ("Costo total (MXN)", m["total_cost"]),
                ("Reparación completada", YES_NO(m["repair_completed"])),
                ("Plan preventivo", m["plan"]["label"] if m["plan"] else "-"),
            ],
        },
        {
            "heading": "Mecánicos que participaron",
            "columns": [("Mecánico", 1)],
            "rows": [[o["label"]] for o in m["operators"]],
            "empty": "Sin mecánicos registrados.",
        },
        {
            "heading": "Refacciones usadas",
            "columns": [("Refacción", 4), ("Piezas", 1)],
            "rows": [[p["label"], p["quantity"]] for p in m["spare_parts"]],
            "empty": "No se usaron refacciones.",
        },
        {"heading": "Observaciones", "text": m["observations"] or "-"},
    ]
    if m["diagnosis"]:
        sections.insert(1, {"heading": "Diagnóstico", "text": m["diagnosis"]["label"]})
        sections.insert(2, {"heading": "Descripción del diagnóstico (causa detallada)", "text": m["diagnosis"]["detailed_cause"]})
    return pdf.sheet_pdf(user, m["title"], "Ficha de mantenimiento", sections)


def checklist_sheet(user, c):
    sections = [
        {
            "heading": "Datos del checklist",
            "pairs": [
                ("Checklist", c["title"]),
                ("Fecha", c["date"]),
                ("Unidad", c["unit"]["label"]),
                ("Operador", c["completed_by"]["label"]),
                ("Kilometraje", c["recorded_mileage"]),
                ("Presión de llantas", c["tire_pressure"]),
                ("Profundidad de dibujo", c["tire_tread_depth"]),
                ("Luces", YES_NO(c["lights_ok"])),
                ("Fluidos", YES_NO(c["fluids_ok"])),
                ("Sin grietas", YES_NO(c["no_cracks"])),
            ],
        },
        {"heading": "Descripción del viaje", "text": c["trip_description"] or "-"},
    ]
    return pdf.sheet_pdf(user, c["title"], "Ficha de checklist", sections)


def part_sheet(user, part):
    sections = [
        {
            "heading": "Datos de la refacción",
            "pairs": [
                ("Refacción", part["name"]),
                ("Estado", "Activa" if part["is_active"] else "Inactiva"),
                ("Existencias", part["stock"]),
                ("Existencia mínima", part["min_stock"]),
                ("Piezas usadas", part["used"]),
                ("Stock bajo", YES_NO(part["low_stock"])),
                ("Precio de referencia (MXN)", part["unit_price"] or "-"),
            ],
        },
        {"heading": "Descripción", "text": part["description"] or "-"},
        {
            "heading": "Movimientos (kardex de la refacción)",
            "columns": [("Fecha", 1.2), ("Movimiento", 2), ("Cambio", 1), ("Existencia", 1), ("Detalle", 3), ("Registró", 2.5)],
            "rows": [
                [e["date"], e["kind"], f"{e['change']:+d}", e["balance"], e["detail"] or "-", e["who"] or "-"]
                for e in part["history"]
            ],
        },
    ]
    return pdf.sheet_pdf(user, f"Refacción: {part['name']}", "Ficha de refacción", sections)


def kardex_sheet(user, data):
    unit, summary = data["unit"], data["summary"]
    plate = unit["current_plate"]
    sections = [
        {
            "heading": "Datos de la unidad",
            "pairs": [
                ("Número económico", unit["economic_number"]),
                ("Estado", "Activa" if unit["is_active"] else "Inactiva"),
                ("Marca / modelo", f"{unit['brand']['label']} / {unit['unit_model']['label']}"),
                ("Kilometraje", unit["mileage"]),
                ("Placa actual", plate["identifier"] if plate else "Sin placa vigente"),
                ("Estado de la placa", plate["state"] if plate else "-"),
                (
                    "Operadores vigentes",
                    ", ".join(o["operator"]["label"] for o in unit["operators"] if o["end_date"] is None) or "-",
                ),
            ],
        },
        {
            "heading": "Resumen",
            "pairs": [
                ("Reportes de falla", f"{summary['reports']} ({summary['pending_reports']} abiertos)"),
                ("Diagnósticos", summary["diagnoses"]),
                (
                    "Mantenimientos",
                    f"{summary['maintenances']} ({summary['preventive_maintenances']} preventivos, "
                    f"{summary['corrective_maintenances']} correctivos)",
                ),
                ("Costo total de mantenimiento (MXN)", summary["total_maintenance_cost"]),
                ("Checklists", summary["checklists"]),
            ],
        },
    ]
    if data["preventive"]:
        sections.append(
            {
                "heading": "Mantenimiento preventivo",
                "columns": [("Plan", 3), ("Estado", 1.6), ("Detalle", 4)],
                "rows": [
                    [r["plan"]["name"], r["status_label"], r["message"]]
                    for r in data["preventive"]
                ],
            }
        )
    if data["parts_used"]:
        sections.append(
            {
                "heading": "Refacciones cambiadas",
                "columns": [("Refacción", 4), ("Piezas", 1), ("Veces", 1), ("Último cambio", 1.6)],
                "rows": [[p["label"], p["pieces"], p["times"], p["last_date"]] for p in data["parts_used"]],
            }
        )
    sections.append(
        {
            "heading": "Historial de la unidad (lo más reciente primero)",
            "columns": [("Fecha", 1.2), ("Evento", 4), ("Detalle", 4)],
            "rows": [[e["date"], e["title"], e["detail"] or "-"] for e in data["events"]],
        }
    )
    return pdf.sheet_pdf(user, f"Kardex de la unidad {unit['economic_number']}", "Historial completo", sections)
