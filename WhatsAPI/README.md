# WhatsAPI — Extractor OCR de Documentos (LlachMetrics)

Aplicación web desarrollada con **React**, **Vite**, **FastAPI** y **EasyOCR** para subir fotografías de documentos (órdenes de inspección, guías de despacho, facturas o fichas de vehículos), extraer automáticamente sus datos y permitir fusionar gráficamente cajas de texto para ajustar los campos autodetectados.

## Funcionamiento en paralelo con la aplicación principal

Esta aplicación está configurada con puertos dedicados y políticas de CORS compatibles para ejecutarse simultáneamente junto a la aplicación principal sin ningún conflicto:

| Servicio | Entorno | Puerto por defecto | Proxy / Destino API |
| :--- | :--- | :--- | :--- |
| **FrontEnd principal** | React + Vite | `http://localhost:5173` | `/api` → `http://127.0.0.1:8000` |
| **BackEnd principal** | FastAPI + PostgreSQL | `http://localhost:8000` | CORS habilitado para `5173`, `5174` y `5175` |
| **WhatsAPI Frontend** | React + Vite | `http://localhost:5175` | `/api` → `http://127.0.0.1:8001` |
| **WhatsAPI EasyOCR API** | FastAPI + EasyOCR | `http://127.0.0.1:8001` | CORS permisivo (`allow_origin_regex`) |

## Ejecución rápida

Desde la carpeta `WhatsAPI/`:

```bash
npm run dev
```

Al ejecutar `npm run dev`, Vite inicia la interfaz en `http://localhost:5175` y el plugin integrado levanta automáticamente en segundo plano el servidor Python de **EasyOCR** en `http://127.0.0.1:8001`.

Si prefieres ejecutar la API de EasyOCR en una terminal separada:

```bash
npm run api
# o directamente:
.venv/bin/uvicorn ocr_server:app --reload --host 0.0.0.0 --port 8001
```
