import json
import logging

from fastapi import FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import get_settings
from app.whatsapp import (
    WhatsAppError,
    download_image,
    image_message_from_payload,
    verify_signature,
)


logger = logging.getLogger(__name__)
settings = get_settings()
app = FastAPI(title="LlachMetrics WhatsApp API", version="1.0.0")


class HealthResponse(BaseModel):
    status: str


class WebhookResponse(BaseModel):
    status: str
    reason: str | None = None
    message_id: str | None = None
    sender: str | None = None
    caption: str | None = None
    file: str | None = None


@app.get("/health")
def health_check() -> HealthResponse:
    """Return the availability of this REST API."""
    return {"status": "ok"}


@app.get("/webhook/whatsapp")
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> int | str:
    """Verify the webhook subscription requested by Meta."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return hub_challenge or ""
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token de verificación inválido")


@app.post("/webhook/whatsapp", response_model_exclude_none=True)
async def receive_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> WebhookResponse:
    """Receive a WhatsApp event and persist an attached image."""
    raw_payload = await request.body()
    if not verify_signature(raw_payload, x_hub_signature_256, settings.whatsapp_app_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Firma inválida")

    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON inválido") from error

    image = image_message_from_payload(payload)
    if image is None:
        return WebhookResponse(status="ignored", reason="no_image_message")

    try:
        destination = await download_image(image, settings)
    except WhatsAppError as error:
        logger.warning("No se pudo guardar la imagen de WhatsApp: %s", error)
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=WebhookResponse(
                status="deferred",
                reason="whatsapp_unavailable",
                message_id=image["message_id"],
                sender=image["sender"],
                caption=image["caption"],
            ).model_dump(exclude_none=True),
        )

    return WebhookResponse(
        status="received",
        message_id=image["message_id"],
        sender=image["sender"],
        caption=image["caption"],
        file=str(destination),
    )
