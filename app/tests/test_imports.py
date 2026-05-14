import textwrap

from sqlalchemy import func, select

from src.config import get_settings
from src.database import get_session_factory
from src.models import Lead, WebhookEvent


CSV_PAYLOAD = textwrap.dedent(
    """\
    First Name,Last Name,Phone,Email,Property Address,City,State,ZIP code,Seller motivation,Selling urgency,Status
    Lynton,Odom,+18133106902,lynton@example.com,"204 Carroll Dr, Warner Robins, GA 31093",Warner Robins,Georgia,31093,Inherited property,ASAP,appointment
    Ava,Stone,+14045550188,ava@example.com,"123 Main St, Lawrenceville, GA 30043",Lawrenceville,Georgia,30043,Vacant property,30 days,new
    """
)


async def test_csv_import_backfills_leads_into_same_analytics_layer(client):
    response = await client.post(
        "/api/imports/leads/csv",
        params={"source": "ISTL Leads 2", "cost_per_lead_dollars": 55},
        content=CSV_PAYLOAD,
        headers={"Content-Type": "text/csv"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "csv-backfill"
    assert body["rows_received"] == 2
    assert body["imported"] == 2
    assert body["failed"] == 0

    leads = await client.get("/api/analytics/leads", params={"source": "ISTL Leads 2", "sort": "source"})
    assert leads.status_code == 200
    leads_body = leads.json()
    assert leads_body["count"] == 2
    assert {lead["lead_name"] for lead in leads_body["leads"]} == {"Lynton Odom", "Ava Stone"}
    assert next(lead for lead in leads_body["leads"] if lead["lead_name"] == "Lynton Odom")["county"] == "Houston"

    roi = await client.get("/api/analytics/source-roi")
    source = next(item for item in roi.json() if item["source"] == "ISTL Leads 2")
    assert source["total_leads"] == 2
    assert source["cost_per_lead_dollars"] == 55.0
    assert source["estimated_spend_dollars"] == 110.0
    assert source["appointment_count"] == 1


async def test_csv_import_is_idempotent_for_generated_row_identity(client):
    for _ in range(2):
        response = await client.post(
            "/api/imports/leads/csv",
            params={"source": "ISTL Leads 2"},
            content=CSV_PAYLOAD,
            headers={"Content-Type": "text/csv"},
        )
        assert response.status_code == 200

    async with get_session_factory()() as session:
        lead_count = await session.scalar(select(func.count()).select_from(Lead).where(Lead.source == "ISTL Leads 2"))
        event_count = await session.scalar(
            select(func.count()).select_from(WebhookEvent).where(WebhookEvent.provider == "csv-backfill")
        )

    assert lead_count == 2
    assert event_count == 2


async def test_csv_import_supports_dry_run(client):
    response = await client.post(
        "/api/imports/leads/csv",
        params={"source": "Dry Run Provider", "dry_run": "true"},
        content=CSV_PAYLOAD,
        headers={"Content-Type": "text/csv"},
    )

    assert response.status_code == 200
    assert response.json()["imported"] == 2

    leads = await client.get("/api/analytics/leads", params={"source": "Dry Run Provider"})
    assert leads.json()["count"] == 0


async def test_csv_import_requires_api_key_when_configured(client, monkeypatch):
    monkeypatch.setenv("CLEARPATH_API_KEY_SECRET", "lead-api-key")
    get_settings.cache_clear()

    response = await client.post(
        "/api/imports/leads/csv",
        content=CSV_PAYLOAD,
        headers={"Content-Type": "text/csv"},
    )

    assert response.status_code == 401
