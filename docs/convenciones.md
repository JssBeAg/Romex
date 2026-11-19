# Convenciones de código

## Idioma

| Qué | Idioma |
|---|---|
| Código, comentarios, nombres de Python y de TypeScript | Inglés |
| Tablas, columnas y restricciones de la base de datos | Español (`db_table`, `db_column`) |
| Todo texto visible al usuario (pantallas, mensajes de error, PDF) | Español |
| Documentación y mensajes de commit de esta carpeta | Español |

## Backend

- Un módulo `*_api.py` por recurso en `fleet/`; las vistas son funciones con los decoradores de permisos de `accounts`.
- Las listas se construyen siempre con `common.listing.list_response(...)`: así heredan búsqueda, orden, fechas, paginación y PDF. No se paginan a mano. Si la lista se arma en memoria (junta varias tablas o suma, como las secciones del kardex), se usa `rows_response(...)`, que da el mismo orden, paginación y PDF.
- Los PDF se hacen con `common/pdf.py` (`list_pdf`, `sheet_pdf`), que además registra la exportación en la bitácora.
- Las altas y ediciones aceptan `?validar=1` (validar sin guardar). Los errores se devuelven como `{"errors": {campo: [mensajes]}}`.
- Lo calculable **no se guarda** (estatus de reportes, existencias, vencimientos preventivos).
- La bitácora se alimenta por señales (`audit/registry.py` lista los modelos); no se llama a mano salvo para sesión, cuentas y exportaciones.
- Las notificaciones salen de señales en `notifications/signals.py`.
- Contadores técnicos (intentos fallidos…) se escriben con `queryset.update()` para no ensuciar la bitácora.
- Toda tabla o columna nueva lleva su migración; los nombres van en español.

## Frontend

- Next.js (App Router) + TypeScript, sin librerías de UI ni de gráficas: componentes propios en `components/`.
- Las llamadas a la API viven en `src/lib/*.ts`; las páginas no hacen `fetch` directo.
- Las pantallas de lista usan `useList` + `Pagination` + `SortHeader` + `ExportButton`.
- Para mostrar la foto de una refacción (o su ícono) se usa `PartPhoto`; las fotos protegidas por la sesión se descargan con el hook `useProtectedImage`, que comparten `Avatar` y `PartPhoto`.
- Para mostrar a una persona (foto o iniciales) se usa siempre el componente `Avatar`: es decorativo por defecto porque el nombre va escrito al lado; solo lleva `label` cuando va solo.
- Los formularios usan `useFormFeedback` (errores en vivo) y `ErrorDialog`.
- Colores solo con variables CSS de `globals.css` (rojo `#bd152c`, tinta `#2d2926`), con modo oscuro. Nada de colores fijos en componentes.
- Debe verse bien en celular: toda tabla va dentro de `<div className="table-scroll">` (si no, las columnas de la derecha quedan recortadas).

## Pruebas

- Toda regla de negocio, permiso o validación nueva lleva su prueba en `backend/tests/` (ver [pruebas.md](pruebas.md)); un flujo de pantalla nuevo, en `frontend/e2e/`. El CI debe pasar antes de entregar.

## Documentación

Cada entrega actualiza `docs/` y el [CHANGELOG](../CHANGELOG.md). Los documentos generados se regeneran con:

```bash
docker compose exec backend python manage.py generar_docs
```
