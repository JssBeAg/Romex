# API

Todas las rutas cuelgan de `/api/`, responden JSON y usan la sesión (cookie) más el encabezado `X-CSRFToken` en los cambios. La lista completa está en [referencia-rutas.md](referencia-rutas.md).

## Errores

| Código | Significa |
|---|---|
| 400 | Datos no válidos: `{"errors": {"campo": ["mensaje"]}}` |
| 401 | Sin sesión |
| 403 | Sin permiso; con `must_change_password: true` si debe cambiar la contraseña |
| 404 | No existe, o la persona no puede verlo |
| 409 | Conflicto: no se puede borrar (tiene historial), existencias insuficientes… |
| 423 | Cuenta bloqueada temporalmente |

Los mensajes `error` y `errors` están en español.

## Validación sin guardar

Cualquier alta o edición acepta `?validar=1`: devuelve `{"errors": {...}}` (vacío si todo está bien) y **no guarda nada**.

## Listas

Todas las listas aceptan, además de sus filtros propios:

| Parámetro | Ejemplo | Efecto |
|---|---|---|
| `q` | `q=E-1` | Búsqueda de texto |
| `order` | `order=-date` | Orden por una columna permitida; `-` para descendente |
| `date_from`, `date_to` | `2026-10-01` | Rango de fechas (en las listas con fecha) |
| `page`, `page_size` | `page=2&page_size=50` | Página (tamaño 1–100, por defecto 20) |
| `format` | `format=pdf` | Todo el resultado filtrado como PDF, sin paginar |

Respuesta: `{"<clave>": [...], "pagination": {"page", "pages", "page_size", "total"}}`. Una página fuera de rango devuelve la última.

| Lista | Clave | Orden permitido | Filtros propios |
|---|---|---|---|
| `reportes-fallas/` | `reports` | `date`, `status`, `unit`, `location`, `reported_by` | `status_id`, `unit_id` |
| `checklists/` | `checklists` | `date`, `unit`, `completed_by`, `mileage` | `unit_id`, `problems=1` |
| `diagnosticos/` | `diagnoses` | `date`, `unit`, `severity`, `diagnosed_by` | `severity_id`, `unit_id` |
| `mantenimientos/` | `maintenances` | `date`, `unit`, `service_type`, `cost`, `mileage` | `service_type_id`, `unit_id` |
| `unidades/` | `units` | `economic_number`, `brand`, `model`, `mileage` | `status` (`active`/`inactive`), `brand_id` |
| `refacciones/` | `spare_parts` | `name`, `stock`, `min_stock`, `price` | `status`, `low=1` (también devuelve `low_stock_count`) |
| `trabajadores/` | `workers` | `enrollment_id`, `name`, `role`, `is_active` | `role_id`, `status` |
| `preventivo/planes/` | `plans` | `name`, `every_km`, `every_days`, `is_active` | `status` |
| `notificaciones/` | `notifications` | `date` | `unread=1`, `kind` |
| `bitacora/` | `entries` | `timestamp`, `user`, `action`, `table` | `user_id`, `action`, `table`, `record_id` (paginación propia: `total`, `page`, `pages`) |

## PDF

- **Listas**: `format=pdf` en cualquiera de las anteriores, más `preventivo/vencimientos/` y `bitacora/` (esta última, las 2000 líneas más recientes).
- **Fichas de un registro**: `format=pdf` en el detalle de `reportes-fallas/<id>/`, `diagnosticos/<id>/`, `mantenimientos/<id>/`, `checklists/<id>/`, `refacciones/<id>/` y `kardex/<id>/`.
- **Dashboard**: `dashboard/?months=6&format=pdf`.

Cada PDF respeta los permisos de quien lo pide (solo exporta lo que podría ver) y deja una línea en la bitácora.

## Cuentas

| Ruta | Método | Descripción |
|---|---|---|
| `auth/csrf/` | GET | Entrega el token CSRF |
| `auth/login/` | POST | `{enrollment_id, password}`; 401 credenciales incorrectas, 423 cuenta bloqueada |
| `auth/logout/` | POST | Cierra la sesión |
| `auth/me/` | GET | Usuario actual (incluye `must_change_password`) |
| `auth/cambiar-contrasena/` | POST | `{current_password, new_password, confirm_password}` (admite `?validar=1`) |

## Teléfono y contactos de un trabajador

Los trabajadores (`trabajadores/…`, solo gerente) traen:

- `phone_code` (`{id, iso, code, label}`, o `null`), `phone_number` (solo dígitos) y `phone_display` (`"+52 8441234567"`).
- `contacts`: lista de `{id, kind, phone_code_id, phone_code, value, display, label, contact_name}`. `kind` es `telefono` o `correo`; en un correo `phone_code_id` es `null`.

Para guardar (POST/PUT, admite `?validar=1`): `phone_code_id` y `phone_number` son obligatorios. `contacts` es **opcional**: si no viene, los contactos quedan como están; si viene, **reemplaza** la lista completa (los que traen `id` se actualizan, los demás se crean y los que faltan se borran). Máximo 3. Los errores llegan en `errors.contacts` como una lista de textos, cada uno con la etiqueta del contacto (`"Número 2: …"`).

`trabajadores/catalogos/` agrega `phone_codes` (solo los activos) y `max_contacts`.

`kardex/<id>/` (solo gerente) trae `events`; los que tienen `type: "change"` son los cambios de datos de la unidad (`title` dice quién, `detail` la hora y *campo: antes → después*). Los eventos `maintenance` traen en `detail` (varias líneas) refacciones, responsables, causa y observaciones, y la respuesta incluye `parts_used` (`label`, `pieces`, `times`, `last_date`).

## Unidades aptas en el checklist

`checklists/catalogos/` devuelve `units` (las aptas para operar: las asignadas al operador, o todas las activas para el gerente) y `not_operable` (las que se dejan fuera por no estar aptas, para que el formulario lo explique). Crear un checklist de una unidad no apta responde 400 con `errors.unit_id`.

## Descripciones que acompañan a cada registro

- `diagnosticos/…`: `fault_report` trae además `description` (lo que escribió el operador). `diagnosticos/catalogos/` incluye `description` en cada reporte.
- `mantenimientos/…`: `diagnosis` trae además `detailed_cause` (la descripción del diagnóstico), o `null` en un preventivo. `mantenimientos/catalogos/` incluye `detailed_cause` en cada diagnóstico.
- Las fichas PDF de diagnóstico y de mantenimiento muestran esas descripciones.

## Domicilio de un trabajador

El trabajador trae `address`: `{state, municipality, neighborhood, street, exterior_number, interior_number}`. `state` y `municipality` son nombres del INEGI (texto); `neighborhood` (colonia) y `street` (calle) son **texto libre** (máx. 150 caracteres).

Para guardar: `address.state` y `address.municipality` (obligatorios, nombres que existan en el INEGI), `address.neighborhood`, `address.street` y `address.exterior_number` obligatorios; `address.interior_number` opcional. Los errores llegan como `errors.state`, `errors.municipality`, `errors.neighborhood`, `errors.street`, `errors.exterior_number`.

`ubicaciones/estados/` y `ubicaciones/municipios/?estado=<nombre>` (solo gerente) sirven las listas del INEGI: `{"options": ["…"]}`; si el INEGI no responde, **503** con `{"error": "…"}`. La placa de una unidad manda `plate.state` (nombre) y su error llega como `errors.plate_state`; las unidades devuelven `state` como texto.

## Fotografía de una refacción

| Ruta | Método | Descripción |
|---|---|---|
| `refacciones/<id>/foto/` | GET | La imagen (JPG). Solo gerente; 404 si no tiene |
| `refacciones/<id>/foto/` | POST | Solo gerente. Multipart con el campo `photo`. Admite `?validar=1`. Devuelve `{"spare_part": …}`; 400 con `{"errors": {"photo": […]}}` si no sirve |
| `refacciones/<id>/foto/` | DELETE | Solo gerente. Quita la fotografía (si no hay, no pasa nada). Devuelve `{"spare_part": …}` |

Las refacciones traen `photo_url` (`refacciones/7/foto/?v=<código>`, que cambia con cada foto nueva) o `null` si no tienen.

## Fotografía de un trabajador

| Ruta | Método | Descripción |
|---|---|---|
| `trabajadores/<id>/foto/` | GET | La imagen (JPG). Gerente: cualquiera; los demás: solo la propia (403 en otro caso); 404 si no tiene |
| `trabajadores/<id>/foto/` | POST | Solo gerente. Multipart con el campo `photo`. Admite `?validar=1`. Devuelve `{"worker": …}`; 400 con `{"errors": {"photo": […]}}` si no sirve |
| `trabajadores/<id>/foto/` | DELETE | Solo gerente. Quita la fotografía (si no hay, no pasa nada). Devuelve `{"worker": …}` |

El trabajador (`trabajadores/…`) y el usuario actual (`auth/me/`) traen `photo_url`: la ruta de la foto con una versión (`trabajadores/7/foto/?v=<código>`) que cambia con cada foto nueva, o `null` si no tiene.

## Notificaciones

| Ruta | Método | Descripción |
|---|---|---|
| `notificaciones/` | GET | Página de notificaciones propias; incluye `unread` |
| `notificaciones/resumen/` | GET | `{"unread": n}` (la campana lo consulta cada minuto) |
| `notificaciones/leer/` | POST | `{"ids": [1, 2]}` o `{}` para todas |
| `notificaciones/limpiar/` | POST | Borra las ya leídas |

## Dashboard

`GET dashboard/?months=3|6|12` (solo gerente). Devuelve `cards`, `monthly`, `report_statuses`, `top_units_by_cost`, `top_units_by_reports`, `top_parts`, `mechanic_workload` y `low_stock`.
