from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import require_leads_api_key
from src.database import get_session
from src.models import FollowUp, Lead, Property
from src.schemas import LeadResponse, LeadsPage, PropertyResponse

router = APIRouter()


@router.get("/leads", response_model=LeadsPage)
async def list_leads(
    county: str | None = None,
    status: str | None = None,
    days_since_contact: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    _api_key: None = Depends(require_leads_api_key),
    session: AsyncSession = Depends(get_session),
):
    last_contacted_at = (
        select(func.max(FollowUp.contacted_at))
        .where(FollowUp.lead_id == Lead.id)
        .correlate(Lead)
        .scalar_subquery()
    )
    next_follow_up = (
        select(FollowUp.next_follow_up)
        .where(FollowUp.lead_id == Lead.id)
        .order_by(FollowUp.contacted_at.desc())
        .limit(1)
        .correlate(Lead)
        .scalar_subquery()
    )

    stmt = (
        select(Lead, Property, last_contacted_at.label("last_contacted_at"), next_follow_up.label("next_follow_up"))
        .outerjoin(Property, Property.lead_id == Lead.id)
        .order_by(Lead.created_at.desc())
        .limit(limit)
    )

    if county:
        stmt = stmt.where(func.lower(Lead.county) == county.lower())
    if status:
        stmt = stmt.where(Lead.status == status)
    if days_since_contact is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_since_contact)
        stmt = stmt.where(or_(last_contacted_at.is_(None), last_contacted_at < cutoff))

    rows = (await session.execute(stmt)).all()
    leads = [
        LeadResponse(
            id=lead.id,
            ghl_id=lead.ghl_id,
            first_name=lead.first_name,
            last_name=lead.last_name,
            status=lead.status,
            source=lead.source,
            county=lead.county,
            state=lead.state,
            property=PropertyResponse.model_validate(prop) if prop else None,
            last_contacted_at=contacted_at,
            next_follow_up=follow_up_date,
        )
        for lead, prop, contacted_at, follow_up_date in rows
    ]
    return LeadsPage(count=len(leads), limit=limit, leads=leads)
