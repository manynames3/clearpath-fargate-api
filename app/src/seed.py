import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete

from src.database import get_engine, get_session_factory
from src.models import Base, DuplicateLead, FollowUp, Lead, LeadScore, LeadSource, MarketSnapshot, Property, WebhookEvent


async def seed_sample_data() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_session_factory()() as session:
        await session.execute(delete(DuplicateLead))
        await session.execute(delete(LeadScore))
        await session.execute(delete(WebhookEvent))
        await session.execute(delete(FollowUp))
        await session.execute(delete(Property))
        await session.execute(delete(Lead))
        await session.execute(delete(LeadSource))
        await session.execute(delete(MarketSnapshot))

        now = datetime.now(timezone.utc)
        sources = [
            LeadSource(name="paid-lead-vendor-a", vendor_name="Vendor A", channel="paid-lead-provider", cost_per_lead_cents=8500),
            LeadSource(name="facebook", vendor_name="Meta", channel="paid-social", cost_per_lead_cents=4200),
            LeadSource(name="direct", vendor_name="Direct", channel="organic", cost_per_lead_cents=0),
        ]
        session.add_all(sources)
        await session.flush()
        source_by_name = {source.name: source for source in sources}

        leads = [
            Lead(
                ghl_id="sample-gwinnett-hot",
                source_id=source_by_name["paid-lead-vendor-a"].id,
                first_name="Maya",
                last_name="Johnson",
                phone="+14045550101",
                email="maya@example.com",
                status="hot",
                source="paid-lead-vendor-a",
                county="Gwinnett",
                state="GA",
            ),
            Lead(
                ghl_id="sample-cobb-warm",
                source_id=source_by_name["facebook"].id,
                first_name="Elliot",
                last_name="Reed",
                phone="+17705550102",
                email="elliot@example.com",
                status="warm",
                source="facebook",
                county="Cobb",
                state="GA",
            ),
            Lead(
                ghl_id="sample-fulton-new",
                source_id=source_by_name["direct"].id,
                first_name="Tanya",
                last_name="Miles",
                phone="+16785550103",
                email="tanya@example.com",
                status="new",
                source="direct",
                county="Fulton",
                state="GA",
            ),
            Lead(
                ghl_id="sample-gwinnett-review",
                source_id=source_by_name["paid-lead-vendor-a"].id,
                first_name="Caleb",
                last_name="Ward",
                phone="+14045550104",
                email="caleb@example.com",
                status="warm",
                source="paid-lead-vendor-a",
                county="Gwinnett",
                state="GA",
            ),
        ]
        session.add_all(leads)
        await session.flush()

        session.add_all(
            [
                Property(
                    lead_id=leads[0].id,
                    address="123 Mill Creek Rd",
                    city="Lawrenceville",
                    county="Gwinnett",
                    state="GA",
                    zip="30043",
                    estimated_value=385000,
                    situation="inherited",
                ),
                Property(
                    lead_id=leads[1].id,
                    address="88 Powder Springs St",
                    city="Marietta",
                    county="Cobb",
                    state="GA",
                    zip="30064",
                    estimated_value=420000,
                    situation="vacant",
                ),
                Property(
                    lead_id=leads[2].id,
                    address="411 Cascade Ave",
                    city="Atlanta",
                    county="Fulton",
                    state="GA",
                    zip="30310",
                    estimated_value=310000,
                    situation="tax-delinquent",
                ),
                Property(
                    lead_id=leads[3].id,
                    address="77 Beaver Ruin Rd",
                    city="Norcross",
                    county="Gwinnett",
                    state="GA",
                    zip="30071",
                    estimated_value=305000,
                    situation="deferred-maintenance",
                ),
                FollowUp(
                    lead_id=leads[0].id,
                    contacted_at=now - timedelta(days=4),
                    method="call",
                    notes="Seller asked for a cash offer this week.",
                    next_follow_up=date.today() + timedelta(days=1),
                ),
                FollowUp(
                    lead_id=leads[1].id,
                    contacted_at=now - timedelta(days=35),
                    method="sms",
                    notes="Needs to coordinate with sibling co-owner.",
                    next_follow_up=date.today() + timedelta(days=3),
                ),
                LeadScore(
                    lead_id=leads[0].id,
                    score=84,
                    priority="high",
                    reasons=["Status is hot", "Property address present", "Motivation signal: inherited"],
                    needs_review=True,
                ),
                LeadScore(
                    lead_id=leads[1].id,
                    score=68,
                    priority="medium",
                    reasons=["Status is warm", "Property address present", "County captured: Cobb"],
                    needs_review=False,
                ),
                LeadScore(
                    lead_id=leads[2].id,
                    score=72,
                    priority="medium",
                    reasons=["Status is new", "Motivation signal: tax-delinquent", "County captured: Fulton"],
                    needs_review=True,
                ),
                LeadScore(
                    lead_id=leads[3].id,
                    score=66,
                    priority="review",
                    reasons=["Status is warm", "Provider quality needs review", "Property address present"],
                    needs_review=True,
                ),
                WebhookEvent(
                    provider="gohighlevel",
                    external_id=leads[0].ghl_id,
                    lead_id=leads[0].id,
                    event_type="contact",
                    payload={"contact_id": leads[0].ghl_id, "source": leads[0].source},
                ),
                MarketSnapshot(
                    county="Gwinnett",
                    state="GA",
                    median_price=385000,
                    avg_dom=21,
                    snapshot_date=date.today(),
                ),
                MarketSnapshot(
                    county="Cobb",
                    state="GA",
                    median_price=420000,
                    avg_dom=18,
                    snapshot_date=date.today(),
                ),
                MarketSnapshot(
                    county="Fulton",
                    state="GA",
                    median_price=395000,
                    avg_dom=24,
                    snapshot_date=date.today(),
                ),
            ]
        )
        await session.commit()

    print("Seeded 4 sample leads, source metadata, scores, and 3 market snapshots.")


if __name__ == "__main__":
    asyncio.run(seed_sample_data())
