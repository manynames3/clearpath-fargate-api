from datetime import date

from src.config import get_settings
from src.database import get_session_factory
from src.models import DuplicateLead, Lead, LeadScore, LeadSource, MarketSnapshot, Property, WebhookEvent


async def _seed_intelligence_data():
    async with get_session_factory()() as session:
        vendor = LeadSource(
            name="paid-lead-vendor-a",
            vendor_name="Vendor A",
            channel="paid-lead-provider",
            cost_per_lead_cents=8500,
        )
        facebook = LeadSource(name="facebook", vendor_name="Meta", channel="paid-social", cost_per_lead_cents=4200)
        session.add_all([vendor, facebook])
        await session.flush()

        lead = Lead(
            ghl_id="intel-001",
            source_id=vendor.id,
            first_name="Maya",
            last_name="Johnson",
            phone="+14045550101",
            status="hot",
            source=vendor.name,
            county="Gwinnett",
            state="GA",
        )
        duplicate = Lead(
            ghl_id="intel-002",
            source_id=vendor.id,
            first_name="Maya",
            last_name="J.",
            phone="+14045550101",
            status="warm",
            source=vendor.name,
            county="Gwinnett",
            state="GA",
        )
        other = Lead(
            ghl_id="intel-003",
            source_id=facebook.id,
            first_name="Elliot",
            last_name="Reed",
            status="dead",
            source=facebook.name,
            county="Cobb",
            state="GA",
        )
        session.add_all([lead, duplicate, other])
        await session.flush()

        session.add_all(
            [
                Property(lead_id=lead.id, address="123 Mill Creek Rd", county="Gwinnett", state="GA", situation="inherited"),
                Property(
                    lead_id=duplicate.id,
                    address="123 Mill Creek Rd",
                    county="Gwinnett",
                    state="GA",
                    situation="inherited",
                ),
                LeadScore(
                    lead_id=lead.id,
                    score=84,
                    priority="high",
                    reasons=["Status is hot", "Property address present"],
                    needs_review=True,
                ),
                LeadScore(
                    lead_id=duplicate.id,
                    score=61,
                    priority="review",
                    reasons=["Possible duplicate lead"],
                    needs_review=True,
                ),
                LeadScore(
                    lead_id=other.id,
                    score=30,
                    priority="low",
                    reasons=["Status is dead"],
                    needs_review=False,
                ),
                DuplicateLead(
                    lead_id=duplicate.id,
                    duplicate_lead_id=lead.id,
                    match_type="phone",
                    confidence=95,
                    reason="Phone number matches an existing lead",
                ),
                WebhookEvent(
                    provider="gohighlevel",
                    external_id=lead.ghl_id,
                    lead_id=lead.id,
                    event_type="contact",
                    payload={"contact_id": lead.ghl_id},
                ),
                MarketSnapshot(
                    county="Gwinnett",
                    state="GA",
                    median_price=385000,
                    avg_dom=21,
                    snapshot_date=date.today(),
                ),
            ]
        )
        await session.commit()


async def test_intelligence_summary_and_breakdowns(client):
    await _seed_intelligence_data()

    response = await client.get("/api/intelligence/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_leads"] == 3
    assert body["total_sources"] == 2
    assert body["total_duplicates"] == 1
    assert body["needs_review_count"] == 2
    assert {"label": "Gwinnett", "count": 2} in body["top_counties"]


async def test_source_performance_exposes_vendor_scorecard(client):
    await _seed_intelligence_data()

    response = await client.get("/api/intelligence/source-performance")

    assert response.status_code == 200
    vendor = next(item for item in response.json() if item["source"] == "paid-lead-vendor-a")
    assert vendor["vendor_name"] == "Vendor A"
    assert vendor["total_leads"] == 2
    assert vendor["duplicate_count"] == 1
    assert vendor["estimated_spend_dollars"] == 170.0


async def test_duplicate_leads_endpoint_returns_matches(client):
    await _seed_intelligence_data()

    response = await client.get("/api/intelligence/duplicates")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["match_type"] == "phone"
    assert body[0]["confidence"] == 95


async def test_lead_scores_endpoint_returns_review_queue(client):
    await _seed_intelligence_data()

    response = await client.get("/api/intelligence/lead-scores", params={"needs_review": "true"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["score"] == 84
    assert body[1]["priority"] == "review"


async def test_county_performance_includes_market_context(client):
    await _seed_intelligence_data()

    response = await client.get("/api/intelligence/county-performance")

    assert response.status_code == 200
    gwinnett = next(item for item in response.json() if item["county"] == "Gwinnett")
    assert gwinnett["total_leads"] == 2
    assert gwinnett["duplicate_count"] == 1
    assert gwinnett["median_price"] == 385000


async def test_intelligence_endpoints_require_api_key_when_configured(client, monkeypatch):
    monkeypatch.setenv("CLEARPATH_API_KEY_SECRET", "lead-api-key")
    get_settings.cache_clear()

    response = await client.get("/api/intelligence/summary")

    assert response.status_code == 401
