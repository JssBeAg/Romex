# Documentación de ROMEX

| Documento | Contenido | Cómo se mantiene |
|---|---|---|
| [instalacion.md](instalacion.md) | Cómo levantar el sistema con Docker y sin Docker | A mano |
| [arquitectura.md](arquitectura.md) | Estructura del código, capas y flujo de una petición | A mano |
| [roles-permisos.md](roles-permisos.md) | Qué puede hacer cada rol | A mano |
| [reglas-negocio.md](reglas-negocio.md) | Estatus de reportes, inventario, preventivo, desactivación, notificaciones | A mano |
| [seguridad.md](seguridad.md) | Contraseñas, bloqueo, sesión, bitácora | A mano |
| [api.md](api.md) | Convenciones de la API: listas, paginación, filtros, PDF | A mano |
| [referencia-rutas.md](referencia-rutas.md) | Todas las rutas de la API | **Generado** |
| [modelo-datos.md](modelo-datos.md) | Tablas, columnas, restricciones y diagrama ER | **Generado** |
| [manual-usuario.md](manual-usuario.md) | Guía de uso por rol | A mano |
| [convenciones.md](convenciones.md) | Reglas de código y de diseño del proyecto | A mano |
| [pruebas.md](pruebas.md) | Pruebas automáticas y CI | A mano |
| [../CHANGELOG.md](../CHANGELOG.md) | Qué cambió en cada entrega | A mano |

## Regla de actualización

En **cada entrega**:

1. Regenerar lo automático: `python manage.py generar_docs` (modelo de datos y rutas).
2. Correr las pruebas (`python manage.py test tests`) y agregar las del cambio.
3. Revisar los documentos escritos a mano que toque el cambio.
4. Agregar una entrada al [CHANGELOG](../CHANGELOG.md) con la fecha, lo nuevo y lo que obliga a hacer algo (migraciones, borrar la base, variables nuevas).
