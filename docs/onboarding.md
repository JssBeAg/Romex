# Onboarding para desarrolladores

Guía para quien llega al proyecto. Al terminarla tendrás el sistema corriendo en tu máquina, sabrás dónde vive cada cosa y cómo entregar un cambio. Para el detalle de cada tema, sigue los enlaces: esta guía no repite lo que ya está en los otros documentos.

## 1. Qué es ROMEX

Sistema **interno** de logística de flota. Un operador reporta una falla de su unidad, el gerente se la asigna a un mecánico, el mecánico la diagnostica y la repara con un mantenimiento, y las refacciones usadas se descuentan del inventario. Alrededor de ese flujo hay checklists, mantenimiento preventivo, kardex por unidad, bitácora de auditoría, notificaciones y un dashboard.

No hay registro público: el administrador y el gerente crean las cuentas, y se entra con **matrícula y contraseña**.

### Vocabulario

| Término | Significado |
|---|---|
| **Unidad** | Un vehículo de la flota, identificado por su número económico |
| **Matrícula** | El usuario con el que entra cada trabajador |
| **Reporte** | Falla que levanta un operador sobre una de sus unidades |
| **Diagnóstico** | Lo que concluye el mecánico: causa y si la unidad puede operar |
| **Mantenimiento** | Correctivo (repara un reporte) o preventivo (según un plan por modelo) |
| **Checklist** | Revisión que llena el operador antes de salir con la unidad |
| **Kardex** | Historial completo de una unidad: reportes, mantenimientos, refacciones y cambios de datos |
| **Bitácora** | Registro inmutable de quién hizo qué y cuándo |

Roles: **Administrador**, **Gerente**, **Mecánico** y **Operador** ([roles-permisos.md](roles-permisos.md)).

## 2. Primer día: levantar el sistema

Necesitas **Git** y **Docker Desktop** (con Docker Compose). Node y Python solo hacen falta para trabajar sin Docker o correr las pruebas de navegador.

```bash
git clone https://github.com/JssBeAg/Romex.git
cd Romex
cp .env.example .env          # cambia POSTGRES_PASSWORD y DJANGO_SECRET_KEY
docker compose up --build -d  # base :5432, API :8000, interfaz :3000
```

En Windows, clona con `git clone -c core.autocrlf=input ...` para que los archivos conserven los finales de línea LF que usan los contenedores.

Al arrancar, el backend aplica las migraciones (`migrate`) y crea los roles (`sync_roles`). Comprueba que respondan:

- <http://localhost:8000/api/health/>: API
- <http://localhost:3000>: interfaz

### Usuarios para probar

Crea tu administrador:

```bash
docker compose exec backend python manage.py createsuperuser
```

Para tener un usuario de cada rol sin darlos de alta a mano, carga los datos de prueba (solo con `DJANGO_DEBUG=1`):

```bash
docker compose exec backend python manage.py seed_e2e
```

Crea estas cuentas, todas con la contraseña `Clave12345x`, y las unidades `E2E-1` (de O1) y `E2E-2` (de O2):

| Matrícula | Rol | Nota |
|---|---|---|
| `G1` | Gerente | |
| `M1` | Mecánico | |
| `O1`, `O2` | Operador | |
| `L1` | Operador | Las pruebas la bloquean a propósito |
| `F1` | Operador | Debe cambiar la contraseña al entrar |

Las pruebas de navegador usan estas cuentas y `seed_e2e` las restablece en cada corrida, así que no guardes en ellas nada que quieras conservar.

### Sin internet

Los estados y municipios se consultan en vivo al INEGI. Para trabajar sin conexión, levanta el INEGI de mentira y apunta el backend a él:

```bash
docker compose exec -d backend python manage.py inegi_falso
# en .env:
INEGI_API_URL=http://localhost:8777/wscatgeo/v2
docker compose up -d backend
```

Más opciones (incluido levantarlo sin Docker): [instalacion.md](instalacion.md).

## 3. Recorrido por el código

```
Romex/
├── backend/            Django 5.2: API JSON + panel /admin/
│   ├── config/         ajustes y rutas raíz
│   ├── accounts/       usuarios, roles, trabajadores, seguridad de cuentas
│   ├── fleet/          unidades, reportes, diagnósticos, mantenimientos, inventario, kardex…
│   ├── locations/      domicilios y cliente del INEGI
│   ├── audit/          bitácora (señales)
│   ├── notifications/  avisos (señales)
│   ├── common/         listados y PDF compartidos
│   └── tests/          pruebas de la API
├── frontend/           Next.js + TypeScript
│   ├── src/app/        páginas (App Router); las protegidas en (app)/
│   ├── src/components/ componentes propios (sin librerías de UI)
│   ├── src/lib/        un módulo por recurso con las llamadas a la API
│   └── e2e/            pruebas de navegador (Playwright)
├── db/                 imagen de PostgreSQL e init.sql
└── docs/               documentación (en español)
```

Para seguir una funcionalidad de punta a punta, empieza por la página en `frontend/src/app/(app)/<pantalla>/`, sigue la llamada en `frontend/src/lib/<recurso>.ts` y llega al `backend/fleet/<recurso>_api.py` correspondiente. El flujo de una petición, las piezas transversales (validación previa, bitácora, notificaciones, listados, PDF) y los datos que se calculan en lugar de guardarse están en [arquitectura.md](arquitectura.md).

Orden de lectura recomendado:

1. [arquitectura.md](arquitectura.md): cómo encaja todo.
2. [reglas-negocio.md](reglas-negocio.md): estatus de reportes, inventario, preventivo.
3. [roles-permisos.md](roles-permisos.md): quién puede hacer qué.
4. [convenciones.md](convenciones.md): las reglas de código que se revisan en cada cambio.
5. [api.md](api.md), [modelo-datos.md](modelo-datos.md) y [referencia-rutas.md](referencia-rutas.md), como consulta.

Para conocer el producto como lo usa la gente, entra con `G1`, `M1` y `O1` y recorre el [manual de usuario](manual-usuario.md): levanta un reporte como operador, asígnalo como gerente y repáralo como mecánico.

## 4. Reglas que conviene saber desde el principio

- **Idiomas**: el código y los comentarios van en inglés; las tablas, las columnas, los textos visibles, la documentación y los commits van en español.
- **Permisos en la API**, con los decoradores `manager_required` y `roles_required`. El frontend solo decide qué mostrar.
- **Lo calculable no se guarda**: existencias, estatus de reportes y vencimientos preventivos se calculan al consultar.
- **Las listas** se arman siempre con `common.listing.list_response(...)`; **los PDF**, con `common/pdf.py`.
- **La bitácora y las notificaciones** salen de señales: no las escribas a mano.
- **Colores** solo con las variables CSS de `globals.css`, y toda tabla dentro de `.table-scroll`, para que se vea bien en celular.

La lista completa está en [convenciones.md](convenciones.md).

## 5. Cómo entregar un cambio

1. Crea una rama desde `main`.
2. Haz el cambio siguiendo las [convenciones](convenciones.md). Si tocas modelos, crea la migración (`python manage.py makemigrations`), con los nombres de tablas y columnas en español.
3. Agrega pruebas: las reglas, permisos y validaciones en `backend/tests/`, y los flujos de pantalla en `frontend/e2e/` ([pruebas.md](pruebas.md)).
4. Corre las pruebas:

   ```bash
   docker compose exec backend python manage.py test tests
   docker compose exec backend python manage.py seed_e2e
   cd frontend && npm run test:e2e
   ```

5. Regenera la documentación automática y revisa la escrita a mano que toque tu cambio:

   ```bash
   docker compose exec backend python manage.py generar_docs
   ```

6. Agrega una entrada arriba en el [CHANGELOG](../CHANGELOG.md): qué cambió y qué hay que hacer al actualizar (migraciones, borrar la base, variables nuevas).
7. Sube la rama y abre un *pull request*. El CI de GitHub Actions corre las pruebas del backend, la revisión de tipos, la compilación y las pruebas de navegador con Docker Compose, y verifica que no falten migraciones ni documentación generada. Debe pasar antes de integrar.

## 6. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| El backend se reinicia en bucle con `password authentication failed for user "romex"` | El volumen `postgres_data` se creó con otra contraseña. `POSTGRES_PASSWORD` solo se aplica la primera vez que se crea la base. Pon en `.env` la contraseña original, o cámbiala dentro de la base: `docker compose exec db psql -U romex -d romex -c "ALTER USER romex WITH PASSWORD '<la de .env>';"`. Si no te importan los datos, `docker compose down -v` borra la base y la crea de nuevo. |
| Los menús de estado y municipio dicen «No se pudo consultar el catálogo del INEGI» | El backend no llega a `gaia.inegi.org.mx`. Usa el INEGI de mentira (sección 2). |
| Las pruebas de navegador fallan en el acceso de `L1` o `F1` | Corre `seed_e2e` antes de cada corrida; las pruebas dejan esas cuentas bloqueadas o con la contraseña cambiada. |
| La primera visita a cada pantalla tarda | Next.js en modo desarrollo compila cada página al primer acceso; las siguientes visitas son rápidas. |
| El CI falla en «La documentación generada está al día» | Corre `python manage.py generar_docs` y sube los cambios de `docs/`. |
| El CI falla en «Migraciones al día» | Cambiaste un modelo sin migración: `python manage.py makemigrations`. |
