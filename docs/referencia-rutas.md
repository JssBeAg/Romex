# Referencia de rutas de la API

_Generado automáticamente con `python manage.py generar_docs` (2026-11-18). No lo edites a mano._

Todas las rutas cuelgan de `/api/`. Detalle de uso y ejemplos en [api.md](api.md).

| Ruta | Vista | Descripción |
|---|---|---|
| `/api/auth/cambiar-contrasena/` | `views.change_password_view` | The logged-in user chooses a new password (also the forced change of the first login). |
| `/api/auth/csrf/` | `views.csrf` | Gives the frontend a CSRF token to send in the X-CSRFToken header. |
| `/api/auth/login/` | `views.login_view` |  |
| `/api/auth/logout/` | `views.logout_view` |  |
| `/api/auth/me/` | `views.me` |  |
| `/api/bitacora/` | `api.entries` |  |
| `/api/bitacora/catalogos/` | `api.catalogs` |  |
| `/api/checklists/` | `checklists_api.checklists` |  |
| `/api/checklists/<pk>/` | `checklists_api.checklist_detail` |  |
| `/api/checklists/catalogos/` | `checklists_api.catalogs` | Options for the checklist form: the units (only the assigned ones for an operator) that are fit |
| `/api/dashboard/` | `dashboard_api.dashboard` |  |
| `/api/diagnosticos/` | `diagnoses_api.diagnoses` |  |
| `/api/diagnosticos/<pk>/` | `diagnoses_api.diagnosis_detail` |  |
| `/api/diagnosticos/catalogos/` | `diagnoses_api.catalogs` | Options for the diagnosis form: severities and the reports that have no diagnosis yet |
| `/api/health/` | `urls.health` | Simple endpoint to verify the API is up. |
| `/api/kardex/<pk>/` | `kardex_api.kardex` | Header of the kardex of a unit (data, summary, preventive plans); with format=pdf, the whole kardex. |
| `/api/kardex/<pk>/cambios/` | `kardex_sections.kardex_cambios` | The kardex section «Cambios de datos» of one unit: filters, order, pages and PDF. |
| `/api/kardex/<pk>/checklists/` | `kardex_sections.kardex_checklists` | The kardex section «Checklists» of one unit: filters, order, pages and PDF. |
| `/api/kardex/<pk>/fallas/` | `kardex_sections.kardex_fallas` | The kardex section «Fallas» of one unit: filters, order, pages and PDF. |
| `/api/kardex/<pk>/linea-de-tiempo/` | `kardex_api.timeline` | General timeline of the kardex of a unit: every event by date, filtered by type. |
| `/api/kardex/<pk>/mantenimientos/` | `kardex_sections.kardex_mantenimientos` | The kardex section «Mantenimientos» of one unit: filters, order, pages and PDF. |
| `/api/kardex/<pk>/operadores/` | `kardex_sections.kardex_operadores` | The kardex section «Operadores y mecánicos» of one unit: filters, order, pages and PDF. |
| `/api/kardex/<pk>/refacciones/` | `kardex_sections.kardex_refacciones` | The kardex section «Refacciones cambiadas» of one unit: filters, order, pages and PDF. |
| `/api/mantenimientos/` | `maintenances_api.maintenances` |  |
| `/api/mantenimientos/<pk>/` | `maintenances_api.maintenance_detail` |  |
| `/api/mantenimientos/catalogos/` | `maintenances_api.catalogs` | Options for the maintenance form. |
| `/api/notificaciones/` | `api.notifications` |  |
| `/api/notificaciones/leer/` | `api.mark_read` |  |
| `/api/notificaciones/limpiar/` | `api.clear_read` |  |
| `/api/notificaciones/resumen/` | `api.summary` |  |
| `/api/preventivo/catalogos/` | `preventive_api.catalogs` |  |
| `/api/preventivo/planes/` | `preventive_api.plans` |  |
| `/api/preventivo/planes/<pk>/` | `preventive_api.plan_detail` |  |
| `/api/preventivo/vencimientos/` | `preventive_api.due` | What is due, most urgent first. The counts cover everything; the list can be filtered. |
| `/api/refacciones/` | `spare_parts_api.spare_parts` |  |
| `/api/refacciones/<pk>/` | `spare_parts_api.spare_part_detail` |  |
| `/api/refacciones/<pk>/foto/` | `spare_parts_api.spare_part_photo` | The photo of a part (optional). Only managers use the spare parts, so only they can see, |
| `/api/refacciones/<pk>/movimientos/` | `spare_parts_api.spare_part_movements` | The manager registers pieces that came in, or corrects the stock after a count. |
| `/api/reportes-fallas/` | `reports_api.reports` |  |
| `/api/reportes-fallas/<pk>/` | `reports_api.report_detail` |  |
| `/api/reportes-fallas/<pk>/evidencias/<evidence_id>/` | `reports_api.evidence_file` | One photo of a report, only for people who can see that report. |
| `/api/reportes-fallas/<pk>/mecanicos/` | `reports_api.report_mechanics` | The manager assigns a mechanic to a report. |
| `/api/reportes-fallas/<pk>/mecanicos/<assignment_id>/` | `reports_api.report_mechanic_detail` | The manager ends the assignment of a mechanic to a report. |
| `/api/reportes-fallas/catalogos/` | `reports_api.catalogs` | Options for the report form and the list filter: units and statuses (and, for managers, |
| `/api/trabajadores/` | `workers_api.workers` |  |
| `/api/trabajadores/<pk>/` | `workers_api.worker_detail` |  |
| `/api/trabajadores/<pk>/foto/` | `workers_api.worker_photo` | GET: the photo. The manager can see anyone's; everyone else only their own. |
| `/api/trabajadores/catalogos/` | `workers_api.catalogs` | Options for the worker form: sexes, roles, phone codes and contact limit. |
| `/api/ubicaciones/estados/` | `api.states` |  |
| `/api/ubicaciones/municipios/` | `api.municipalities` |  |
| `/api/unidades/` | `units_api.units` |  |
| `/api/unidades/<pk>/` | `units_api.unit_detail` |  |
| `/api/unidades/catalogos/` | `units_api.catalogs` | Options for the unit form: brands, models and the operators without a unit (plus the current one). |
