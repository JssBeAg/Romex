# Historial de cambios

Cada entrega agrega una entrada arriba. Formato: fecha, qué cambió y qué hay que hacer al actualizar.

## Entrega 21 — Estados y municipios desde la API del INEGI

**Cambios**
- Los estados y municipios ya **no están en la base de datos**: se consultan al servicio web del **INEGI** (Catálogo Único de Claves Geoestadísticas) cada vez que un formulario los necesita. El país es siempre **México**.
- El **domicilio** guarda el estado y el municipio como texto (como ya hacía con colonia y calle). La **placa** de una unidad guarda también el estado como texto. El servidor comprueba con el INEGI que existan.
- Si el INEGI **no responde**, los menús avisan y no se puede guardar un domicilio ni una placa nuevos; un domicilio ya guardado se puede seguir editando mientras no cambie su estado ni su municipio.
- Se eliminan las tablas `paises`, `estados` y `ciudades`. La migración conserva el estado y el municipio de cada domicilio y el estado de cada placa. **No se puede deshacer** una vez aplicada.
- Nuevo comando `inegi_falso` (un INEGI de mentira para desarrollar y probar sin internet) y variables `INEGI_API_URL` / `INEGI_TIMEOUT`. El CI lo levanta solo.
- El formulario de trabajadores ya no tiene lista de países (muestra «México») y «Ciudad» ahora se llama «Municipio». El panel de administración también.
- Pruebas: 220 de backend y 72 de navegador.

**Al actualizar**
- Hay migraciones con datos (`locations 0015–0018`, `fleet 0043–0045`): **no hace falta borrar la base**, solo `python manage.py migrate`. Haz un respaldo antes: no se pueden deshacer.
- El servidor necesita salida a internet hacia `gaia.inegi.org.mx`.

## Entrega 20 — El kardex muestra el trabajo físico de los mantenimientos

**Cambios**
- Cada mantenimiento del **kardex** ahora trae lo que se le hizo físicamente a la unidad: **quién lo realizó**, las **refacciones cambiadas** (refacción × cantidad, o «Sin refacciones»), las observaciones y, en los correctivos, la **falla reportada**, la **causa del diagnóstico** y si la **reparación quedó terminada**. Los reportes y diagnósticos también muestran su descripción y causa.
- Nueva tabla **Refacciones cambiadas** en el kardex y su PDF: piezas totales, veces y fecha del último cambio por refacción.
- PDF: la flecha «→» ya se imprime (antes salía «?») y los renglones de varias líneas se ven en varias líneas.
- 4 pruebas de backend y 1 de navegador nuevas (ahora 222 y 72).

**Al actualizar**
- Sin migraciones: **no hace falta borrar la base**.

## Entrega 19 — El kardex muestra los cambios de la unidad

**Cambios**
- En el **kardex de cada unidad** ahora aparecen las veces que se **corrigió o cambió su información** (número económico, modelo, kilometraje, activa o no): una línea «Cambio de datos» con *campo: antes → después*, quién lo hizo y a qué hora. También sale en el PDF del kardex.
- Salen de la bitácora, así que desde ahora todo cambio queda en el kardex automáticamente. Los cambios **anteriores a esta entrega también aparecen**, porque la bitácora ya los tenía.
- Un guardado sin cambios no genera línea. Placas y operadores no se repiten (ya tienen sus propias líneas).
- 7 pruebas de backend y 1 de navegador nuevas (ahora 218 y 71).

**Al actualizar**
- Sin migraciones: **no hace falta borrar la base**.

## Entrega 18 — Las unidades no aptas no aparecen en el checklist

**Cambios**
- Un checklist se hace antes de salir a operar, así que ahora **una unidad no apta para operar no aparece en el formulario de checklist** (ni para el operador ni para el gerente), y el servidor tampoco la acepta.
- **Cuándo no está apta:** si tiene un diagnóstico que dice que **no puede seguir operando** y su reporte sigue abierto. **Vuelve a estar apta** al quedar reparada (o con «sin reparación necesaria»), o si ese diagnóstico se corrige o se elimina. No hay que marcarla a mano.
- El formulario explica qué unidades quedaron fuera y por qué. Si el operador se queda sin unidades aptas, dice «No tienes unidades aptas para operar ahora».
- Un checklist que ya existe se puede seguir editando aunque su unidad haya dejado de ser apta.
- 10 pruebas de backend y 5 de navegador nuevas (ahora 211 y 70). Las pruebas de navegador ahora limpian los diagnósticos de sus unidades al sembrar.

**Al actualizar**
- Sin migraciones: **no hace falta borrar la base**.

## Entrega 17 — Descripciones a lo largo del flujo

**Cambios**
- **Diagnóstico**: ahora se ve la **descripción del reporte** (lo que escribió el operador): en el formulario al elegir el reporte, al editarlo, en la ficha de solo lectura del gerente y en el PDF.
- **Mantenimiento**: ahora se ve la **descripción del diagnóstico** (causa detallada): en el formulario al elegir el diagnóstico (correctivo), al editarlo, en la ficha de solo lectura y en el PDF. Un preventivo no la lleva porque no tiene diagnóstico.
- El campo «Causa detallada» del diagnóstico se llama ahora «Descripción del diagnóstico (causa detallada)».
- Las listas no cambian (se mantienen compactas).
- 6 pruebas de backend y 5 de navegador nuevas (ahora 201 y 65).

**Al actualizar**
- Sin migraciones: **no hace falta borrar la base**.

## Entrega 16 — Los PDF se abren en pantalla

**Cambios**
- Todos los botones de PDF (listas, dashboard, bitácora, kardex y fichas de cada registro) ahora **abren el PDF en una pestaña nueva** en lugar de descargarlo. Desde el visor del navegador se puede imprimir o guardar.
- Las fichas dicen **«Ver ficha en PDF»** (antes «Descargar ficha en PDF»).
- Si el navegador bloquea las ventanas emergentes, el PDF se descarga como antes. Si falla la generación, la pestaña se cierra y sale el aviso de error de siempre.
- Las 3 pruebas de navegador que esperaban una descarga ahora esperan la pestaña nueva (siguen siendo 60 de navegador y 195 de backend).

**Al actualizar**
- Solo cambia el frontend: **no hace falta borrar la base** ni hay migraciones nuevas.

## Entrega 15 — Domicilio con colonia y calle como texto, y correcciones

**Cambios**
- **Domicilio**: se conservan las tablas **País → Estado → Ciudad** (menús en cascada). **Colonia y calle ya no son tablas**: se escriben a mano dentro del domicilio. Con esto se puede registrar un domicilio en **cualquier ciudad** del país (antes solo Saltillo tenía colonias). Aplica al formulario de Trabajadores y al panel de administración.
- **Error «Seleccione uno válido» al registrar un trabajador** (rol de gerente): el menú mostraba México +52 como elegido, pero el valor no se enviaba. Ahora México +52 queda **realmente elegido** al abrir el formulario (se puede cambiar).
- **Panel de administración**: al agregar un usuario ya no aparecen los botones (cambiar, añadir, eliminar, ver) junto al **rol**, y el código telefónico empieza en **México +52**.
- 12 pruebas de backend y 1 de navegador nuevas (ahora 195 y 60). La prueba que exigía el botón «ver» del rol se invirtió.

**Al actualizar**
- Migraciones nuevas: `locations 0012`, `0013` y `0014`. Convierten los domicilios existentes: cada uno conserva su ciudad y el **nombre** de su colonia y de su calle, que pasan a texto. **No hace falta borrar la base.**
- Se eliminan las tablas `colonias` y `calles`. **No se puede volver atrás** una vez aplicadas con datos (los nombres sí quedan en `domicilios`).
- Los nombres de colonia/calle del catálogo anterior (solo Saltillo, calles de ejemplo) ya no se ofrecen como lista.

## Entrega 14 — Ciudades de todos los estados

**Novedades**
- Los 32 estados de México ahora traen **todas sus ciudades**: **2,478 municipios** oficiales de INEGI (antes solo Coahuila tenía las suyas, 38). En el sistema una «ciudad» es un municipio, así que no se agregó ningún nivel nuevo: el menú de **Ciudad** del domicilio (formulario de Trabajadores y panel de administración) ya muestra las de cada estado.
- Dos pares de municipios de Oaxaca se llaman igual (INEGI los distingue por distrito): `San Juan Mixtepec (Dto. 08)` y `(Dto. 26)`, `San Pedro Mixtepec (Dto. 22)` y `(Dto. 26)`.
- Lo que ya existía no se toca: las 38 ciudades de Coahuila y las colonias de Saltillo siguen igual, sin duplicados. Ver [reglas de negocio](docs/reglas-negocio.md).
- **Pendiente (no se pidió):** solo Saltillo tiene colonias, así que en las demás ciudades el menú de colonia queda vacío y no se puede completar un domicilio ahí todavía.
- 11 pruebas de backend y 3 de navegador nuevas (ahora 183 y 59).

**Al actualizar**
- Migración nueva: `locations 0011` (solo agrega ciudades que faltan; repetirla no cambia nada). **No hace falta borrar la base.** No hay dependencias nuevas.
- Los datos están en `backend/locations/migrations/_datos_ciudades.py`.

## Entrega 13 — Límites de la bitácora y panel de administración

**Cambios**
- **Bitácora**: el gerente ya no ve la actividad privada de los administradores: sus inicios y cierres de sesión, intentos fallidos con su matrícula, bloqueos, cambios de contraseña y exportaciones, ni los cambios a sus cuentas, ni los del catálogo de códigos telefónicos. **Sí** sigue viendo los cambios que un administrador haga a unidades, reportes, refacciones, etc., porque modifican datos de los que el gerente responde. Los administradores no salen en el filtro *Usuario* y el bloqueo de su cuenta no avisa a los gerentes. Todo se sigue guardando completo y se ve en el panel de administración. Ver [reglas de negocio](docs/reglas-negocio.md).
- **Panel de administración**: al agregar o editar un usuario, el código telefónico (y el de sus contactos) ya no muestra los botones de cambiar, añadir, eliminar y ver; es un menú simple.
- 15 pruebas de backend nuevas (ahora 172 y 56 de navegador).
- Se corrigió una prueba de navegador **intermitente** (ordenar columnas en Refacciones): leía la primera fila antes de que cargara la lista. Era un defecto de la prueba, no del sistema.

**Al actualizar**
- Sin migraciones ni dependencias nuevas; no hace falta borrar la base. Las líneas que ya existían quedan intactas: solo cambia lo que se muestra al gerente.

## Entrega 12 — Correcciones del formulario de teléfono

**Correcciones**
- En el formulario del trabajador, el **número telefónico se veía muy chico**: compartía una fila estrecha con el selector del código del país. Ahora el código y el número son campos separados, cada uno con el ancho de una celda normal (en escritorio y en celular, también en *Otros contactos*).
- El código del país **aparecía bajo la etiqueta «Número telefónico»**. Ahora cada campo tiene su propia etiqueta: **Código del país** y **Número telefónico**.
- 1 prueba de navegador nueva (ahora 157 de backend y 56 de navegador).

**Al actualizar**
- Solo cambia la interfaz: sin migraciones ni dependencias nuevas; no hace falta borrar la base.

## Entrega 11 — Fotografía opcional de las refacciones

**Novedades**
- Cada refacción puede tener una **fotografía** (opcional). La pone, cambia o quita el gerente en el formulario de la refacción, con vista previa. Se ve como miniatura en la lista de Refacciones y en grande en el formulario.
- **Sin fotografía** se muestra un **ícono neutro** (engrane) en una caja gris.
- A diferencia de la de los trabajadores, **no se recorta en cuadro**: se reduce a 800 px de lado largo (sin agrandar) y conserva sus proporciones, para no cortar la pieza. Se guarda como JPG, sin metadatos. Solo la ve el gerente. Ver [reglas de negocio](docs/reglas-negocio.md) y [seguridad](docs/seguridad.md).
- Nuevas rutas `refacciones/<id>/foto/` (GET, POST, DELETE) y `photo_url` en `refacciones/` ([api.md](docs/api.md)).
- El campo de la foto se oculta en el panel de administración (subirla ahí se saltaría la revisión del contenido).
- Interno: el procesamiento de fotos se generalizó (`accounts/photos.py`) y la descarga de fotos protegidas es un hook compartido (`useProtectedImage`) que usan `Avatar` y `PartPhoto`.
- 18 pruebas de backend y 5 de navegador nuevas (ahora 157 y 55).

**Al actualizar**
- Migración nueva: `fleet 0042` (columna `foto` en `refacciones`). No hace falta borrar la base.
- Las fotos se guardan en el volumen `media_data`, carpeta `refacciones/`. No hay dependencias nuevas.

## Entrega 10 — Códigos de país en los teléfonos y contactos adicionales del trabajador

**Novedades**
- **Código de país** en el teléfono: nueva tabla `codigos_telefonicos` (~245 países con nombre en español; `+52`, `+1`, `+51`…). El teléfono principal ahora es *código + número (solo dígitos)*. Un administrador activa o desactiva países en el panel (22 activos de inicio, México por defecto). El código **no es único** (varios países comparten `+1`), por eso es una tabla aparte y no una columna de `paises`.
- **Contactos adicionales** de un trabajador (nueva tabla `contactos_trabajador`): hasta **3** teléfonos o correos más de la **misma persona**, con etiqueta (*Número 2*…) y, opcional, de quién es. Sin repetidos, validados en la API, en el panel y en la base.
- Formulario del trabajador: selector de código junto al número y sección **Otros contactos** con *Agregar teléfono / correo* y *Quitar*; la lista muestra el teléfono completo y los contactos debajo. El PDF de trabajadores trae el teléfono con código.
- Las altas, cambios y bajas de contactos quedan en la bitácora. Solo el gerente los ve. Ver [reglas de negocio](docs/reglas-negocio.md), [API](docs/api.md) y [seguridad](docs/seguridad.md).
- `trabajadores/` trae `phone_code`, `phone_display` y `contacts`; `trabajadores/catalogos/` trae `phone_codes` y `max_contacts`.
- 38 pruebas de backend y 6 de navegador nuevas (ahora 139 y 50).

**Cambio que rompe compatibilidad**
- Guardar un trabajador ahora exige `phone_code_id`, y `phone_number` debe ser solo dígitos (4 a 14) sin código. Cualquier cliente de la API que enviaba `+52 844 123 4567` en `phone_number` debe separarlo.

**Al actualizar**
- Migraciones nuevas: `accounts 0009` (tablas), `0010` (carga los códigos y **convierte los teléfonos existentes**) y `0011` (restricciones). **No hace falta borrar la base**: los números existentes se convierten solos (con `+` se reconoce el código; sin él se asume México +52 y se quita un `52`/`521` inicial). Revisa en *Trabajadores* los teléfonos de personas de otro país.
- Los datos de los códigos viven en `backend/accounts/phone_codes_data.py` (sin dependencias nuevas).

## Entrega 9 — Fotografía opcional de los trabajadores

**Novedades**
- Cada trabajador puede tener una **fotografía** (opcional). La pone, cambia o quita el gerente en el formulario del trabajador, con vista previa. Se ve en el encabezado, en la lista de Trabajadores y en el formulario.
- **Sin fotografía** se muestran las **iniciales** en un círculo de color (JPG/PNG/WebP hasta 5 MB). Se eligieron las iniciales en vez de una silueta porque identifican a cada persona, tienen contraste AA en modo claro y oscuro y no hacen repetir el nombre a un lector de pantalla.
- La imagen se **recorta en cuadro (512 × 512) y se vuelve a guardar como JPG**: elimina metadatos (GPS, cámara) y archivos disfrazados. Solo la ve su dueño o el gerente. Ver [reglas de negocio](docs/reglas-negocio.md) y [seguridad](docs/seguridad.md).
- Nuevas rutas `trabajadores/<id>/foto/` (GET, POST, DELETE) y `photo_url` en `trabajadores/` y `auth/me/` ([api.md](docs/api.md)).
- 19 pruebas de backend y 6 de navegador nuevas (ahora 101 y 44).

**Al actualizar**
- Migración nueva: `accounts 0008` (columna `foto` en `usuarios`). No hace falta borrar la base.
- Las fotos se guardan en el volumen `media_data`. No hay dependencias nuevas (Pillow ya estaba).

## Entrega 8 — Pruebas de navegador y corrección en celular

**Novedades**
- **38 pruebas de navegador** (Playwright, `frontend/e2e/`): acceso, bloqueo, cambio obligatorio de contraseña, reporte de falla de punta a punta, listas (paginación, orden, búsqueda, PDF), dashboard, celular y modo oscuro. Ver [pruebas.md](docs/pruebas.md).
- Comando `python manage.py seed_e2e`: crea y restablece los usuarios y unidades de prueba (solo con `DJANGO_DEBUG=1`).
- El CI ahora también corre las pruebas de navegador sobre el sistema levantado con Docker Compose.

**Errores corregidos (los encontraron las pruebas nuevas)**
- **Listas en celular**: en Reportes, Unidades, Trabajadores, Mantenimientos, Diagnósticos, Checklists y Kardex (y en las tablas de las fichas) la tabla era más ancha que la pantalla y se recortaba sin poder desplazarla: las columnas de la derecha, como *Ver/Editar*, no se alcanzaban. Ahora todas las tablas se desplazan dentro de su caja.
- **Formularios de acceso y cambio de contraseña**: si se enviaban antes de que la página terminara de cargar, la matrícula y la contraseña viajaban en la dirección (URL). Ahora el envío nativo es por `POST`.

**Al actualizar**
- No hay migraciones ni dependencias nuevas en el backend; no hace falta borrar la base.
- Frontend: nueva dependencia de desarrollo `@playwright/test` (`npm install`).

## Entrega 7 — Pruebas automáticas, CI y PostgreSQL verificado

**Novedades**
- **82 pruebas automáticas** del backend (`backend/tests/`): seguridad de cuentas, listas y PDF, flujo de reportes, inventario, preventivo, notificaciones, dashboard, bitácora y permisos por rol. Ver [pruebas.md](docs/pruebas.md).
- **CI con GitHub Actions** (`.github/workflows/ci.yml`): pruebas con PostgreSQL 16, migraciones al día, documentación generada al día, tipos y compilación del frontend, y arranque completo con Docker Compose.
- **PostgreSQL probado de verdad**: la migración desde cero, las 82 pruebas, el servidor y las pantallas principales se ejecutaron sobre PostgreSQL 16 (ya no solo SQLite).
- Script `npm run typecheck` en el frontend; `.env.example` igual al `.env` del proyecto (incluye `PGDATA`).

**Al actualizar**
- No hay migraciones nuevas ni dependencias nuevas; no hace falta borrar la base.
- Para correr las pruebas: `docker compose exec backend python manage.py test tests`.

**Nota**: lo único que no se pudo ejecutar aquí es `docker compose` (no hay Docker en este entorno); el CI lo comprueba en GitHub.

## Entrega 6 — Dashboard, PDF, listas, seguridad y notificaciones

**Novedades**
- **Dashboard** del gerente con indicadores y gráficas (3/6/12 meses) y exportación a PDF.
- **Exportes a PDF** de todas las listas (con los filtros activos), de las fichas de reporte, diagnóstico, mantenimiento, checklist, refacción y kardex, del preventivo y de la bitácora.
- **Paginación, orden por columna y filtros** (búsqueda, fechas, estatus, rol…) en todas las listas.
- **Seguridad de cuentas**: bloqueo tras 5 intentos fallidos (15 min), cambio obligatorio de contraseña al crear o restablecer, cambio voluntario de contraseña, sesión de 8 h por inactividad.
- **Notificaciones** dentro del sistema (campana): reportes, asignaciones, cambios de estatus, stock bajo, preventivo y cuentas bloqueadas.
- **Documentación** en español en `docs/` (se actualiza en cada entrega).

**Al actualizar**
- Borra tu base anterior (`docker compose down -v`) y levanta de nuevo.
- Migraciones nuevas: `accounts 0007`, `audit 0002` y `0003`, `notifications 0001`, `fleet 0041`.
- Dependencia nueva del backend: `reportlab` (se instala con `--build`).
- Crea tu `.env` desde `.env.example`.

**Nota**: la verificación de esta entrega se hizo con SQLite; PostgreSQL se probó en la entrega 7.

## Entregas 1 a 5

Bitácora de auditoría, estatus de reportes calculados, inventario y kardex de refacciones, mantenimiento preventivo, y desactivación de unidades y refacciones. Ver [reglas de negocio](docs/reglas-negocio.md).
