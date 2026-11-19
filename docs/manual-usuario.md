# Manual de usuario

Entra con tu **matrícula** y contraseña. Si es tu primer acceso o el gerente restableció tu contraseña, el sistema te pedirá elegir una nueva antes de continuar. Con 5 intentos fallidos la cuenta se bloquea 15 minutos.

## Todos los roles

- **Campana** (arriba): avisos nuevos; entra a *Notificaciones* para leerlos o limpiar los leídos.
- **Contraseña**: cambia tu contraseña cuando quieras.
- Junto a tu nombre ves tu **fotografía** o, si no tienes, tus **iniciales**. La pone el gerente.
- **Listas**: escribe en el buscador, filtra, haz clic en el encabezado de una columna para ordenar (otro clic invierte el orden) y usa la paginación al pie. **Exportar a PDF** abre en una pestaña nueva justo lo que estás viendo, sin paginar; desde el visor del navegador puedes imprimirlo o guardarlo.
- El botón **Ver ficha en PDF** dentro de un registro abre su ficha en una pestaña nueva. Si el navegador bloquea las ventanas emergentes, el archivo se descarga en su lugar.

## Operador

Solo ves **la unidad que tienes asignada ahora**. Si el gerente te cambia de unidad, la anterior deja de aparecer en tus formularios (tus reportes y checklists anteriores se conservan).

1. **Checklist**: antes de salir, registra el kilometraje y marca el estado de tu unidad. Las unidades **no aptas para operar** no aparecen en la lista: el formulario te avisa cuáles son y por qué (tienen una falla diagnosticada que aún no se repara).
2. **Reportar una falla**: unidad, lugar y descripción. Puedes corregirlo mientras esté *Pendiente*.
3. Sigue el estatus en **Reportes**; recibirás un aviso cuando cambie.

## Mecánico

1. **Reportes asignados**: lo que el gerente te encargó (aviso al asignarte).
2. **Diagnóstico**: al elegir el reporte ves **la descripción que escribió el operador**. Registra gravedad, la descripción del diagnóstico (causa detallada) y si requiere reparación.
3. **Mantenimiento**: en un correctivo, al elegir el diagnóstico ves **su descripción (causa detallada)**. Registra servicio realizado, kilometraje, costo y refacciones usadas (se descuentan solas del inventario). Marca *reparación completada* para cerrar el reporte.

## Gerente

- **Dashboard**: indicadores de 3, 6 o 12 meses, con exportación a PDF.
- **Reportes**: asigna mecánico, revisa el historial de estatus.
- **Unidades y asignaciones**: alta, baja (desactivar) y operador de cada unidad. Cada unidad tiene **un solo operador** y cada operador **una sola unidad**. En el formulario de la unidad, sección **Operador**:
  - Sin operador: elige uno y la fecha **Desde**. Solo aparecen los operadores activos que no tienen unidad.
  - **Cambiar de operador**: elige al nuevo y la fecha **A partir de**. El actual deja la unidad ese día y el nuevo la tiene desde ese día.
  - **Quitar operador**: indica el día en que deja la unidad.
  - Los cambios se aplican al **Guardar**. Debajo está el **Historial de operadores** (operador, desde, hasta). Si otra persona asignó ese operador a otra unidad mientras tanto, la ventana de errores te dice cuál.
  - Para desactivar una unidad, primero quítale el operador.
- **Kardex**: el historial de cada unidad. Arriba ves sus datos, el resumen y el preventivo. Debajo, una **pestaña por tema**: *Mantenimientos*, *Fallas*, *Checklists*, *Refacciones cambiadas*, *Operadores y mecánicos*, *Placas y cambios de datos* y *Línea de tiempo* (todo junto, por fecha).
  - Cada pestaña tiene su tabla y sus filtros: escribe en el buscador, elige fechas (*Desde/Hasta*) y los filtros de esa pestaña (por ejemplo, tipo de servicio o reparación terminada en Mantenimientos, o estatus en Fallas), y pulsa **Buscar**. **Limpiar** quita los filtros.
  - Haz clic en un encabezado para ordenar. Un texto largo se recorta: pulsa **ver más** para leerlo completo.
  - **Exportar … a PDF** (dentro de cada pestaña) saca esa tabla con tus filtros. **Exportar kardex completo** (arriba) saca todas las secciones.
  - En *Placas y cambios de datos* ves cada corrección al número económico, modelo, kilometraje o si la unidad está activa: qué decía antes, qué dice ahora, quién lo cambió y a qué hora.
- **Refacciones**: existencias, entradas y ajustes; aviso de stock bajo. En el formulario de la refacción, **Fotografía (opcional)**: elige una imagen (JPG, PNG o WebP, hasta 5 MB), mira cómo queda y guarda; **Quitar fotografía** la elimina. Sin fotografía se ve un ícono. La imagen no se recorta.
- **Preventivo**: planes (cada cuántos km o días) y tabla de vencimientos.
- **Trabajadores**: altas, roles, desactivar, restablecer contraseña (la persona deberá cambiarla) y desbloquear cuentas. En el formulario, **Fotografía (opcional)**: elige una imagen (JPG, PNG o WebP, hasta 5 MB), mira cómo queda y guarda; **Quitar fotografía** la elimina. Sin fotografía se ven las iniciales de la persona. El **teléfono** lleva su **código de país** (empieza en México +52) y se escribe solo con números. En **Domicilio** el país es siempre México; eliges el **estado** y el **municipio** (las listas se consultan al INEGI; si el INEGI no responde se avisa y no se puede guardar un domicilio nuevo) y **escribes** la colonia y la calle, más el número exterior (y el interior si lo hay). En **Otros contactos** (hasta 3) agrega otro teléfono (*Número 2*) u otro correo de la misma persona, con una etiqueta y, si quieres, de quién es; se ven debajo del teléfono en la lista.
- **Bitácora**: quién hizo qué y cuándo; también se puede exportar. No incluye los accesos ni la actividad de las cuentas de administración.

## Dudas frecuentes

- *No puedo entrar*: revisa matrícula y contraseña; si aparece "cuenta bloqueada", espera 15 minutos o pide al gerente que la desbloquee.
- *Olvidé mi contraseña*: pide al gerente que la restablezca.
- *No encuentro una unidad o refacción*: puede estar desactivada; el gerente puede reactivarla.
