import hashlib
import hmac
import json

from src.config import get_settings


async def test_ghl_webhook_upserts_lead_and_property(client):
    response = await client.post(
        "/webhooks/ghl",
        json={
            "contact_id": "abc123",
            "first_name": "John",
            "last_name": "Smith",
            "phone": "+14045550100",
            "custom_fields": {
                "property_address": "123 Main St",
                "county": "Gwinnett",
                "situation": "inherited",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    leads = await client.get("/api/leads", params={"county": "Gwinnett", "status": "new"})
    assert leads.status_code == 200
    body = leads.json()
    assert body["count"] == 1
    assert body["leads"][0]["property"]["address"] == "123 Main St"


async def test_ghl_webhook_accepts_highlevel_contact_payload(client):
    response = await client.post(
        "/webhooks/ghl",
        json={
            "id": "contact-789",
            "firstName": "Avery",
            "lastName": "Morgan",
            "phone": "+17705550123",
            "email": "avery@example.com",
            "source": "facebook",
            "status": "warm",
            "customFields": [
                {"key": "property_address", "field_value": "88 Peachtree Ave"},
                {"key": "city", "field_value": "Atlanta"},
                {"key": "county", "field_value": "Fulton"},
                {"key": "state", "field_value": "GA"},
                {"key": "situation", "field_value": "vacant"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"

    leads = await client.get("/api/leads", params={"county": "Fulton", "status": "warm"})
    assert leads.status_code == 200
    body = leads.json()
    assert body["count"] == 1
    assert body["leads"][0]["ghl_id"] == "contact-789"
    assert body["leads"][0]["property"]["address"] == "88 Peachtree Ave"


async def test_ghl_webhook_validates_shared_secret_signature(client, monkeypatch):
    monkeypatch.setenv("GHL_WEBHOOK_SECRET", "test-shared-secret")
    get_settings.cache_clear()

    payload = {
        "contact_id": "signed-123",
        "first_name": "Signed",
        "custom_fields": {"county": "Gwinnett"},
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(b"test-shared-secret", body, hashlib.sha256).hexdigest()

    response = await client.post(
        "/webhooks/ghl",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Clearpath-Signature": f"sha256={signature}",
        },
    )

    assert response.status_code == 200


async def test_ghl_webhook_accepts_static_shared_secret_header(client, monkeypatch):
    monkeypatch.setenv("GHL_WEBHOOK_SECRET", "test-shared-secret")
    get_settings.cache_clear()

    response = await client.post(
        "/webhooks/ghl",
        json={"contact_id": "static-secret-123", "custom_fields": {"county": "Gwinnett"}},
        headers={"X-Clearpath-Webhook-Secret": "test-shared-secret"},
    )

    assert response.status_code == 200


async def test_ghl_webhook_rejects_invalid_shared_secret_signature(client, monkeypatch):
    monkeypatch.setenv("GHL_WEBHOOK_SECRET", "test-shared-secret")
    get_settings.cache_clear()

    response = await client.post(
        "/webhooks/ghl",
        json={"contact_id": "rejected-123"},
        headers={"X-Clearpath-Signature": "sha256=bad"},
    )

    assert response.status_code == 401
