from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session
from src.models import MarketSnapshot
from src.schemas import MarketSnapshotResponse

router = APIRouter()


@router.get("/market/{county}", response_model=MarketSnapshotResponse)
async def get_market_snapshot(
    county: str,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(MarketSnapshot)
        .where(func.lower(MarketSnapshot.county) == county.lower(), MarketSnapshot.state == "GA")
        .order_by(MarketSnapshot.snapshot_date.desc())
        .limit(1)
    )
    snapshot = (await session.execute(stmt)).scalar_one_or_none()
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Market snapshot not found")

    response.headers["Cache-Control"] = "public, max-age=3600"
    return MarketSnapshotResponse.model_validate(snapshot)
