# LlachMetrics API

API REST para registro y autenticacion de usuarios con FastAPI, SQLAlchemy y PostgreSQL.

Las contraseñas se protegen con Argon2id. Cada llamada a `hash_password` genera un
`salt` criptograficamente aleatorio y diferente; el salt queda incluido en el hash
codificado, por lo que no se almacena como un campo separado. Durante el login,
Argon2 extrae ese salt del hash guardado para verificar la contraseña.

## Puesta en marcha

1. Crea y activa el entorno virtual:

   **Linux / macOS (Bash / Zsh):**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   **Windows (PowerShell):**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Instala las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Copia `.env.example` como `.env` y ajusta `DATABASE_URL` y `JWT_SECRET_KEY`:

   **Linux / macOS:**
   ```bash
   cp .env.example .env
   ```

   **Windows (PowerShell):**
   ```powershell
   Copy-Item .env.example .env
   ```

   Ambas variables son obligatorias; `.env` es local y no se incluye en Git.
   Usa una clave JWT aleatoria y larga, y no reutilices contraseñas reales en
   `.env.example`.
4. Crea la base de datos configurada en `DATABASE_URL` (el usuario PostgreSQL
   debe tener permiso para crear bases de datos):

   ```bash
   python scripts/create_database.py
   ```

   Para probar con otro nombre sin tocar la base configurada:

   ```bash
   python scripts/create_database.py --name llachmetrics_test
   ```

5. Arranca la API:

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

La documentacion interactiva queda disponible en `http://localhost:8000/docs`.
Para compartir la API mediante el reenvío de puertos de VS Code, reenvía el
puerto `8000` como público y configura `CORS_ORIGINS` en `.env` con el origen
HTTPS del frontend. No incluyas una barra final en el origen.

## Esquema de usuarios

SQLAlchemy crea estas tablas en PostgreSQL:

- `"user"`: `id` integer autogenerado, `email` text y `full_name` text.
- `pwd_hash`: `id` integer, clave foranea a `"user".id`, y `hash` text.

El nombre `"user"` se cita porque `user` puede ser una palabra reservada en
PostgreSQL. `create_all` crea las tablas que no existen, pero no migra tablas
anteriores como `users`; si ya existe el esquema antiguo, hay que migrarlo o
eliminarlo antes de arrancar.

## Endpoints

- `GET /health`: comprobacion de estado.
- `POST /auth/register`: crea un usuario. Recibe JSON con `email`, `password` y `full_name` opcional.
- `POST /auth/login`: recibe formulario OAuth2 (`username` es el email y `password`) y devuelve un JWT.
- `GET /auth/me`: devuelve el usuario autenticado. Usa `Authorization: Bearer <token>`.

## Datos para el frontend

- `GET /data/dashboard`: resumen agregado y estado de cada vehículo.
- `GET /data/readings`: totales de kilómetros, costo, presiones y profundidad de surcos.
- `GET /data/vehicles`: métricas agregadas por patente, incluido el último registro de presión.
- `GET /data/vehicles/{patente}/series`: serie histórica de viajes y presión de un vehículo.
- `GET /data/trips`: serie histórica de toda la flota, incluyendo la patente.

Estos endpoints leen las tablas `Neumatico`, `Vehiculo`, `Viaje-Vehiculo`, `Viaje` y
`Conductor`. La API no genera valores para temperatura, ruta o predicciones porque
esas columnas no existen en el esquema actual.

## Poblar datos de prueba

Desde la carpeta `BackEnd`, con el entorno virtual activo:

```powershell
python scripts/seed_database.py
```

Para cargar en una base alternativa (por ejemplo, la base temporal de prueba),
usa `--database-name` o su alias `--name`:

```powershell
python scripts/seed_database.py --database-name llachmetrics_test
```

El script lee `../synthetic.csv`, crea una flota reutilizable de 12 vehículos
y 8 conductores, y carga viajes, relaciones viaje-vehículo y cuatro neumáticos
por cada viaje. Para volver a cargar desde cero las tablas de negocio:

```powershell
python scripts/seed_database.py --reset-business-data
```

## Probar con una base de datos aislada

Estos pasos crean y pueblan `llachmetrics_test` sin cambiar la base indicada
en `.env`. Ejecuta los comandos desde `BackEnd`, con PostgreSQL activo y el
entorno virtual habilitado:

```powershell
python scripts/create_database.py --name llachmetrics_test
python scripts/seed_database.py --database-name llachmetrics_test --reset-business-data
```

Para que la API lea esa base, detén cualquier instancia activa con `Ctrl+C` y,
en la misma terminal de PowerShell, elimina un posible override anterior y
deriva una URL de prueba a partir de las credenciales de `.env`:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$env:DATABASE_URL = & .\.venv\Scripts\python.exe -c "from app.config import get_settings; from sqlalchemy.engine import make_url; print(make_url(get_settings().database_url).set(database='llachmetrics_test').render_as_string(hide_password=False))"
uvicorn app.main:app --reload
```

La API crea las tablas automáticamente al arrancar. Abre `http://localhost:8000/docs`
y usa `POST /auth/register` para crear un usuario en la base de prueba; después
inicia sesión en el frontend con ese usuario. Los usuarios de la base original
no existen en la base aislada a menos que los registres allí también.

Para volver a la base definida en `.env`, detén la API con `Ctrl+C`, elimina el
override en esa terminal y vuelve a arrancar el servidor:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
uvicorn app.main:app --reload
```

La base de prueba se puede conservar para volver a usarla. Si quieres borrarla,
hazlo solo cuando la API ya no esté conectada a ella y después de confirmar que
no necesitas sus datos.
