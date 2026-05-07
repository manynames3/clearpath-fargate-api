from datetime import date

from src.database import get_session_factory
from src.models import MarketSnapshot


async def test_market_snapshot_sets_cache_header(client):
    async with get_session_factory()() as session:
        session.add(
            MarketSnapshot(
                county="Gwinnett",
                state="GA",
                median_price=385000,
                avg_dom=21,
                snapshot_date=date(2026, 5, 6),
            )
        )
        await session.commit()

    response = await client.get("/api/market/gwinnett")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert response.json()["median_price"] == 385000
