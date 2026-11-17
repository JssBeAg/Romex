# Roles y permisos

Hay cuatro roles (grupos de Django). El rol se revisa en la API; el frontend solo decide qué mostrar.

| Rol | Quién es |
|---|---|
| **Administrador** | Superusuario de Django (`createsuperuser`). Entra al panel `/admin/`; no aparece en las listas de trabajadores |
| **Gerente** | Administra trabajadores, unidades, refacciones, planes y asignaciones; ve todo |
| **Mecánico** | Diagnostica y repara los reportes que se le asignaron; registra mantenimientos |
| **Operador** | Reporta fallas y llena checklists de **sus** unidades |

## Matriz

| Función | Gerente | Mecánico | Operador |
|---|:-:|:-:|:-:|
| Dashboard e indicadores | ✔ | | |
| Trabajadores (alta, edición, desbloqueo) | ✔ | | |
| Poner o quitar la fotografía de un trabajador | ✔ | | |
| Ver y editar teléfono con código y contactos adicionales de un trabajador | ✔ | | |
| Ver una fotografía de perfil | todas | la propia | la propia |
| Unidades, placas, operadores asignados | ✔ | | |
| Refacciones e inventario | ✔ | | |
| Poner, ver o quitar la fotografía de una refacción | ✔ | | |
| Kardex de una unidad | ✔ | | |
| Bitácora de auditoría (sin la actividad privada de los administradores) | ✔ | | |
| Planes de preventivo (administrar) | ✔ | | |
| Vencimientos de preventivo (consultar) | ✔ | ✔ | |
| Reportes de falla: ver | todos | solo los asignados | solo los propios |
| Reportes de falla: crear / editar | | | ✔ (propios, mientras estén pendientes) |
| Asignar mecánico a un reporte | ✔ | | |
| Diagnósticos | ver todos | crear/editar los de sus reportes | |
| Mantenimientos | ver todos | crear/editar (sus reportes y preventivos en los que participó) | |
| Checklists | ver todos | | crear/editar propios |
| Notificaciones propias | ✔ | ✔ | ✔ |
| Exportar PDF | lo que puede ver | lo que puede ver | lo que puede ver |
| Cambiar su propia contraseña | ✔ | ✔ | ✔ |

## Reglas de asignación

- Un operador solo puede reportar y hacer checklists de las **unidades que tiene asignadas** y que estén **activas**.
- Una unidad puede tener varios operadores a la vez y un operador varias unidades (historial con fecha de inicio y fin).
- Solo el mecánico asignado a un reporte puede verlo, diagnosticarlo y repararlo.
- Cada usuario tiene **un** rol.
