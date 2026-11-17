# ROMEX Logística

Sistema interno de logística de flota: control de **unidades**, **reportes de fallas**, **diagnósticos**, **mantenimientos** (correctivo y preventivo), **inventario de refacciones**, **checklists** de operadores, **bitácora de auditoría**, **notificaciones** y **dashboard de indicadores**.

Es un sistema **interno**: no hay registro público. Las cuentas las crean únicamente el administrador o el gerente, y se entra con **matrícula y contraseña**.

| Capa | Tecnología |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | Django 5.2 (API JSON con sesión y CSRF) |
| Base de datos | PostgreSQL 16 |
| Catálogo de estados y municipios | Servicio web del INEGI (consulta en vivo) |
| PDF | ReportLab |
| Pruebas | Pruebas de Django + Playwright, en GitHub Actions |
| Despliegue | Docker Compose |

> **¿Eres nuevo en el proyecto?** Empieza por la [guía de onboarding](docs/onboarding.md): levantar el sistema, usuarios de prueba, recorrido por el código y cómo entregar un cambio.

## Inicio rápido

```bash
git clone https://github.com/JssBeAg/Romex.git
cd Romex
cp .env.example .env        # cambia POSTGRES_PASSWORD y DJANGO_SECRET_KEY
docker compose up --build   # base (:5432), backend (:8000) y frontend (:3000)
docker compose exec backend python manage.py createsuperuser
```

Entra a <http://localhost:3000> con la matrícula del superusuario. El panel de Django está en <http://localhost:8000/admin/>.

- **Usuarios de prueba**, uno por rol: `docker compose exec backend python manage.py seed_e2e` (solo con `DJANGO_DEBUG=1`).
- **Sin internet**: los estados y municipios vienen del INEGI. Para trabajar sin conexión usa `python manage.py inegi_falso` y `INEGI_API_URL=http://localhost:8777/wscatgeo/v2`.
- **Pruebas**: `docker compose exec backend python manage.py test tests`.

Detalles y variables de entorno: [docs/instalacion.md](docs/instalacion.md).

## Documentación

Toda la documentación está en español en la carpeta [`docs/`](docs/README.md) y **se actualiza en cada entrega** (ver el [CHANGELOG](CHANGELOG.md)).

- [Onboarding para desarrolladores](docs/onboarding.md)
- [Instalación](docs/instalacion.md)
- [Arquitectura](docs/arquitectura.md)
- [Roles y permisos](docs/roles-permisos.md)
- [Reglas de negocio](docs/reglas-negocio.md)
- [Seguridad de cuentas](docs/seguridad.md)
- [API](docs/api.md) y [referencia de rutas](docs/referencia-rutas.md)
- [Modelo de datos](docs/modelo-datos.md)
- [Manual de usuario](docs/manual-usuario.md)
- [Convenciones de desarrollo](docs/convenciones.md)
- [Pruebas y CI](docs/pruebas.md)
