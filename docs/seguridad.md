# Seguridad de cuentas

## Acceso

- Inicio de sesión con **matrícula y contraseña**; sesión de Django con cookie y **token CSRF** en cada cambio.
- Las cuentas solo las crea el administrador o el gerente. No hay registro público ni recuperación por correo: el gerente restablece la contraseña desde **Trabajadores**.
- **La sesión caduca tras 8 horas sin actividad** (se renueva con cada petición).

## Contraseñas

- Reglas (validadores de Django): mínimo 8 caracteres, no solo números, no una contraseña común, no parecida a los datos de la persona; además, distinta de la actual y de la matrícula.
- Se guardan con el *hash* de Django (PBKDF2); la bitácora nunca las registra.
- **Cambio obligatorio**: cuando el gerente crea una cuenta o restablece la contraseña, la persona **debe elegir una nueva** al entrar. Mientras no lo haga, el backend rechaza todo salvo `/api/auth/` (aunque se llame a la API directamente) y el frontend solo muestra la pantalla de cambio.
- Cualquier usuario puede cambiar su contraseña en **Contraseña** (menú superior); pide la actual. Al cambiarla, la sesión sigue abierta.

## Bloqueo por intentos fallidos

- **5 intentos fallidos seguidos** bloquean la cuenta **15 minutos**. Durante el bloqueo no entra ni con la contraseña correcta (respuesta 423).
- Un acceso correcto reinicia el contador.
- El gerente puede **desbloquear** guardando al trabajador (la lista muestra la etiqueta *Bloqueada*).
- Cada bloqueo queda en la bitácora y avisa a los gerentes (salvo el de una cuenta de administración: los gerentes no las administran, así que no se les avisa ni ven esa línea).

## Fotografías de perfil

- Se entregan solo con sesión iniciada y solo a su dueño o al gerente (`GET /api/trabajadores/<id>/foto/`); no hay carpeta pública. El navegador las pide con la cookie y las muestra desde una dirección temporal.
- Lo que se sube **nunca se guarda tal cual**: se comprueba el contenido real (no el nombre ni el tipo que declara el archivo), se rechaza lo que no sea JPG/PNG/WebP o pase de 5 MB o 50 millones de píxeles, y se vuelve a generar como JPG de 512 × 512 con un nombre aleatorio. Así se descartan metadatos como la ubicación GPS y archivos disfrazados de imagen.
- Se entregan con `X-Content-Type-Options: nosniff` y `Cache-Control: private`. Subir, cambiar o quitar queda en la bitácora.

## Fotografías de refacciones

- Mismas protecciones que las de perfil (se vuelven a generar como JPG con nombre aleatorio, se verifica el contenido real, `nosniff`, `Cache-Control: private`), pero **solo el gerente** puede pedirlas, subirlas o quitarlas (`/api/refacciones/<id>/foto/`); mecánicos y operadores reciben 403 y sin sesión, 401.
- En el panel de administración el campo de la foto está oculto a propósito: subirla ahí se saltaría la revisión.

## Datos de contacto

- Los teléfonos y correos adicionales de un trabajador solo los ven y editan los gerentes (`trabajadores/…`); ningún otro rol los recibe. Cada persona sigue viendo únicamente sus propios datos básicos.
- Todo se valida en el servidor: código existente y activo, solo dígitos, máximo de 15 dígitos entre código y número, correo válido, máximo de 3 contactos, sin repetidos, y que un contacto solo se pueda modificar si pertenece al trabajador que se está editando. La base de datos además impide guardar un número sin código o un correo con código (`CHECK`).

## Constantes

Están en `backend/accounts/security.py` (`MAX_FAILED_ATTEMPTS`, `LOCK_MINUTES`) y en `config/settings.py` (`SESSION_COOKIE_AGE`).

## Lo que no cubre (todavía)

Autenticación de dos factores, recuperación por correo, expiración periódica de contraseñas y *rate limit* por IP. Para producción además: `DJANGO_DEBUG=0`, HTTPS, cookies `Secure` y una `DJANGO_SECRET_KEY` propia.
