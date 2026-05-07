import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete

from src.database import get_engine, get_session_factory
from src.models import Base, FollowUp, Lead, MarketSnapshot, Property


async def seed_sample_data() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_session_factory()() as session:
        await session.execute(delete(FollowUp))
        await session.execute(delete(Property))
        await session.execute(delete(Lead))
        await session.execute(delete(MarketSnapshot))

        now = datetime.now(timezone.utc)
        leads = [
            Lead(
                ghl_id="sample-gwinnett-hot",
                first_name="Maya",
                last_name="Johnson",
                phone="+14045550101",
                email="maya@example.com",
                status="hot",
                source="sms",
                county="Gwinnett",
                state="GA",
            ),
            Lead(
                ghl_id="sample-cobb-warm",
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
                first_name="Tanya",
                last_name="Miles",
                phone="+16785550103",
                email="tanya@example.com",
                status="new",
                source="direct",
                county="Fulton",
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

    print("Seeded 3 sample leads and 3 market snapshots.")


if __name__ == "__main__":
    asyncio.run(seed_sample_data())
