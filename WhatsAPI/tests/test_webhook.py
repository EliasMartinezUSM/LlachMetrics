from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_verification() -> None:
    response = client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "change-this-token",
            "hub.challenge": "challenge-123",
        },
    )
    assert response.status_code == 200
    assert response.text == '"challenge-123"'


def test_non_image_message_is_ignored() -> None:
    response = client.post(
        "/webhook/whatsapp",
        json={"entry": [{"changes": [{"value": {"messages": [{"type": "text"}]}}]}]},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "ignored", "reason": "no_image_message"}


def test_image_is_deferred_when_whatsapp_is_disabled() -> None:
    response = client.post(
        "/webhook/whatsapp",
        json={
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "id": "message-123",
                                        "from": "34600000000",
                                        "type": "image",
                                        "image": {"id": "media-123"},
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        },
    )
    assert response.status_code == 202
    assert response.json()["status"] == "deferred"
    assert response.json()["reason"] == "whatsapp_unavailable"
