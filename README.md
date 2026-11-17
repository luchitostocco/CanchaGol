# ReservaGol

Sistema de reservas de canchas de fútbol para un complejo deportivo. Trabajo Parcial 2 de Análisis y Metodología de Sistemas.

- **Cliente:** se registra con su correo, busca turnos F5, F7, F8 o F11, confirma un horario y consulta su historial. Puede cancelar una reserva propia con al menos 24 horas de anticipación.
- **Administrador:** da de alta y desactiva canchas, publica turnos de 60 minutos, cambia precios, cancela y bloquea por contingencias, filtra la agenda y completa reservas de turnos finalizados.

## Abrir y ejecutar en VS Code

Abrí esta carpeta en VS Code. Si ya hay un entorno `.venv`, empezá por aplicar las migraciones. Para crear un entorno desde cero necesitás Python 3.12 y una terminal PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py demo
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

Abrí [ReservaGol](http://127.0.0.1:8000/). Entrá con el correo y la contraseña que definiste en `createsuperuser` para ver **Gestionar agenda**. Para probar como cliente usá **Crear cuenta**. Los datos de demo son ficticios y las fechas se calculan al ejecutar el comando.

## Base de datos

SQLite permite ejecutar la demo de inmediato. Para usar **MySQL 8.4 o posterior** y reproducir el motor del diseño del Parcial 1, creá una base vacía `reservagol` con `utf8mb4` en Workbench y usá una cuenta con permisos sobre ese esquema. En una terminal PowerShell de VS Code:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-mysql.txt
$env:MYSQL_DATABASE = 'reservagol'
$env:MYSQL_USER = 'reservagol'
$env:MYSQL_PASSWORD = Read-Host 'Contraseña MySQL' -MaskInput
.\.venv\Scripts\python.exe manage.py migrate
```

Podés indicar `MYSQL_HOST` y `MYSQL_PORT` si tu servidor usa otra dirección o puerto. Con esas variables en la misma terminal, ejecutá `demo`, `createsuperuser` y `runserver`.

Las migraciones crean las tablas `usuario`, `tipo_cancha`, `cancha`, `turno` y `reserva`, además de las tablas internas de Django. `usuario.last_login` registra el último ingreso con el mecanismo de sesiones de Django. `reserva.turno_ocupado` es una columna generada con índice único. Vale el ID del turno para reservas confirmadas o completadas, y `NULL` para las canceladas. Cada reserva conserva su importe acordado y su historial.

## Arquitectura

Django organiza MVC como Model–Template–View. `agenda/models.py` modela las tablas usando el ORM, `agenda/templates/` presenta las pantallas y `agenda/views.py` controla peticiones, permisos y respuestas. `agenda/services.py` concentra las operaciones transaccionales, con bloqueo de la cancha y del turno al modificar su agenda. La disponibilidad se calcula sobre turnos futuros habilitados en canchas activas.

## Verificación y entrega

```powershell
.\.venv\Scripts\python.exe manage.py test
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Para ejecutar las pruebas con MySQL, la cuenta local de pruebas debe poder crear y eliminar el esquema temporal `test_reservagol`. Los horarios se muestran en hora de Buenos Aires y los importes en pesos argentinos.

- [Tablero Kanban y criterios de las historias](docs/kanban.md)
- [Guion de demostración de cinco minutos](docs/demo.md)

El repositorio versiona código y migraciones. Git ignora el entorno virtual, la base local, los archivos `.sql` y las variables sensibles.

Para publicar desde VS Code, abrí **Control de código fuente** y elegí **Publish to GitHub**. Iniciá sesión con tu cuenta, elegí el nombre `reservagol` y definí la visibilidad. Si el repositorio es privado, dale acceso al docente antes de entregar el enlace en el campus.
