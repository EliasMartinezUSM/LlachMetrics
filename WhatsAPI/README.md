# WhatsAPI

API independiente para recibir imágenes mediante WhatsApp Cloud API de Meta.

## Puesta en marcha

```powershell
cd WhatsAPI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8001
```

Por defecto la API funciona en modo local y no intenta conectarse a WhatsApp. Para activar la integración configura `WHATSAPP_ENABLED=true`, el token de acceso, el secreto de la aplicación y el token de verificación de Meta. En el panel de Meta configura el webhook `https://TU_DOMINIO/webhook/whatsapp` con el mismo token de verificación y suscribe el campo `messages`.

## Flujo

- `GET /webhook/whatsapp` valida la suscripción de Meta.
- `POST /webhook/whatsapp` valida la firma, detecta imágenes, obtiene su URL temporal desde Graph API y las guarda en `DOWNLOAD_DIR`.
- `GET /health` comprueba que el servicio está disponible.

Si WhatsApp está deshabilitado o no está disponible, la API continúa ejecutándose y responde `202 Accepted` con `status: deferred` para las imágenes. Así el webhook no provoca una caída del servicio.

Solo se aceptan JPEG, PNG y WebP de hasta `MAX_IMAGE_SIZE_MB`. El archivo queda preparado para conectar el procesamiento posterior en `app/whatsapp.py` o en un worker separado.
