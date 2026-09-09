# LlachMetrics API

API REST para registro y autenticacion de usuarios con FastAPI, SQLAlchemy y PostgreSQL.

Las contraseñas se protegen con Argon2id. Cada llamada a `hash_password` genera un
`salt` criptograficamente aleatorio y diferente; el salt queda incluido en el hash
codificado, por lo que no se almacena como un campo separado. Durante el login,
Argon2 extrae ese salt del hash guardado para verificar la contraseña.

## Puesta en marcha

1. Crea una base de datos PostgreSQL llamada `llachmetrics`.
2. Crea y activa el entorno virtual:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Instala las dependencias:

   ```powershell
   pip install -r requirements.txt
   ```

4. Copia `.env.example` como `.env` y ajusta `DATABASE_URL` y `JWT_SECRET_KEY`.
5. Arranca la API:

   ```powershell
   uvicorn app.main:app --reload
   ```

La documentacion interactiva queda disponible en `http://localhost:8000/docs`.

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
