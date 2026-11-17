# Pruebas y CI

Hay dos niveles: **pruebas del backend** (API, reglas de negocio) y **pruebas de navegador** (las pantallas, con un navegador real).

## Pruebas del backend

### Qué se prueba

El backend tiene **220 pruebas automáticas** en `backend/tests/`. Llaman a la API igual que lo hace la interfaz (con sesión, roles y JSON), así que cubren las reglas de punta a punta, no solo funciones sueltas.

| Archivo | Cubre |
|---|---|
| `test_security.py` | Inicio de sesión, bloqueo a los 5 intentos y desbloqueo, cambio obligatorio y voluntario de contraseña, validación sin guardar, caducidad de sesión |
| `test_listing.py` | Paginación, tamaños y páginas fuera de rango, orden, búsqueda, filtros, PDF de listas, permisos del PDF y su registro en la bitácora |
| `test_workflow.py` | Reporte → asignación → diagnóstico → mantenimiento → reparado: estatus calculado, historial, avisos, restricciones por rol y por unidad |
| `test_inventory.py` | Existencias, descuento y devolución por mantenimiento, no usar más de lo que hay, stock bajo y su aviso, entradas y ajustes, desactivar en lugar de borrar |
| `test_preventive.py` | Sin historial / al corriente / próximo / vencido, planes por modelo, planes inactivos, aviso único al gerente |
| `test_notifications.py` | Solo las propias, conteo, marcar leídas, limpiar, sin repetir mientras no se lean |
| `test_photos.py` | Fotografías de perfil: formatos y tamaños, recorte a cuadro, eliminación de metadatos GPS/EXIF, nombre aleatorio, permisos (gerente / dueño / otros), reemplazo y borrado de archivos, bitácora |
| `test_inegi.py` | Estados y municipios del INEGI (con el servicio simulado): los 32 estados, municipios por estado, solo gerente, caché, aviso 503 cuando no responde, nombres de campo del servicio, tablas viejas eliminadas, domicilio nuevo rechazado con el INEGI caído y domicilio existente que sigue guardando, estado de la placa |
| `test_audit_visibility.py` | Qué ve el gerente en la bitácora (sin sesiones ni cuentas de administradores, con sus cambios a la operación), filtros, avisos de bloqueo y botones del panel de administración junto al código telefónico |
| `test_address_text.py` | Domicilio con estado y municipio del INEGI y colonia y calle como texto: se guardan tal cual, avisos por campo, estado o municipio inexistente rechazado, validación sin guardar, edición y tablas `colonias`/`calles` eliminadas |
| `test_descriptions.py` | La descripción del reporte llega con el diagnóstico (y en su catálogo); la descripción del diagnóstico, con el mantenimiento correctivo (y en su catálogo); preventivo sin diagnóstico; las fichas PDF se generan |
| `test_operability.py` | Unidad no apta para operar (diagnóstico «no puede operar» con reporte abierto): sale del formulario de checklist (operador y gerente) y se lista aparte, se rechaza en el servidor, vuelve al repararse o al corregir/eliminar el diagnóstico, y un checklist anterior sigue editable |
| `test_kardex_changes.py` | Cambios de datos de la unidad en su kardex: antes y después, quién y cuándo, sin líneas si no cambió nada, orden, sin mezclar otras unidades, PDF y acceso solo del gerente |
| `test_part_photos.py` | Fotografías de refacciones: proporciones (sin recorte, máx. 800 px, sin agrandar), formatos y tamaños, metadatos, nombre aleatorio, solo gerente, reemplazo y borrado de archivos, bitácora, panel sin subida cruda |
| `test_contacts.py` | Catálogo de códigos (carga, códigos compartidos, solo activos, CHECK de dígitos), teléfono principal con código (dígitos, 15 dígitos, separadores, obligatorio), contactos adicionales (etiqueta por defecto, máximo 3, duplicados, correos, sincronizar por `id`, ajeno, validación sin guardar, restricciones de la base, bitácora, borrado en cascada, solo gerente) |
| `test_dashboard_audit_roles.py` | Dashboard y sus periodos, bitácora (quién/qué, sin contraseñas), matriz de permisos por rol |

`tests/base.py` crea un usuario por rol y trae ayudantes (`make_unit`, `make_part`, `make_report`) para armar datos por la API.

### Cómo correrlas

Con Docker (ya hay base PostgreSQL; el usuario de la base puede crear la base de pruebas):

```bash
docker compose exec backend python manage.py test tests
```

Sin Docker, con un PostgreSQL local y las variables `POSTGRES_*` de `.env`:

```bash
cd backend
python manage.py test tests            # todas
python manage.py test tests.test_inventory   # un archivo
```

Django crea una base temporal (`test_romex`) y la borra al terminar; tus datos no se tocan. Tardan unos 10 segundos. Durante las pruebas se usa un *hash* de contraseñas rápido (solo cuando el comando es `test`).

### Reglas para escribir pruebas nuevas

- Cada regla de negocio nueva lleva su prueba en el archivo que corresponda (o uno nuevo `test_*.py`).
- Prueba por la API y con el rol correcto; incluye el caso que debe **fallar** (permiso, validación).
- Los avisos usan `on_commit`: envuelve la llamada en `with self.captureOnCommitCallbacks(execute=True):`.
- Las fechas se arman con `today()` de `tests/base.py` (hora de Ciudad de México, como el servidor).
- No dependas del orden alfabético de la base (cambia con la *collation*): usa nombres ASCII propios.
- Si cambias un valor documentado (por ejemplo 5 intentos / 15 minutos), cambia la prueba **y** el documento.

## Pruebas de navegador (frontend)

Están en `frontend/e2e/` y usan [Playwright](https://playwright.dev). Abren un Chromium real, entran con usuarios de prueba y hacen lo que haría una persona. Son **72 pruebas**:

| Archivo | Cubre |
|---|---|
| `01-acceso.spec.ts` | Contraseña incorrecta, entrar y salir, pantallas internas sin sesión, mostrar contraseña, menú por rol, el operador no entra a pantallas del gerente |
| `02-bloqueo.spec.ts` | 5 intentos fallidos bloquean la cuenta, aun con la contraseña correcta |
| `03-cambio-obligatorio.spec.ts` | Cuenta con cambio obligatorio: solo ve esa pantalla, errores en vivo, ventana de errores, cambia y entra |
| `04-reportes.spec.ts` | El operador crea un reporte, otro operador no lo ve, el gerente recibe el aviso y lo marca leído, asigna mecánico, el mecánico lo ve |
| `05-listas.spec.ts` | Paginación, orden por columna, búsqueda, filtro, exportar a PDF (se abre en una pestaña nueva y es un PDF válido) y carga + PDF de las 9 listas del gerente |
| `06-dashboard.spec.ts` | Indicadores y gráficas, «Reportes abiertos» contra la lista, cambio de periodo, PDF |
| `07-celular-y-tema.spec.ts` | Pantallas en 375 px sin desborde, **todas las tablas alcanzables**, botones de acción alcanzables, modo oscuro (se recuerda al recargar) |
| `08-fotos.spec.ts` | Iniciales sin fotografía, archivo inválido rechazado en pantalla, subir y ver la foto (lista y encabezado), quién puede pedirla, quitarla |
| `11-ciudades.spec.ts` | Estados y municipios del INEGI (simulado): 32 estados, cambiar de estado reemplaza los municipios, colonia/calle son texto y la placa también elige estado |
| `12-domicilio.spec.ts` | Alta de trabajador con el +52 por defecto sin tocarlo (se guarda sin «Elige una opción válida») y con colonia y calle escritas a mano; se comprueba abriendo al trabajador |
| `15-kardex-cambios.spec.ts` | Se corrige el kilometraje de una unidad por pantalla y aparece en su kardex como «Cambio de datos» con el antes, el después y quién |
| `14-unidad-no-apta.spec.ts` | Una unidad diagnosticada como no operable desaparece del formulario de checklist de su operador con la explicación, y la unidad apta de otro operador sí aparece |
| `13-descripciones.spec.ts` | Reporte → asignación → diagnóstico → mantenimiento por pantalla: el mecánico lee la descripción del reporte al diagnosticar y la del diagnóstico al crear el mantenimiento; el gerente ve ambas en la ficha |
| `10-fotos-refacciones.spec.ts` | Ícono sin foto, archivo inválido rechazado en pantalla, crear con foto y verla en la lista, quitarla al editar, sin sesión no se puede pedir |
| `09-contactos.spec.ts` | Teléfono principal con código (etiquetas propias y número que no se encoge), solo dígitos, agregar "Número 2" con el nombre de la persona (se ve en la lista), avisos antes de guardar, máximo de 3 y borrado |

### Cómo correrlas

Necesitan el sistema levantado (interfaz `:3000`, API `:8000`) y los datos de prueba:

```bash
docker compose up -d
docker compose exec backend python manage.py seed_e2e   # crea/restablece G1, M1, O1, O2, L1, F1 y 2 unidades (contraseña Clave12345x)

cd frontend
npm install
npx playwright install chromium     # solo la primera vez
npm run test:e2e
```

- **Estados y municipios**: las pruebas no llaman al INEGI real. Levanta `python manage.py inegi_falso` (puerto 8777) y arranca el backend con `INEGI_API_URL=http://localhost:8777/wscatgeo/v2` (las pruebas del backend ya lo simulan solas).
- **Corre `seed_e2e` antes de cada corrida**: restablece las cuentas que las pruebas consumen (el bloqueo de `L1` y el cambio de contraseña de `F1`). Solo funciona con `DJANGO_DEBUG=1`.
- Si ya tienes un Chromium instalado: `PW_CHROMIUM=/ruta/a/chromium npm run test:e2e`.
- Una sola: `npx playwright test 03`. Con ventana: `npx playwright test --headed`.
- Si algo falla, queda una captura y un *trace* en `frontend/test-results/` (`npx playwright show-trace <archivo>`).

### Reglas para escribir pruebas de navegador

- Busca por lo que ve la persona (rol, etiqueta, texto), no por clases CSS; las excepciones (`.kpi`, `.field-error`, `.table-scroll`) ya están en uso.
- **El mensaje de error de un formulario es `p[role='alert']`**: no uses `getByRole("alert")` a secas, porque Next.js tiene un anunciador de rutas invisible con ese mismo rol y la prueba pasaría siempre.
- Tras `goto("/login")` espera `networkidle` (el ayudante `login` ya lo hace): enviar el formulario antes de que la página termine de cargar no hace nada.
- Después de «Cerrar sesión» espera a estar en `/login` antes de volver a entrar.
- Si una prueba cambia datos que otra necesita, déjalas en el mismo archivo con `test.describe.serial` o restablécelos en `seed_e2e`.

## CI (GitHub Actions)

`.github/workflows/ci.yml` corre en cada *push* y *pull request*:

1. **Backend**: PostgreSQL 16 real, verifica que no falten migraciones (`makemigrations --check`), migra una base vacía, corre las pruebas y comprueba que `docs/` generado esté al día.
2. **Frontend**: `npm run typecheck` y `npm run build`.
3. **Docker Compose + navegador**: levanta todo con `docker compose up --build`, corre las pruebas del backend dentro del contenedor, prepara los datos con `seed_e2e` y ejecuta las pruebas de Playwright. Si fallan, sube el informe y las capturas como artefacto.

Si el paso de documentación falla, ejecuta `python manage.py generar_docs` y sube los cambios de `docs/`.

## Lo que aún no cubre

- Solo se prueba en Chromium de escritorio y a 375 px de ancho; no hay Firefox ni Safari.
- Del flujo de mecánico (diagnóstico y mantenimiento) y del inventario solo hay pruebas de backend; las pantallas de esos formularios no se recorren de punta a punta.
- Pruebas de carga.
- El trabajo de `docker compose` solo se puede comprobar donde haya Docker (el CI lo hace).
