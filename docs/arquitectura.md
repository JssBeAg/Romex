# Arquitectura

```
Navegador ── Next.js (:3000) ── fetch con cookie de sesión + CSRF ──▶ Django (:8000) ──▶ PostgreSQL
                                                                  └─▶ media/ (evidencias y fotos de perfil)
```

El frontend es una aplicación de páginas que solo habla con la API JSON. El backend no tiene sitio público: solo `/api/...` y el panel `/admin/` para el administrador.

## Backend (`backend/`)

| Carpeta | Responsabilidad |
|---|---|
| `config/` | Ajustes, rutas raíz |
| `accounts/` | Usuario (matrícula como login), roles, API de trabajadores, seguridad de cuentas (`security.py`), bloqueo y cambio obligatorio de contraseña (`middleware.py`) |
| `locations/` | Domicilios (estado y municipio como texto) y el cliente del servicio del INEGI que ofrece las listas de estados y municipios |
| `fleet/` | Unidades, placas, operadores, reportes, diagnósticos, mantenimientos, checklists, refacciones, preventivo, kardex, dashboard, fichas PDF (`sheets.py`) |
| `audit/` | Bitácora inmutable, escrita con señales de Django |
| `notifications/` | Notificaciones por usuario, creadas con señales |
| `common/` | Listados compartidos (`listing.py`: orden, fechas, paginación, PDF) y generación de PDF (`pdf.py`) |

Cada módulo de API (`*_api.py`) tiene su `*_urls.py`. Los permisos se deciden **en la API** con decoradores (`manager_required`, `roles_required`), no con las tablas de permisos de Django.

### Piezas transversales

- **Validación previa (`?validar=1`)**: los formularios piden al servidor que revise los datos sin guardar; responde `{"errors": {...}}`. Así los errores aparecen mientras se escribe.
- **Bitácora**: `audit/signals.py` escucha guardados y borrados de los modelos de `audit/registry.py`; un *middleware* aporta usuario e IP. No se puede modificar ni borrar.
- **Notificaciones**: `notifications/signals.py` crea avisos ante eventos (reporte nuevo, asignación, cambio de estatus, stock bajo, bloqueo). Los de preventivo se derivan al consultar.
- **Listados**: `common/listing.py` da a todas las listas el mismo comportamiento (ver [api.md](api.md)).
- **PDF**: `common/pdf.py` (aspecto común) y `fleet/sheets.py` (fichas de un registro).

## Frontend (`frontend/src/`)

| Carpeta | Contenido |
|---|---|
| `app/(app)/` | Páginas protegidas, todas dentro del `AppShell` (encabezado, menú por rol, campana, tema) |
| `app/login/` | Inicio de sesión |
| `components/` | Formularios, `Pagination`, `SortHeader`, `ExportButton`, `ErrorDialog`, gráficas (`MiniCharts`) |
| `lib/` | Un módulo por recurso (tipos y llamadas a la API), `http.ts` (cliente), `listing.ts` (hook `useList`, PDF), `useFormFeedback.tsx` |

Los colores salen de variables CSS (`globals.css`) con modo claro y oscuro (rojo `#bd152c`, tinta `#2d2926`).

## Datos derivados (no se guardan)

- **Existencias** de refacciones = entradas y ajustes − piezas usadas en mantenimientos.
- **Estatus del reporte**: lo calcula `fleet/report_status.py` según asignaciones, diagnóstico y mantenimientos.
- **Vencimientos preventivos** y **dashboard**: se calculan al consultar.
