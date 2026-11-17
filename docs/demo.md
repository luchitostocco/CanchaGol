# Demostración · 5 minutos

Antes de exponer, ejecutá `migrate` y `demo`. Prepará una cuenta administradora y una cuenta cliente. Podés usar ventanas distintas del navegador para mantener las dos sesiones abiertas.

| Tiempo | Qué mostrar |
| --- | --- |
| 0:00–0:35 | Explicá el problema de administrar reservas por mensajes y mostrá la búsqueda F5 por fecha. |
| 0:35–1:40 | Como cliente, elegí un turno de pasado mañana, revisá el precio y confirmá. Mostrá el número y el importe. Buscá de nuevo para comprobar que salió de la disponibilidad. |
| 1:40–2:15 | Cancelá esa reserva desde **Mis reservas**. Mostrá el estado Cancelada y volvé a buscar el horario liberado. |
| 2:15–3:45 | Confirmá otra vez ese horario. Como administrador, filtrá por fecha, cambiá el precio del turno y comparalo con el importe de la reserva. Bloqueá el turno por lluvia autorizando la cancelación y verificá que desaparece de la disponibilidad. |
| 3:45–5:00 | Mostrá las dos historias en Hecho y el historial de commits. Señalá la migración con `turno_ocupado` y el resultado de la prueba de concurrencia. |

La demostración usa la aplicación y datos de prueba. Para repetirla, habilitá el turno bloqueado o elegí otro horario futuro.
