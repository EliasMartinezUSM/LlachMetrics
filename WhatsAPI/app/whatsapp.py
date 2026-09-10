import hashlib
import hmac
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.config import Settings


ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


class WhatsAppError(Exception):
    """Raised when WhatsApp cannot provide a usable image."""


def verify_signature(payload: bytes, signature: str | None, app_secret: str) -> bool:
    if not app_secret:
        return True
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature.removeprefix("sha256="), expected)


def image_message_from_payload(payload: dict[str, Any]) -> dict[str, str] | None:
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                if message.get("type") == "image" and message.get("image", {}).get("id"):
                    return {
                        "message_id": message.get("id", ""),
                        "media_id": message["image"]["id"],
                        "sender": message.get("from", ""),
                        "caption": message.get("image", {}).get("caption", ""),
                    }
    return None


async def download_image(
    image: dict[str, str], settings: Settings, client: httpx.AsyncClient | None = None
) -> Path:
    if not settings.whatsapp_enabled:
        raise WhatsAppError("La integración con WhatsApp está deshabilitada")
    if not settings.whatsapp_access_token:
        raise WhatsAppError("WHATSAPP_ACCESS_TOKEN no está configurado")

    api_base = f"https://graph.facebook.com/{settings.whatsapp_api_version}"
    own_client = client is None
    http_client = client or httpx.AsyncClient(timeout=30)
    try:
        media_response = await http_client.get(
            f"{api_base}/{image['media_id']}",
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        )
        media_response.raise_for_status()
        media = media_response.json()
        media_url = media.get("url")
        if not media_url:
            raise WhatsAppError("WhatsApp no devolvió una URL para la imagen")

        image_response = await http_client.get(
            media_url,
            headers={"Authorization": f"Bearer {settings.whatsapp_access_token}"},
        )
        image_response.raise_for_status()
        content_type = image_response.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise WhatsAppError(f"Tipo de imagen no permitido: {content_type or 'desconocido'}")
        if len(image_response.content) > settings.max_image_size_bytes:
            raise WhatsAppError("La imagen supera el tamaño máximo permitido")

        extension = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}[content_type]
        settings.download_dir.mkdir(parents=True, exist_ok=True)
        destination = settings.download_dir / f"{uuid.uuid4().hex}{extension}"
        destination.write_bytes(image_response.content)
        return destination
    except httpx.HTTPError as error:
        raise WhatsAppError("No se pudo descargar la imagen desde WhatsApp") from error
    finally:
        if own_client:
            await http_client.aclose()
