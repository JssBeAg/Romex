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
- **Fichas de un registro**: `format=pdf` en el detalle de `reportes-fallas/<id>/`, `diagnosticos/<id>/`, `mantenimientos/<id>/`, `checklists/<id>/` y `refacciones/<id>/`. El del kardex está en `kardex/<id>/` (completo) y en cada una de sus secciones.
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

## Kardex de una unidad

Solo para el gerente. `kardex/<id>/` devuelve el encabezado: `unit`, `summary` y `preventive`. Con `format=pdf` devuelve el **kardex completo**: una tabla por sección, sin filtros.

Cada sección es una lista con el comportamiento de las demás (`q`, `date_from`/`date_to`, `order`, `page`/`page_size`, `format=pdf`, que respeta los filtros), y sus filas traen cada dato en su campo:

| Ruta | Clave | Orden (`order`) | Filtros propios | Campos de cada fila |
|---|---|---|---|---|
| `kardex/<id>/mantenimientos/` | `maintenances` | `date`, `mileage`, `cost` | `tipo` (`preventivo`/`correctivo`), `terminada` (`si`/`no`, solo correctivos) | `folio`, `date`, `service_type`, `plan`, `mileage`, `cost`, `people`, `parts` (`label`, `quantity`), `repair_completed` (`null` en preventivos), `report`, `diagnosis` (`id`, `label`), `failure`, `cause`, `observations` |
| `kardex/<id>/fallas/` | `faults` (+ `statuses`) | `date`, `status` | `estatus` (id) | `folio`, `date`, `reported_by`, `location`, `description`, `status`, `mechanics`, `diagnosis` (`cause`, `severity`, `requires_repair`, `unit_operable`…) o `null` |
| `kardex/<id>/checklists/` | `checklists` | `date`, `mileage` | `resultado` (`ok`/`fallas`) | `folio`, `date`, `operator`, `mileage`, `ok`, `failed_items`, `trip_description`… |
| `kardex/<id>/refacciones/` | `parts` | `last_date`, `part`, `pieces`, `times` | — | `label`, `pieces`, `times`, `last_date` |
| `kardex/<id>/operadores/` | `people` | `start_date`, `end_date`, `person` | `rol` (`operador`/`mecanico`) | `role`, `person`, `start_date`, `end_date` (`null` = actual), `report` |
| `kardex/<id>/cambios/` | `changes` (+ `users`) | `moment`, `field` | `usuario` (id) | `moment`, `date`, `field`, `old`, `new`, `user` |
| `kardex/<id>/linea-de-tiempo/` | `events` (+ `types`) | `date` | `tipo` (`maintenance`, `report`, `operator`…) | `type`, `type_label`, `date`, `title`, `detail` (una línea), `link` |

Por defecto, cada sección viene ordenada de lo más reciente a lo más antiguo. Una unidad que no existe responde 404, y un rol que no es gerente, 403. En la línea de tiempo, los eventos `operator` dicen «Asignada a *operador*» y «Operador *operador* dejó la unidad», con el periodo en `detail`.

## Operador de una unidad

Cada unidad devuelve `current_operator` (la asignación abierta: `{id, operator: {id, label}, start_date, end_date: null}`, o `null`) y `operators`, el historial completo, del más reciente al más antiguo.

El alta (`POST unidades/`) y la edición (`PUT unidades/<id>/`) aceptan, opcionales:

| Campo | Qué hace |
|---|---|
| `end_operator: {assignment_id, end_date}` | Termina la asignación abierta de la unidad (fecha de fin; no se borra la fila) |
| `new_operator: {operator_id, start_date}` | Abre una asignación nueva |

Los dos juntos son un **cambio de operador**, que se guarda en una sola transacción. Los errores llegan en `errors.operator` (400, o 200 con `?validar=1`). Por ejemplo, la unidad ya tiene operador, el operador ya tiene otra unidad, fechas futuras o una fecha de fin anterior al inicio. Si la base rechaza la asignación porque otra persona la hizo antes, también responde 400 en `errors.operator`, con quién la tiene. Desactivar (`is_active: false`) una unidad que conserva su operador responde 400 en `errors.is_active`.

`unidades/catalogos/` devuelve en `operators` los operadores activos **sin unidad abierta**, cada uno con `current: false`. Con `?unidad=<id>` incluye además al operador actual de esa unidad, con `current: true`.

## Unidades aptas en el checklist

`checklists/catalogos/` devuelve `units` (las aptas para operar: la que el operador tiene asignada ahora, o todas las activas para el gerente) y `not_operable` (las que se dejan fuera por no estar aptas, para que el formulario lo explique). Crear un checklist de una unidad no apta responde 400 con `errors.unit_id`.

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
