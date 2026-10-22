# LlachMetrics

LlachMetrics es una aplicación para consultar y analizar métricas de una flota de vehículos pesados. El sistema consiste en una interfaz web, una API con autenticación y una base de datos relacional con información de viajes, vehículos y neumáticos. Con efoque en el mantenimiento preventivo de neumáticos y potenciación del recauchaje en la industria.

LlachMetrics es la solución propuesta al desafío número 24 propuesto por la empresa Gildo Llach para el programa de memorias multidisciplinarias de la Universidad Técnica Federico Santa María.

# Integrantes

- Gustavo Venegas Bravo
- Elías Simón Martínez Rodríguez

# Profesores Guía
- Mauricio Araya
- José Manuel Martínez

## Componentes

- `FrontEnd/`: aplicación de una sola página desarrollada con React y Vite. Incluye paneles de métricas, mediciones y vistas de predicción.
- `BackEnd/`: API REST desarrollada con FastAPI, SQLAlchemy y PostgreSQL. Proporciona autenticación con tokens JWT, contraseñas protegidas con Argon2id y endpoints para consultar métricas de la flota.
- `BackEnd/scripts/seed_database.py`: carga datos de prueba en la base de datos a partir de `synthetic.csv`.
- `generate_fleet_dataset.py`: genera un conjunto de viajes sintético reproducible.
- `Modelo.ipynb`: notebook de exploración y modelado.
- `WhatsAPI/`: módulo auxiliar independiente; no es necesario para ejecutar la aplicación web principal.

## Requisitos

- Node.js y npm para el frontend.
- Python 3.10 o posterior para el backend.
- PostgreSQL instalado y en ejecución. No es necesario crear previamente la base de datos.

## Ejecución local

Inicia el backend y el frontend en terminales separadas. A continuación se presentan las instrucciones tanto para **Linux / macOS (Bash / Zsh)** como para **Windows (PowerShell)**.

### 1. Preparar el backend y crear la base de datos

Instala las dependencias del backend y prepara su configuración local:

**En Linux / macOS (Bash / Zsh):**

```bash
cd BackEnd
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

**En Windows (PowerShell):**

```powershell
cd .\BackEnd\
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Confirma que el servicio de PostgreSQL esté iniciado. Edita `BackEnd/.env` con tus propios valores: `DATABASE_URL` debe incluir el host, puerto, usuario y contraseña de PostgreSQL, y `JWT_SECRET_KEY` debe ser una clave aleatoria larga. Ambas variables son obligatorias. El usuario de PostgreSQL indicado en `DATABASE_URL` debe poder conectarse y tener permiso para crear bases de datos (`CREATEDB`).

Ejemplo de formato para `DATABASE_URL`:

```text
postgresql+psycopg://USUARIO:CONTRASENA@localhost:5432/llachmetrics
```

Crea la base de datos indicada por `DATABASE_URL` con el script del proyecto:

```bash
python scripts/create_database.py
```

El script se conecta al servidor PostgreSQL usando la configuración de `.env` y crea la base si todavía no existe. No hace falta abrir `psql` o pgAdmin ni crear la base manualmente. No cambia ni borra bases existentes. Para crear una base temporal de prueba, se puede indicar otro nombre:

```bash
python scripts/create_database.py --name llachmetrics_test
```

Arranca la API desde la carpeta `BackEnd`:

```bash
uvicorn app.main:app --reload
```

La API estará disponible en `http://localhost:8000`; su documentación interactiva está en `http://localhost:8000/docs` y el estado se puede comprobar en `http://localhost:8000/health`.

### 2. Crear un usuario para ingresar

Con la API en ejecución, abre `http://localhost:8000/docs`, despliega
`POST /auth/register` y selecciona **Try it out**. Envía un cuerpo como este,
cambiando el correo y la contraseña por credenciales propias:

```json
{
	"email": "usuario@ejemplo.com",
	"password": "UnaClaveDePrueba123!",
	"full_name": "Usuario de prueba"
}
```

El correo debe ser válido y la contraseña debe tener entre 8 y 128 caracteres.
Cuando la respuesta sea `201`, el usuario quedó registrado; abre la aplicación
frontend e inicia sesión con ese correo y contraseña. Para una base de datos
temporal, registra el usuario mientras la API está conectada a esa base: las
cuentas no se comparten entre bases de datos.

### 3. Preparar y arrancar el frontend

Abre otra terminal en la raíz del repositorio:

**En Linux / macOS (Bash / Zsh):**

```bash
cd FrontEnd
npm install
cp .env.example .env
npm run dev
```

**En Windows (PowerShell):**

```powershell
cd .\FrontEnd\
npm install
Copy-Item .env.example .env
npm run dev
```

`FrontEnd/.env` permite configurar `VITE_API_URL`; para el backend local utiliza:

```text
VITE_API_URL=http://127.0.0.1:8000
```

La dirección del frontend se mostrará en la terminal de Vite, normalmente `http://localhost:5173`.

## Compartir mediante el reenvío de puertos de VS Code

La aplicación está configurada para usar estos túneles:

- Frontend: `https://88hfzxbh-5173.brs.devtunnels.ms/`
- Backend: `https://88hfzxbh-8000.brs.devtunnels.ms/`

En VS Code, reenvía los puertos `5173` y `8000` y configúralos como **Públicos**
si las personas que recibirán el enlace no pertenecen a tu sesión de VS Code.
Arranca los servidores con una terminal en cada carpeta:

```bash
# BackEnd (con el entorno virtual activo)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# FrontEnd
npm run dev
```

`FrontEnd/.env` define `VITE_API_URL` con el túnel del backend y
`VITE_DEV_TUNNEL_HOST` con el host permitido por Vite. `BackEnd/.env` define
`CORS_ORIGINS` con el origen del frontend. Si VS Code asigna otras direcciones,
actualiza esos tres valores y reinicia ambos servidores; Vite incorpora las
variables al iniciar. CORS permite que el navegador use la API desde el frontend,
pero no sustituye autenticación ni hace privado un túnel configurado como público.

## Cargar datos de prueba

Con PostgreSQL activo y el entorno virtual del backend habilitado, ejecuta desde `BackEnd/`:

```bash
python scripts/seed_database.py
```

Para poblar una base alternativa de pruebas en lugar de la definida en
`DATABASE_URL`, indica su nombre:

```bash
python scripts/seed_database.py --database-name llachmetrics_test
```

Para reemplazar los datos de negocio existentes antes de volver a cargarlos:

```bash
python scripts/seed_database.py --reset-business-data
```

El cargador utiliza `synthetic.csv`, crea registros de vehículos y conductores, y agrega viajes, presiones y datos de neumáticos.


