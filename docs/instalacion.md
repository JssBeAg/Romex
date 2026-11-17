# Instalación

## Con Docker (recomendado)

Requisitos: Docker y Docker Compose.

1. Crea el archivo `.env` en la raíz con, como mínimo:

   ```env
   POSTGRES_DB=romex
   POSTGRES_USER=romex
   POSTGRES_PASSWORD=cambia-esta-contraseña
   POSTGRES_HOST=db
   POSTGRES_PORT=5432
   DJANGO_SECRET_KEY=una-clave-larga-y-aleatoria
   DJANGO_DEBUG=1
   DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
   CORS_ALLOWED_ORIGINS=http://localhost:3000
   NEXT_PUBLIC_API_URL=http://localhost:8000
   PGDATA=/var/lib/postgresql/data/pgdata
   ```

   Lo más fácil: `cp .env.example .env` y cambia la contraseña y la clave secreta.

2. `docker compose up --build`. Al arrancar, el backend ejecuta solo `migrate` y `sync_roles` (crea los roles).
3. Crea el primer administrador: `docker compose exec backend python manage.py createsuperuser`.
4. Entra a <http://localhost:3000> con esa matrícula. El administrador da de alta al resto desde el panel de Django (<http://localhost:8000/admin/>) y el gerente desde **Trabajadores**.

Servicios: base `:5432`, API `:8000`, interfaz `:3000`. Los datos viven en los volúmenes `postgres_data` y `media_data` (fotos de evidencia de los reportes y fotografías de perfil).

## Actualizar a una versión nueva

1. Lee el [CHANGELOG](../CHANGELOG.md): indica si hay migraciones nuevas o si conviene recrear la base.
2. `docker compose up --build` aplica las migraciones al arrancar.
3. Para empezar de cero (se pierden los datos): `docker compose down -v`.

## Sin Docker (desarrollo)

```bash
# Backend
cd backend
pip install -r requirements.txt
python manage.py migrate && python manage.py sync_roles
python manage.py runserver 8000

# Frontend
cd frontend
npm install && npm run dev
```

## Correr las pruebas

```bash
docker compose exec backend python manage.py test tests
```

Las pruebas de navegador necesitan `seed_e2e` y Playwright: ver [pruebas.md](pruebas.md).

## Regenerar la documentación automática

```bash
python manage.py generar_docs
```
