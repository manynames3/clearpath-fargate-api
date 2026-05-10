from datetime import datetime, timedelta, timezone

from src.config import get_settings
from src.database import get_session_factory
from src.models import FollowUp, Lead, Property


async def test_leads_filters_by_days_since_contact(client):
    async with get_session_factory()() as session:
        lead = Lead(ghl_id="old-contact", first_name="Ava", status="warm", county="Gwinnett")
        session.add(lead)
        await session.flush()
        session.add(Property(lead_id=lead.id, address="55 Lake Dr", county="Gwinnett", state="GA"))
        session.add(
            FollowUp(
                lead_id=lead.id,
                method="sms",
                contacted_at=datetime.now(timezone.utc) - timedelta(days=45),
            )
        )
        await session.commit()

    response = await client.get(
        "/api/leads",
        params={"county": "Gwinnett", "status": "warm", "days_since_contact": 30},
    )

    assert response.status_code == 200
    assert response.json()["count"] == 1


async def test_leads_requires_api_key_when_configured(client, monkeypatch):
    monkeypatch.setenv("CLEARPATH_API_KEY_SECRET", "lead-api-key")
    get_settings.cache_clear()

    response = await client.get("/api/leads")

    assert response.status_code == 401


async def test_leads_rejects_invalid_api_key(client, monkeypatch):
    monkeypatch.setenv("CLEARPATH_API_KEY_SECRET", "lead-api-key")
    get_settings.cache_clear()

    response = await client.get("/api/leads", headers={"X-Clearpath-API-Key": "wrong"})

    assert response.status_code == 401


async def test_leads_accepts_valid_api_key(client, monkeypatch):
    monkeypatch.setenv("CLEARPATH_API_KEY_SECRET", "lead-api-key")
    get_settings.cache_clear()

    response = await client.get("/api/leads", headers={"X-Clearpath-API-Key": "lead-api-key"})

    assert response.status_code == 200
