import hashlib
import hmac
import json

from sqlalchemy import select

from src.config import get_settings
from src.database import get_session_factory
from src.models import Lead, LeadScore, Property, WebhookEvent
from src.schemas import GHLWebhookPayload
from src.webhooks import upsert_lead_from_payload


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


async def test_ghl_webhook_maps_provider_detail_fields_into_score(client):
    response = await client.post(
        "/webhooks/ghl",
        json={
            "id": "provider-lead-001",
            "source": "main-lead-provider",
            "customFields": [
                {"key": "First Name", "field_value": "Lynton"},
                {"key": "Last Name", "field_value": "Odom"},
                {"key": "Standard Seller Number", "field_value": "+18133106902"},
                {"key": "E-mail (entered by seller)", "field_value": "seller@example.com"},
                {"key": "Property Address", "field_value": "204 Carroll Dr, Warner Robins, GA 31093"},
                {"key": "City", "field_value": "warner robins"},
                {"key": "State", "field_value": "Georgia"},
                {"key": "Who's living in the property?", "field_value": "Vacant"},
                {"key": "Selling urgency", "field_value": "ASAP"},
                {"key": "Seller motivation", "field_value": "Inherited property"},
                {"key": "Seller: owner or agent?", "field_value": "Owner"},
                {"key": "Listing status", "field_value": "Not listed"},
                {"key": "APN", "field_value": "0W020L 062000"},
                {"key": "Repair scope", "field_value": "Major remodel: kitchen, bathroom, roof, etc."},
                {"key": "ZIP code", "field_value": "31093"},
                {"key": "Property type", "field_value": "Single family"},
                {"key": "Years of ownership", "field_value": "15-19 years"},
            ],
        },
    )

    assert response.status_code == 200

    async with get_session_factory()() as session:
        stored_lead = (await session.execute(select(Lead).where(Lead.ghl_id == "provider-lead-001"))).scalar_one_or_none()
        assert stored_lead is not None
        assert stored_lead.first_name == "Lynton"
        assert stored_lead.phone == "+18133106902"
        assert stored_lead.email == "seller@example.com"
        assert stored_lead.state == "GA"
        assert stored_lead.county == "Houston"

        prop = (await session.execute(select(Property).where(Property.lead_id == stored_lead.id))).scalar_one_or_none()
        assert prop is not None
        assert prop.county == "Houston"
        assert prop.county_resolution_method == "zip_crosswalk"
        assert prop.county_resolution_confidence == 70
        assert prop.occupancy == "Vacant"
        assert prop.selling_urgency == "ASAP"
        assert prop.seller_type == "Owner"
        assert prop.listing_status == "Not listed"
        assert prop.repair_scope.startswith("Major remodel")
        assert prop.property_type == "Single family"
        assert prop.years_owned == "15-19 years"

        score = (await session.execute(select(LeadScore).where(LeadScore.lead_id == stored_lead.id))).scalar_one_or_none()
        assert score is not None
        assert score.score >= 90
        assert "Urgency signal: ASAP" in score.reasons
        assert "Property is vacant" in score.reasons


async def test_ghl_webhook_maps_istl_export_columns(client):
    response = await client.post(
        "/webhooks/ghl",
        json={
            "id": "istl-export-001",
            "source": "ISTL Leads 2",
            "customFields": [
                {"key": "First Name", "field_value": "Sample"},
                {"key": "Last Name", "field_value": "Lead"},
                {"key": "Phone", "field_value": "+14045550123"},
                {"key": "Email", "field_value": "sample@example.com"},
                {"key": "Property Address", "field_value": "123 Main St, Lawrenceville, GA 30043"},
                {"key": "City", "field_value": "Lawrenceville"},
                {"key": "State", "field_value": "Georgia"},
                {"key": "County", "field_value": "Gwinnett"},
                {"key": "ZIP code", "field_value": "30043.0"},
                {"key": "Sold comps", "field_value": "288000.0"},
                {"key": "Seller motivation", "field_value": "Selling a vacant/non-occupied property"},
                {"key": "Type of Property", "field_value": "Single family"},
                {
                    "key": "What kind of repairs and maintenance does the property NEED?",
                    "field_value": "Remodel - Kitchen, Bathroom, Roof",
                },
                {"key": "How fast they want to sell", "field_value": "ASAP"},
                {"key": "How long have you owned the property in years?", "field_value": "20-29"},
                {"key": "Anyone living in the house?", "field_value": "No its Vacant"},
                {"key": "Owner or Agent/Wholesaler?", "field_value": "Yes, i own this property"},
                {"key": "Is your property listed with a real estate agent?", "field_value": "No it's not listed"},
            ],
        },
    )

    assert response.status_code == 200

    async with get_session_factory()() as session:
        stored_lead = (await session.execute(select(Lead).where(Lead.ghl_id == "istl-export-001"))).scalar_one()
        prop = (await session.execute(select(Property).where(Property.lead_id == stored_lead.id))).scalar_one()
        assert stored_lead.county == "Gwinnett"
        assert prop.zip == "30043"
        assert prop.estimated_value == 288000
        assert prop.situation == "Selling a vacant/non-occupied property"
        assert prop.property_type == "Single family"
        assert prop.repair_scope == "Remodel - Kitchen, Bathroom, Roof"
        assert prop.selling_urgency == "ASAP"
        assert prop.years_owned == "20-29"
        assert prop.occupancy == "No its Vacant"
        assert prop.seller_type == "Yes, i own this property"
        assert prop.listing_status == "No it's not listed"

        score = (await session.execute(select(LeadScore).where(LeadScore.lead_id == stored_lead.id))).scalar_one()
        assert score.score >= 90
        assert "Urgency signal: ASAP" in score.reasons


async def test_csv_backfill_event_logging_is_idempotent(client):
    payload = {
        "id": "csv-backfill-001",
        "source": "ISTL Leads 2",
        "customFields": [
            {"key": "First Name", "field_value": "Sample"},
            {"key": "Property Address", "field_value": "123 Main St, Lawrenceville, GA 30043"},
            {"key": "County", "field_value": "Gwinnett"},
        ],
    }

    async with get_session_factory()() as session:
        parsed = GHLWebhookPayload.model_validate(payload)
        await upsert_lead_from_payload(session, parsed, payload, provider="csv-backfill")
        await upsert_lead_from_payload(session, parsed, payload, provider="csv-backfill")
        await session.commit()

        events = (
            await session.execute(select(WebhookEvent).where(WebhookEvent.provider == "csv-backfill"))
        ).scalars().all()
        assert len(events) == 1


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
