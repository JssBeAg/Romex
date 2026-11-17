# ROMEX Logística

Sistema interno de logística de flota: control de **unidades**, **reportes de fallas**, **diagnósticos**, **mantenimientos** (correctivo y preventivo), **inventario de refacciones**, **checklists** de operadores, **bitácora de auditoría**, **notificaciones** y **dashboard de indicadores**.

Es un sistema **interno**: no hay registro público. Las cuentas las crean únicamente el administrador o el gerente, y se entra con **matrícula y contraseña**.

| Capa | Tecnología |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | Django 5.2 (API JSON con sesión y CSRF) |
| Base de datos | PostgreSQL |
| PDF | ReportLab |
| Despliegue | Docker Compose |

## Inicio rápido

```bash
cp .env.example .env        # ajusta usuarios y contraseñas de la base
docker compose up --build   # base, backend (:8000) y frontend (:3000)
docker compose exec backend python manage.py createsuperuser
```

Detalles y variables de entorno: [docs/instalacion.md](docs/instalacion.md).

## Documentación

Toda la documentación está en español en la carpeta [`docs/`](docs/README.md) y **se actualiza en cada entrega** (ver el [CHANGELOG](CHANGELOG.md)).

- [Arquitectura](docs/arquitectura.md)
- [Roles y permisos](docs/roles-permisos.md)
- [Reglas de negocio](docs/reglas-negocio.md)
- [Seguridad de cuentas](docs/seguridad.md)
- [API](docs/api.md) y [referencia de rutas](docs/referencia-rutas.md)
- [Modelo de datos](docs/modelo-datos.md)
- [Manual de usuario](docs/manual-usuario.md)
- [Convenciones de desarrollo](docs/convenciones.md)
- [Pruebas y CI](docs/pruebas.md)
