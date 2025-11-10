# Levantar la aplicación con Docker

Este repositorio contiene tres servicios principales:

- MySQL (Moscowle_Complete)
- Backend FastAPI (puerto 8001)
- Frontend público (Principal_Page) servido en nginx (puerto 3002)
- Dashboard administrativo (Dashboard Administrativo Integral) servido en nginx (puerto 3001)

Nota: Para evitar conflictos si ya tienes MySQL local en el puerto 3306, el contenedor MySQL está mapeado al puerto 3307 en el host. Conéctate desde MySQL Workbench a localhost:3307 (usuario `root`, contraseña `Rucula_530`).

Inicialización automática de la base de datos
------------------------------------------
Este `docker-compose.yml` incluye un servicio `db_init` que ejecuta `init_db.py` (ubicado en `backend_messaging/`) una sola vez al arrancar la pila. El orden es:

1. MySQL (`db`) arranca y pasa su healthcheck.
2. `db_init` se ejecuta y crea la base de datos y tablas usando `init_database.sql`.
3. `backend` arranca (solo después de `db_init`) y ya encontrará las tablas creadas.

Si necesitas volver a ejecutar la inicialización manualmente puedes usar:

```bash
docker compose run --rm db_init
```

Nota: el servicio `db_init` está configurado para no reiniciarse (`restart: 'no'`).
Requisitos:
- Docker y Docker Compose v2 instalados

Comandos básicos:

1) Construir y levantar todo:

```bash
cd /ruta/al/proyecto/moscowle
docker compose up --build
```

2) Para ejecutar en segundo plano:

```bash
docker compose up -d --build
```

3) Parar y eliminar contenedores:

```bash
docker compose down
```

Notas importantes:
- La contraseña root de MySQL está tomada de `backend_messaging/.env` (Rucula_530) y la base de datos se crea como `Moscowle_Complete`.
- El backend toma variables desde `backend_messaging/.env` por medio del `env_file` en `docker-compose.yml`. Revisa y cambia SECRET_KEY antes de usar en producción.
- Los frontends están configurados para hacer proxy de las rutas `/api/` al servicio backend dentro de la red de docker-compose (`moscowle_backend:8001`). Asegúrate que las llamadas desde el frontend usan rutas relativas como `/api/...` o ajusta `VITE_` variables en cada proyecto si hicieras uso de `VITE_API_URL`.

Problemas comunes:
- Si los frontends intentan acceder a `http://localhost:8001` desde el navegador, y el backend está en el contenedor, es mejor usar rutas relativas o exponer y mapear puertos como se hace en el `docker-compose.yml`.
- Si la base de datos ya existe localmente, el contenedor MySQL usará el volumen `db_data`.

Si quieres que el compose cree la base de datos y datos iniciales automáticamente mediante un script, puedo añadir un servicio init que ejecute los scripts SQL o ejecute `init_db.py` del backend.
