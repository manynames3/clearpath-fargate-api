from datetime import datetime, timedelta, timezone

from src.config import get_settings
from src.database import get_session_factory
from src.models import Lead, LeadOutcome, LeadSource, Property


async def _seed_paid_lead_analytics_data():
    async with get_session_factory()() as session:
        provider_a = LeadSource(
            name="provider-a",
            vendor_name="Provider A",
            channel="paid-lead-provider",
            cost_per_lead_cents=10000,
        )
        provider_b = LeadSource(
            name="provider-b",
            vendor_name="Provider B",
            channel="paid-lead-provider",
            cost_per_lead_cents=5000,
        )
        session.add_all([provider_a, provider_b])
        await session.flush()

        closed = Lead(
            ghl_id="analytics-closed",
            source_id=provider_a.id,
            first_name="Maya",
            last_name="Johnson",
            status="closed",
            source=provider_a.name,
            county="Gwinnett",
            state="GA",
        )
        dead = Lead(
            ghl_id="analytics-dead",
            source_id=provider_a.id,
            first_name="Caleb",
            last_name="Ward",
            status="dead",
            source=provider_a.name,
            county="Gwinnett",
            state="GA",
        )
        appointment = Lead(
            ghl_id="analytics-appointment",
            source_id=provider_b.id,
            first_name="Elliot",
            last_name="Reed",
            status="appointment",
            source=provider_b.name,
            county="Cobb",
            state="GA",
        )
        stale = Lead(
            ghl_id="analytics-stale",
            source_id=provider_b.id,
            first_name="Tanya",
            last_name="Miles",
            status="new",
            source=provider_b.name,
            county="Fulton",
            state="GA",
        )
        session.add_all([closed, dead, appointment, stale])
        await session.flush()

        now = datetime.now(timezone.utc)
        session.add_all(
            [
                Property(
                    lead_id=closed.id,
                    address="123 Mill Creek Rd",
                    city="Lawrenceville",
                    county="Gwinnett",
                    state="GA",
                    situation="inherited",
                    selling_urgency="ASAP",
                    listing_status="Not listed",
                ),
                Property(lead_id=appointment.id, address="88 Powder Springs St", county="Cobb", state="GA"),
                Property(lead_id=stale.id, address="411 Cascade Ave", county="Fulton", state="GA"),
                LeadOutcome(lead_id=closed.id, stage="received", occurred_at=now - timedelta(days=30)),
                LeadOutcome(lead_id=closed.id, stage="contacted", occurred_at=now - timedelta(days=29)),
                LeadOutcome(lead_id=closed.id, stage="appointment", occurred_at=now - timedelta(days=25)),
                LeadOutcome(lead_id=closed.id, stage="offer", occurred_at=now - timedelta(days=20)),
                LeadOutcome(lead_id=closed.id, stage="contract", occurred_at=now - timedelta(days=10)),
                LeadOutcome(lead_id=closed.id, stage="closed", occurred_at=now - timedelta(days=2)),
                LeadOutcome(lead_id=dead.id, stage="received", occurred_at=now - timedelta(days=20)),
                LeadOutcome(lead_id=dead.id, stage="contacted", occurred_at=now - timedelta(days=19)),
                LeadOutcome(lead_id=dead.id, stage="dead", dead_reason="Retail price expectation", occurred_at=now - timedelta(days=15)),
                LeadOutcome(lead_id=appointment.id, stage="received", occurred_at=now - timedelta(days=12)),
                LeadOutcome(lead_id=appointment.id, stage="contacted", occurred_at=now - timedelta(days=10)),
                LeadOutcome(lead_id=appointment.id, stage="appointment", occurred_at=now - timedelta(days=8)),
                LeadOutcome(lead_id=stale.id, stage="received", occurred_at=now - timedelta(days=14)),
            ]
        )
        await session.commit()
        return stale.id


async def test_source_roi_calculates_paid_lead_performance(client):
    await _seed_paid_lead_analytics_data()

    response = await client.get("/api/analytics/source-roi")

    assert response.status_code == 200
    body = response.json()
    provider_a = next(item for item in body if item["source"] == "provider-a")
    assert provider_a["total_leads"] == 2
    assert provider_a["estimated_spend_dollars"] == 200.0
    assert provider_a["contacted_count"] == 2
    assert provider_a["closed_count"] == 1
    assert provider_a["close_rate"] == 50.0
    assert provider_a["cost_per_close_dollars"] == 200.0


async def test_funnel_and_stale_leads_expose_operational_followup(client):
    await _seed_paid_lead_analytics_data()

    funnel = await client.get("/api/analytics/funnel")
    stale = await client.get("/api/analytics/stale-leads", params={"days": 7})

    assert funnel.status_code == 200
    stages = {item["stage"]: item["count"] for item in funnel.json()["stages"]}
    assert stages["received"] == 4
    assert stages["contacted"] == 3
    assert stages["appointment"] == 2
    assert stages["closed"] == 1
    assert stages["dead"] == 1

    assert stale.status_code == 200
    stale_ids = {item["lead_name"] for item in stale.json()}
    assert "Tanya Miles" in stale_ids


async def test_analytics_leads_filters_by_provider_fields(client):
    await _seed_paid_lead_analytics_data()

    response = await client.get(
        "/api/analytics/leads",
        params={"source": "provider-a", "motivation": "inherited", "sort": "source"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["leads"][0]["lead_name"] == "Maya Johnson"
    assert body["leads"][0]["motivation"] == "inherited"


async def test_patch_outcome_updates_lead_lifecycle(client):
    lead_id = await _seed_paid_lead_analytics_data()

    response = await client.patch(
        f"/api/leads/{lead_id}/outcome",
        json={"stage": "contacted", "notes": "Reached seller by phone"},
    )

    assert response.status_code == 200
    assert response.json()["stage"] == "contacted"
    assert response.json()["status"] == "contacted"

    stale = await client.get("/api/analytics/stale-leads", params={"days": 7})
    assert "Tanya Miles" not in {item["lead_name"] for item in stale.json()}


async def test_source_cost_update_sets_roi_input(client):
    await _seed_paid_lead_analytics_data()

    response = await client.patch(
        "/api/analytics/sources/provider-b/cost",
        json={"cost_per_lead_dollars": 75, "vendor_name": "Updated Provider B"},
    )

    assert response.status_code == 200
    assert response.json()["cost_per_lead_dollars"] == 75.0

    roi = await client.get("/api/analytics/source-roi")
    provider_b = next(item for item in roi.json() if item["source"] == "provider-b")
    assert provider_b["estimated_spend_dollars"] == 150.0


async def test_analytics_endpoints_require_api_key_when_configured(client, monkeypatch):
    monkeypatch.setenv("CLEARPATH_API_KEY_SECRET", "lead-api-key")
    get_settings.cache_clear()

    response = await client.get("/api/analytics/source-roi")

    assert response.status_code == 401
