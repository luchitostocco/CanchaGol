# Kanban · ReservaGol · Parcial 2

Flujo **Por hacer → En curso → En revisión → Hecho**. Límite de dos tarjetas en curso. Las historias pasan a Hecho cuando están implementadas y sus criterios se verificaron en la aplicación o con pruebas.

| Por hacer | En curso | En revisión | Hecho |
| --- | --- | --- | --- |
| | | | [T01 · Implementar el DER](#t01--implementar-el-der) |
| T05 · Presentar y entregar el enlace en el campus | | | [HU-01 · Consultar y reservar](#hu-01--consultar-y-reservar-una-cancha) |
| | | | [HU-02 · Mantener la agenda](#hu-02--mantener-la-agenda-del-complejo) |
| | | | [T02 · Verificar persistencia y concurrencia](#t02--verificar-persistencia-y-concurrencia) |
| | | | [T03 · Preparar la demo](demo.md) |
| | | | [T04 · Publicar el repositorio](#t04--publicar-el-repositorio) |

## HU-01 · Consultar y reservar una cancha

Como cliente, quiero consultar canchas por fecha y modalidad para reservar un turno con horario y precio confirmados.

- [x] Registro e ingreso por correo para clientes activos.
- [x] Disponibilidad de turnos futuros, habilitados y libres en canchas activas.
- [x] Resumen con cancha, fecha, horario y precio. Confirmación con número de reserva.
- [x] Una sola reserva ocupante por turno, con restricción de unicidad en la base.
- [x] Dos intentos simultáneos en MySQL dejan una sola confirmación.
- [x] Cancelación propia con 24 horas o más de anticipación. El horario vuelve a ofrecerse si está habilitado.
- [x] Rechazo de cancelaciones tardías y acceso bloqueado a reservas de otros clientes.

## HU-02 · Mantener la agenda del complejo

Como administrador, quiero gestionar canchas, precios y horarios para ofrecer turnos que el complejo pueda prestar.

- [x] Alta, edición y baja lógica de canchas. La baja exige resolver las confirmaciones futuras.
- [x] Turnos futuros de 60 minutos, sin superposiciones por cancha y con precio no negativo.
- [x] Cambio del precio publicado con conservación del importe acordado en reservas existentes.
- [x] Bloqueo con motivo. Si hay una reserva confirmada, exige autorizar la cancelación y guarda ambos cambios en una transacción.
- [x] Filtro por fecha, cancha y estado. Solo permite completar una reserva confirmada después del fin del turno.
- [x] Gestión restringida a administradores desde el servidor.

## T01 · Implementar el DER

- [x] Migraciones para las cinco tablas del diseño.
- [x] Relaciones, restricciones de duración y precio, y columna calculada `turno_ocupado`.
- [x] Carga inicial de F5, F7, F8 y F11.

## T02 · Verificar persistencia y concurrencia

- [x] Probar interfaz, permisos, precios y transiciones con las pruebas de Django en SQLite.
- [x] Ejecutar migraciones y pruebas en MySQL, incluida la confirmación simultánea. Las diez pruebas pasaron con MySQL 9.5.

## T04 · Publicar el repositorio

- [x] Revisar los archivos ignorados y dejar los commits de las etapas.
- [x] Crear el repositorio en la cuenta de GitHub del autor y subir `main`.
- [x] Verificar el enlace y el acceso para la corrección. Repositorio público en https://github.com/luchitostocco/CanchaGol.

## Seguimiento del desarrollo

| Fecha | Movimiento | Evidencia |
| --- | --- | --- |
| 17/11/2026 | T01 pasó de En curso a Hecho. | Commit con el proyecto inicial y las migraciones. |
| 17/11/2026 | Las dos historias pasaron de En curso a En revisión. | Commit con los flujos de cliente y administrador. |
| 17/11/2026 | HU-02 pasó a Hecho. HU-01 quedó en revisión de concurrencia. | Pruebas de Django de disponibilidad, permisos, bloqueo, importes y estados. |
| 17/11/2026 | T03 pasó a Hecho. | Comando `demo` y guion de cinco minutos. |
| 17/11/2026 | T02 y HU-01 pasaron a Hecho. | Pruebas en MySQL. Dos confirmaciones concurrentes produjeron una sola reserva. |
| 17/11/2026 | T04 pasó a Hecho. | Publicación de `main` en GitHub y verificación de los commits remotos. |

El trabajo avanzó en etapas dentro de una misma sesión. Las fechas corresponden al desarrollo real.
