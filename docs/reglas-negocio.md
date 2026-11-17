# Reglas de negocio

## Estatus de un reporte de falla

El estatus **no se captura**: lo calcula el sistema y deja historial (`historial_estatus_reportes`: quién y cuándo).

| Estatus | Cuándo |
|---|---|
| Pendiente | El operador lo creó y nadie lo tiene asignado |
| Asignado | El gerente asignó un mecánico |
| Diagnosticado | El mecánico registró el diagnóstico (con reparación requerida) |
| Sin reparación necesaria | El diagnóstico indica que no requiere reparación (cerrado) |
| En reparación | Hay mantenimientos del diagnóstico, aún sin completar la reparación |
| Reparado | Un mantenimiento marcó la reparación como completada (cerrado) |

Un reporte cerrado deja de aparecer como abierto en el dashboard, en el kardex y en la carga de los mecánicos. Un operador solo modifica sus reportes mientras están pendientes.

## Inventario de refacciones

- Las **existencias no se guardan**: son entradas y ajustes − piezas usadas en mantenimientos (`movimientos_inventario`, `mantenimiento_refacciones`). Editar o borrar un mantenimiento devuelve sus piezas.
- Un mantenimiento no puede usar más piezas de las que hay (se revalida al guardar, con bloqueo de filas).
- **Stock bajo**: solo si el mínimo es mayor que 0 y las existencias son ≤ al mínimo. Con mínimo 0 no se avisa.
- Una refacción ya usada no se puede borrar: se **desactiva**.

## Kardex de una unidad

- Es de solo lectura y solo lo ve el gerente. No se guarda: se calcula cada vez a partir de las demás tablas.
- Trae el historial de **placas, operadores, mecánicos asignados, reportes, diagnósticos, mantenimientos y checklists**, del más reciente al más antiguo.
- Trae también los **cambios de datos de la unidad** («Cambio de datos»): cada vez que se corrige o cambia su número económico, modelo, kilometraje o si está activa, queda una línea con *campo: antes → después*, quién lo hizo y la hora. Salen de la bitácora; un guardado sin cambios no genera nada. Los cambios de placa y de operador no se repiten ahí porque ya tienen sus propias líneas.
- Cada **mantenimiento** muestra el trabajo físico hecho a la unidad: tipo de servicio, km, costo, **quién lo realizó**, las **refacciones cambiadas** (refacción × cantidad, o «Sin refacciones»), las observaciones y, si es correctivo, la **falla reportada**, la **causa del diagnóstico** y si la **reparación quedó terminada**. Los reportes traen su descripción y los diagnósticos su causa.
- Una tabla **Refacciones cambiadas** suma por refacción las piezas usadas, las veces y la fecha del último cambio.
- Aparece también en el PDF del kardex (con la misma tabla de refacciones).

## Unidad apta para operar

- Un **checklist** se hace cada vez que la unidad va a salir a operar, así que **una unidad no apta no aparece** en el formulario de checklist ni se acepta en el servidor (error en el campo Unidad).
- Una unidad **no está apta** mientras tenga un **diagnóstico con «¿La unidad puede seguir operando?» = No** cuyo reporte siga abierto. Nadie la marca a mano: sale de los diagnósticos.
- Vuelve a estar apta cuando el reporte se cierra: **Reparado** (un mantenimiento marca la reparación terminada) o **Sin reparación necesaria**. También cuando se corrige o elimina ese diagnóstico. Mientras está *En reparación* sigue sin ser apta.
- Un checklist que ya existe puede editarse aunque su unidad haya dejado de ser apta (no se reescribe el pasado), pero no se puede cambiar a otra unidad que no lo sea.
- Esta regla solo afecta al checklist; los reportes de falla, diagnósticos y mantenimientos de la unidad siguen funcionando.

## Mantenimiento preventivo

- Un **plan** define cada cuántos km y/o días se repite el servicio, y a qué modelo aplica (o a todos).
- Cada unidad activa se compara contra cada plan activo que le aplique. El kilometraje actual es el mayor entre el de la unidad, el último checklist y el último mantenimiento.
- Estados: **vencido**, **próximo** (queda menos del 10 % del intervalo), **sin historial**, **al corriente**. Si hay km y días, manda el peor.
- Un mantenimiento preventivo puede ligarse a un plan; uno correctivo, no.

## Desactivar en lugar de borrar

| Elemento | Se desactiva | Efecto |
|---|---|---|
| Trabajador | sí | No puede entrar; conserva su historial |
| Unidad | sí | Desaparece de selectores, alertas y preventivo; no admite operadores nuevos; el kardex sigue mostrándola. **No** se puede desactivar con reportes abiertos |
| Refacción | sí | No se puede usar en mantenimientos nuevos (los existentes la conservan); no da alertas |
| Plan preventivo | sí | Deja de calcular vencimientos |

El borrado solo se permite si el registro no tiene historial asociado; si no, el sistema sugiere desactivar.

## Bitácora de auditoría

Registra quién, cuándo, desde qué IP y qué cambió (valor anterior y nuevo) en altas, cambios y bajas de los datos principales, además de inicios y cierres de sesión, intentos fallidos, bloqueos de cuenta, cambios de contraseña y exportaciones a PDF. Las contraseñas nunca se guardan. Las líneas no se pueden editar ni borrar.

**Qué ve el gerente.** La bitácora guarda todo, pero el gerente ve la actividad de la operación, no la privada de los administradores (que están por encima del gerente y ni siquiera aparecen en la pantalla de Trabajadores):

| Se ve | No se ve |
|---|---|
| Altas, cambios y bajas de unidades, reportes, refacciones, trabajadores, etc., **también las que hace un administrador** (cambian datos de los que el gerente responde; no deben aparecer de la nada) | Inicios y cierres de sesión de administradores |
| Accesos, bloqueos y cambios de contraseña de gerentes, mecánicos y operadores | Intentos fallidos con la matrícula de un administrador, bloqueos, cambios de contraseña y exportaciones de administradores |
| Intentos fallidos con una matrícula que no existe | Cambios a las cuentas de administración |
| | Cambios al catálogo de códigos telefónicos (lo mantiene el administrador) |

Los administradores tampoco salen en el filtro *Usuario*, y el bloqueo de una cuenta de administración no genera aviso a los gerentes. La persona con acceso al panel de administración sí ve todas las líneas. Una línea sobre los contactos adicionales de un administrador (casi nunca existen) no se puede ligar a su dueño y se sigue mostrando.

## Fotografía de los trabajadores

- Es **opcional**. Solo el gerente la pone, la cambia o la quita (en el formulario del trabajador).
- **Sin fotografía** se muestra un círculo de color con las **iniciales**: la primera letra del primer nombre y la del apellido paterno (`Juan Pérez` → `JP`). El color sale de la matrícula, así que cada persona conserva siempre el mismo. Se eligió esto en lugar de una silueta porque identifica a cada persona de un vistazo, tiene buen contraste (WCAG AA) y un lector de pantalla no repite el nombre.
- Formatos JPG, PNG o WebP, hasta 5 MB. El sistema la **recorta en cuadro (512 × 512), la endereza según la cámara y la guarda de nuevo como JPG**: así se eliminan los metadatos (cámara, ubicación GPS) y todas pesan poco.
- La foto aparece en el encabezado (la propia), en la lista de Trabajadores y en su formulario. Cada persona solo puede ver **su propia** foto; el gerente ve todas.
- Al reemplazarla, quitarla o eliminar al trabajador, el archivo anterior se borra del disco.

## Ubicaciones y domicilios

- El **país es siempre México**. El **estado** y el **municipio** salen del servicio web del **INEGI** (Catálogo Único de Claves Geoestadísticas): no hay tablas de países, estados ni ciudades en la base. Cada formulario consulta la lista cuando la necesita (el servidor guarda la respuesta una hora para no preguntar a cada rato).
- El domicilio guarda **estado** y **municipio** como texto, igual que **colonia** y **calle** (hasta 150 caracteres, se escriben a mano), más el número exterior (obligatorio) y el interior (opcional).
- Al guardar, el servidor **comprueba con el INEGI** que el estado exista y que el municipio sea de ese estado (error «Elige una opción válida.»).
- **Si el INEGI no responde**, los menús muestran el aviso y no se puede guardar un domicilio ni una placa nuevos. Un domicilio ya guardado **sigue pudiéndose editar** (colonia, calle, números…) mientras no cambie su estado ni su municipio: esos nombres ya guardados se aceptan sin preguntar.
- La **placa** también guarda el **estado** que la emitió como texto (nombre del INEGI), validado igual.
- La migración `locations 0015–0018` y `fleet 0043–0045` pasó el estado y el municipio de cada domicilio y el estado de cada placa a texto y eliminó las tablas `paises`, `estados` y `ciudades`, sin perder ningún dato. No se puede deshacer una vez aplicada. Los nombres viejos se conservan tal cual (por ejemplo «Estado de México», que en el INEGI es «México»); al editar ese estado se puede cambiar por el del INEGI.
- Configuración: `INEGI_API_URL` (por defecto `https://gaia.inegi.org.mx/wscatgeo/v2`) y `INEGI_TIMEOUT` (segundos, 8). Para desarrollar sin internet: `python manage.py inegi_falso` levanta un INEGI de mentira en `http://localhost:8777`.

## Fotografía de las refacciones

- Es **opcional**, una por refacción. Solo el gerente la ve, la pone, la cambia o la quita (en el formulario de la refacción, con vista previa).
- **Sin fotografía** se muestra un ícono neutro (un engrane) en una caja gris, junto al nombre. Es decorativo: el nombre ya está escrito al lado.
- Formatos JPG, PNG o WebP, hasta 5 MB. A diferencia de la foto de un trabajador, **no se recorta**: se reduce para que su lado más largo mida como máximo 800 px (sin agrandarla) y conserva sus proporciones, para no cortar la pieza. Se guarda de nuevo como JPG, sin metadatos.
- Aparece como miniatura en la lista de Refacciones y en grande en el formulario. No sale en el PDF.
- Al reemplazarla, quitarla o eliminar la refacción, el archivo anterior se borra del disco. Desactivar una refacción conserva su foto.

## Teléfonos y otros contactos de un trabajador

- El **teléfono principal** se guarda en dos partes: el **código del país** (`+52`, `+1`, `+51`…) y el **número nacional, solo dígitos** (de 4 a 14). Código + número no pueden pasar de **15 dígitos** (norma E.164). Al capturar se aceptan espacios, guiones y paréntesis (`844 123-4567`), pero se guarda solo con dígitos.
- Los códigos salen de una **tabla propia** (`codigos_telefonicos`, ~245 países, nombres en español) (el domicilio ya no tiene catálogo de países) (este solo sirve para teléfonos). **El código no es único**: varios países comparten el mismo (`+1` Estados Unidos, Canadá, República Dominicana…), por eso cada país es una fila.
- Al capturar solo se ofrecen los códigos **activos** (por defecto 22: México, Estados Unidos, Canadá, Perú, Colombia, Guatemala, España, Argentina, Chile, Brasil, Ecuador, Bolivia, Costa Rica, Panamá, Honduras, El Salvador, Nicaragua, Venezuela, Uruguay, Paraguay, Cuba y República Dominicana). Un administrador activa o desactiva países en el panel de administración (*Códigos telefónicos*). Un trabajador que ya usa un código que se desactivó **lo conserva**; no se puede elegir para otro.
- Un nuevo trabajador empieza con México (+52) seleccionado.
- **Otros contactos**: además del teléfono y el correo principales, cada trabajador puede tener **hasta 3 contactos adicionales** (`MAX_CONTACTS` en `accounts/models.py`): otro teléfono ("Número 2") u otro correo. Son otras formas de localizar a **la misma persona**, no otra persona.
  - Cada contacto tiene una **etiqueta** (si se deja vacía se pone `Número 2`, `Número 3`… o `Correo 2`…; el principal es el 1) y, opcional, el **nombre de la persona** a quien pertenece (por ejemplo "su esposa").
  - No se permiten **repetidos**: ni entre sí ni iguales al teléfono o correo principal (el mismo número con otro código de país sí es otro teléfono).
  - El límite se valida en la API, en el panel de administración y no se puede rebasar con dos ediciones a la vez (la fila del trabajador se bloquea al guardar).
  - Solo el gerente los ve y los edita. Las altas, cambios y bajas quedan en la bitácora (*Contacto del trabajador*). Al eliminar al trabajador se eliminan sus contactos.

## Notificaciones

| Evento | Quién la recibe |
|---|---|
| Reporte de falla nuevo | Gerentes |
| Mecánico asignado a un reporte | Ese mecánico |
| Cambio de estatus de un reporte | El operador que lo reportó; los gerentes cuando se cierra |
| Stock bajo tras un mantenimiento o movimiento | Gerentes (no se repite mientras no la hayan leído) |
| Preventivo vencido o próximo | Gerentes (una vez por plan, unidad, último servicio y estado) |
| Cuenta bloqueada por intentos fallidos | Gerentes |

La persona que provoca el evento no recibe su propia notificación. La campana del menú muestra las no leídas y se actualiza cada minuto.

## Dashboard

Calcula al momento (3, 6 o 12 meses): reportes abiertos y sin mecánico, preventivo vencido/próximo, stock bajo, unidades activas e inactivas, reportes y mantenimientos por mes, costo total y promedio, días promedio para cerrar un reporte, unidades con más costo y más reportes, refacciones más usadas y carga de cada mecánico. Se puede exportar a PDF.
