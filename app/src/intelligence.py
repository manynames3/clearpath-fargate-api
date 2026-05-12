from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.auth import require_leads_api_key
from src.database import get_session
from src.models import DuplicateLead, Lead, LeadScore, LeadSource, MarketSnapshot, Property, WebhookEvent
from src.schemas import (
    BreakdownItem,
    CountyPerformanceItem,
    DuplicateLeadItem,
    IntelligenceSummary,
    LeadScoreItem,
    SourcePerformanceItem,
)

router = APIRouter(prefix="/intelligence", dependencies=[Depends(require_leads_api_key)])


def _lead_name(lead: Lead) -> str:
    name = " ".join(part for part in [lead.first_name, lead.last_name] if part)
    return name or lead.ghl_id


def _source_name(lead: Lead, source: LeadSource | None = None) -> str:
    return (source.name if source else lead.source) or "unknown"


def _round_average(values: list[int]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 1)


@router.get("/summary", response_model=IntelligenceSummary)
async def get_intelligence_summary(session: AsyncSession = Depends(get_session)):
    total_leads = await session.scalar(select(func.count(Lead.id)))
    total_sources = await session.scalar(select(func.count(LeadSource.id)))
    total_duplicates = await session.scalar(select(func.count(DuplicateLead.id)))
    needs_review_count = await session.scalar(select(func.count(LeadScore.id)).where(LeadScore.needs_review.is_(True)))
    average_score = await session.scalar(select(func.avg(LeadScore.score)))
    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent_webhook_events = await session.scalar(
        select(func.count(WebhookEvent.id)).where(WebhookEvent.received_at >= recent_cutoff)
    )

    status_rows = (
        await session.execute(select(Lead.status, func.count(Lead.id)).group_by(Lead.status).order_by(func.count(Lead.id).desc()))
    ).all()
    county_rows = (
        await session.execute(
            select(Lead.county, func.count(Lead.id))
            .where(Lead.county.is_not(None))
            .group_by(Lead.county)
            .order_by(func.count(Lead.id).desc())
            .limit(5)
        )
    ).all()

    return IntelligenceSummary(
        total_leads=total_leads or 0,
        total_sources=total_sources or 0,
        total_duplicates=total_duplicates or 0,
        needs_review_count=needs_review_count or 0,
        average_score=round(float(average_score), 1) if average_score is not None else None,
        status_counts=[BreakdownItem(label=status or "unknown", count=count) for status, count in status_rows],
        top_counties=[BreakdownItem(label=county or "unknown", count=count) for county, count in county_rows],
        recent_webhook_events=recent_webhook_events or 0,
    )


@router.get("/source-performance", response_model=list[SourcePerformanceItem])
async def get_source_performance(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(Lead, LeadScore, LeadSource)
            .outerjoin(LeadScore, LeadScore.lead_id == Lead.id)
            .outerjoin(LeadSource, LeadSource.id == Lead.source_id)
        )
    ).all()
    duplicate_rows = (await session.execute(select(DuplicateLead.lead_id))).scalars().all()
    duplicates_by_lead: dict[str, int] = defaultdict(int)
    for lead_id in duplicate_rows:
        duplicates_by_lead[lead_id] += 1

    groups: dict[str, dict] = {}
    for lead, score, source in rows:
        name = _source_name(lead, source)
        group = groups.setdefault(
            name,
            {
                "source": name,
                "vendor_name": source.vendor_name if source else None,
                "channel": source.channel if source else None,
                "cost_per_lead_cents": source.cost_per_lead_cents if source else None,
                "total_leads": 0,
                "hot_leads": 0,
                "warm_leads": 0,
                "closed_leads": 0,
                "dead_leads": 0,
                "duplicate_count": 0,
                "needs_review_count": 0,
                "scores": [],
            },
        )
        group["total_leads"] += 1
        group["hot_leads"] += 1 if lead.status == "hot" else 0
        group["warm_leads"] += 1 if lead.status == "warm" else 0
        group["closed_leads"] += 1 if lead.status == "closed" else 0
        group["dead_leads"] += 1 if lead.status == "dead" else 0
        group["duplicate_count"] += duplicates_by_lead.get(lead.id, 0)
        if score:
            group["scores"].append(score.score)
            group["needs_review_count"] += 1 if score.needs_review else 0

    items: list[SourcePerformanceItem] = []
    for group in groups.values():
        cost_per_lead_cents = group.pop("cost_per_lead_cents")
        estimated_spend = None
        if cost_per_lead_cents is not None:
            estimated_spend = round((cost_per_lead_cents * group["total_leads"]) / 100, 2)
        scores = group.pop("scores")
        items.append(
            SourcePerformanceItem(
                **group,
                average_score=_round_average(scores),
                estimated_spend_dollars=estimated_spend,
            )
        )

    return sorted(items, key=lambda item: (item.average_score or 0, item.total_leads), reverse=True)


@router.get("/duplicates", response_model=list[DuplicateLeadItem])
async def get_duplicate_leads(
    limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    duplicate_alias = aliased(Lead)
    rows = (
        await session.execute(
            select(DuplicateLead, Lead, duplicate_alias)
            .join(Lead, DuplicateLead.lead_id == Lead.id)
            .join(duplicate_alias, DuplicateLead.duplicate_lead_id == duplicate_alias.id)
            .order_by(DuplicateLead.created_at.desc())
            .limit(limit)
        )
    ).all()

    return [
        DuplicateLeadItem(
            id=duplicate.id,
            lead_id=lead.id,
            duplicate_lead_id=duplicate_lead.id,
            match_type=duplicate.match_type,
            confidence=duplicate.confidence,
            reason=duplicate.reason,
            lead_name=_lead_name(lead),
            duplicate_name=_lead_name(duplicate_lead),
            created_at=duplicate.created_at,
        )
        for duplicate, lead, duplicate_lead in rows
    ]


@router.get("/lead-scores", response_model=list[LeadScoreItem])
async def get_lead_scores(
    needs_review: bool | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Lead, LeadScore, Property)
        .join(LeadScore, LeadScore.lead_id == Lead.id)
        .outerjoin(Property, Property.lead_id == Lead.id)
        .order_by(LeadScore.score.desc(), Lead.updated_at.desc())
        .limit(limit)
    )
    if needs_review is not None:
        stmt = stmt.where(LeadScore.needs_review.is_(needs_review))

    rows = (await session.execute(stmt)).all()
    return [
        LeadScoreItem(
            lead_id=lead.id,
            lead_name=_lead_name(lead),
            source=lead.source,
            county=lead.county,
            status=lead.status,
            score=score.score,
            priority=score.priority,
            reasons=score.reasons or [],
            needs_review=score.needs_review,
            property_address=prop.address if prop else None,
            updated_at=score.updated_at,
        )
        for lead, score, prop in rows
    ]


@router.get("/county-performance", response_model=list[CountyPerformanceItem])
async def get_county_performance(session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(Lead, LeadScore)
            .outerjoin(LeadScore, LeadScore.lead_id == Lead.id)
            .where(Lead.county.is_not(None))
        )
    ).all()
    duplicate_rows = (await session.execute(select(DuplicateLead.lead_id))).scalars().all()
    duplicates_by_lead: dict[str, int] = defaultdict(int)
    for lead_id in duplicate_rows:
        duplicates_by_lead[lead_id] += 1

    snapshots = (
        await session.execute(
            select(MarketSnapshot).order_by(
                MarketSnapshot.county,
                MarketSnapshot.state,
                MarketSnapshot.snapshot_date.desc(),
            )
        )
    ).scalars()
    latest_market: dict[tuple[str, str], MarketSnapshot] = {}
    for snapshot in snapshots:
        latest_market.setdefault((snapshot.county.lower(), snapshot.state), snapshot)

    groups: dict[tuple[str, str], dict] = {}
    for lead, score in rows:
        key = ((lead.county or "unknown").lower(), lead.state)
        group = groups.setdefault(
            key,
            {
                "county": lead.county or "unknown",
                "state": lead.state,
                "total_leads": 0,
                "hot_leads": 0,
                "warm_leads": 0,
                "duplicate_count": 0,
                "needs_review_count": 0,
                "scores": [],
            },
        )
        group["total_leads"] += 1
        group["hot_leads"] += 1 if lead.status == "hot" else 0
        group["warm_leads"] += 1 if lead.status == "warm" else 0
        group["duplicate_count"] += duplicates_by_lead.get(lead.id, 0)
        if score:
            group["scores"].append(score.score)
            group["needs_review_count"] += 1 if score.needs_review else 0

    items: list[CountyPerformanceItem] = []
    for key, group in groups.items():
        scores = group.pop("scores")
        snapshot = latest_market.get(key)
        items.append(
            CountyPerformanceItem(
                **group,
                average_score=_round_average(scores),
                median_price=snapshot.median_price if snapshot else None,
                avg_dom=snapshot.avg_dom if snapshot else None,
            )
        )

    return sorted(items, key=lambda item: (item.average_score or 0, item.total_leads), reverse=True)
