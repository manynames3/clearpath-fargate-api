from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import require_leads_api_key
from src.database import get_session
from src.models import FollowUp, Lead, LeadOutcome, LeadScore, LeadSource, Property
from src.schemas import (
    AnalyticsLeadItem,
    AnalyticsLeadsPage,
    FunnelResponse,
    FunnelStageItem,
    OutcomeResponse,
    OutcomeUpdateRequest,
    SourceCostResponse,
    SourceCostUpdateRequest,
    SourceRoiItem,
    StaleLeadItem,
)

router = APIRouter(dependencies=[Depends(require_leads_api_key)])

ACTIVE_STAGES = ("received", "contacted", "appointment", "offer", "contract", "closed")
TERMINAL_STAGES = {"closed", "dead"}
STAGE_INDEX = {stage: index for index, stage in enumerate(ACTIVE_STAGES)}
STAGE_ALIASES = {
    "new": "received",
    "contact": "contacted",
    "called": "contacted",
    "sms": "contacted",
    "appointment_set": "appointment",
    "appt": "appointment",
    "offer_made": "offer",
    "under_contract": "contract",
    "contracted": "contract",
    "closed_won": "closed",
    "lost": "dead",
}
SORT_FIELDS = {"created_at", "updated_at", "score", "source", "status", "motivation", "lifecycle_stage"}


def _lead_name(lead: Lead) -> str:
    name = " ".join(part for part in [lead.first_name, lead.last_name] if part)
    return name or lead.ghl_id


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _date_floor(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _date_ceiling(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


def normalize_lifecycle_stage(stage: str) -> str:
    normalized = stage.lower().strip().replace(" ", "_").replace("-", "_")
    normalized = STAGE_ALIASES.get(normalized, normalized)
    if normalized not in {*ACTIVE_STAGES, "dead"}:
        allowed = ", ".join([*ACTIVE_STAGES, "dead"])
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported lifecycle stage '{stage}'. Use one of: {allowed}",
        )
    return normalized


def _stage_set(lead: Lead, outcomes: list[LeadOutcome]) -> set[str]:
    stages = {normalize_lifecycle_stage(outcome.stage) for outcome in outcomes if outcome.stage}
    try:
        stages.add(normalize_lifecycle_stage(lead.status or "received"))
    except HTTPException:
        pass
    stages.add("received")
    return stages


def _latest_outcome(outcomes: list[LeadOutcome]) -> LeadOutcome | None:
    if not outcomes:
        return None
    return max(outcomes, key=lambda outcome: _as_utc(outcome.occurred_at) or datetime.min.replace(tzinfo=timezone.utc))


def _lifecycle_stage(lead: Lead, outcomes: list[LeadOutcome]) -> str:
    latest = _latest_outcome(outcomes)
    if latest:
        return normalize_lifecycle_stage(latest.stage)
    try:
        return normalize_lifecycle_stage(lead.status or "received")
    except HTTPException:
        return "received"


def _reached(stages: set[str], target: str) -> bool:
    if target == "dead":
        return "dead" in stages
    target_index = STAGE_INDEX[target]
    max_index = max((STAGE_INDEX[stage] for stage in stages if stage in STAGE_INDEX), default=0)
    return max_index >= target_index


def _dollars(cents: int | None) -> float | None:
    return round(cents / 100, 2) if cents is not None else None


def _rate(count: int, total: int) -> float | None:
    return round((count / total) * 100, 1) if total else None


def _cost(spend: float | None, count: int) -> float | None:
    return round(spend / count, 2) if spend is not None and count else None


async def _outcomes_by_lead(session: AsyncSession, lead_ids: list[str]) -> dict[str, list[LeadOutcome]]:
    if not lead_ids:
        return {}
    rows = (
        await session.execute(
            select(LeadOutcome)
            .where(LeadOutcome.lead_id.in_(lead_ids))
            .order_by(LeadOutcome.lead_id, LeadOutcome.occurred_at)
        )
    ).scalars()
    grouped: dict[str, list[LeadOutcome]] = defaultdict(list)
    for outcome in rows:
        grouped[outcome.lead_id].append(outcome)
    return grouped


async def _followup_activity_by_lead(session: AsyncSession, lead_ids: list[str]) -> dict[str, datetime]:
    if not lead_ids:
        return {}
    rows = (
        await session.execute(
            select(FollowUp.lead_id, func.max(FollowUp.contacted_at))
            .where(FollowUp.lead_id.in_(lead_ids))
            .group_by(FollowUp.lead_id)
        )
    ).all()
    return {lead_id: contacted_at for lead_id, contacted_at in rows if contacted_at}


def _matches_text(value: str | None, needle: str | None) -> bool:
    if not needle:
        return True
    return needle.lower() in (value or "").lower()


async def _lead_rows(
    session: AsyncSession,
    *,
    source: str | None = None,
    status_filter: str | None = None,
    county: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    stmt = (
        select(Lead, Property, LeadScore, LeadSource)
        .outerjoin(Property, Property.lead_id == Lead.id)
        .outerjoin(LeadScore, LeadScore.lead_id == Lead.id)
        .outerjoin(LeadSource, LeadSource.id == Lead.source_id)
    )
    start = _date_floor(date_from)
    end = _date_ceiling(date_to)
    if source:
        stmt = stmt.where(func.lower(Lead.source) == source.lower())
    if status_filter:
        stmt = stmt.where(func.lower(Lead.status) == status_filter.lower())
    if county:
        stmt = stmt.where(func.lower(Lead.county) == county.lower())
    if start:
        stmt = stmt.where(Lead.created_at >= start)
    if end:
        stmt = stmt.where(Lead.created_at <= end)

    return (await session.execute(stmt)).all()


def _analytics_item(lead: Lead, prop: Property | None, score: LeadScore | None, source: LeadSource | None, outcomes: list[LeadOutcome]):
    latest = _latest_outcome(outcomes)
    return AnalyticsLeadItem(
        id=lead.id,
        ghl_id=lead.ghl_id,
        lead_name=_lead_name(lead),
        source=lead.source,
        vendor_name=source.vendor_name if source else None,
        status=lead.status,
        lifecycle_stage=_lifecycle_stage(lead, outcomes),
        score=score.score if score else None,
        priority=score.priority if score else None,
        county=lead.county,
        state=lead.state,
        city=prop.city if prop else None,
        zip=prop.zip if prop else None,
        property_address=prop.address if prop else None,
        motivation=prop.situation if prop else None,
        urgency=prop.selling_urgency if prop else None,
        occupancy=prop.occupancy if prop else None,
        listing_status=prop.listing_status if prop else None,
        repair_scope=prop.repair_scope if prop else None,
        last_outcome_at=latest.occurred_at if latest else None,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


@router.get("/analytics/leads", response_model=AnalyticsLeadsPage)
async def get_analytics_leads(
    source: str | None = None,
    status: str | None = None,
    county: str | None = None,
    lifecycle_stage: str | None = None,
    motivation: str | None = None,
    urgency: str | None = None,
    listing_status: str | None = None,
    sort: str = Query(default="created_at"),
    direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    if sort not in SORT_FIELDS:
        raise HTTPException(status_code=422, detail=f"Unsupported sort field '{sort}'")
    normalized_stage = normalize_lifecycle_stage(lifecycle_stage) if lifecycle_stage else None

    rows = await _lead_rows(
        session,
        source=source,
        status_filter=status,
        county=county,
        date_from=date_from,
        date_to=date_to,
    )
    lead_ids = [lead.id for lead, *_ in rows]
    outcomes = await _outcomes_by_lead(session, lead_ids)
    items = [
        _analytics_item(lead, prop, score, source_meta, outcomes.get(lead.id, []))
        for lead, prop, score, source_meta in rows
    ]
    items = [
        item
        for item in items
        if (normalized_stage is None or item.lifecycle_stage == normalized_stage)
        and _matches_text(item.motivation, motivation)
        and _matches_text(item.urgency, urgency)
        and _matches_text(item.listing_status, listing_status)
    ]

    def sort_key(item: AnalyticsLeadItem):
        values = {
            "created_at": _as_utc(item.created_at) or datetime.min.replace(tzinfo=timezone.utc),
            "updated_at": _as_utc(item.updated_at) or datetime.min.replace(tzinfo=timezone.utc),
            "score": item.score or 0,
            "source": item.source or "",
            "status": item.status or "",
            "motivation": item.motivation or "",
            "lifecycle_stage": item.lifecycle_stage,
        }
        return values[sort]

    items = sorted(items, key=sort_key, reverse=direction == "desc")
    return AnalyticsLeadsPage(count=len(items), limit=limit, leads=items[:limit])


@router.get("/analytics/funnel", response_model=FunnelResponse)
async def get_funnel(
    source: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_session),
):
    rows = await _lead_rows(session, source=source, date_from=date_from, date_to=date_to)
    lead_ids = [lead.id for lead, *_ in rows]
    outcomes = await _outcomes_by_lead(session, lead_ids)

    counts = {stage: 0 for stage in ACTIVE_STAGES}
    counts["dead"] = 0
    for lead, *_ in rows:
        stages = _stage_set(lead, outcomes.get(lead.id, []))
        for stage in ACTIVE_STAGES:
            counts[stage] += 1 if _reached(stages, stage) else 0
        counts["dead"] += 1 if _reached(stages, "dead") else 0

    total = len(rows)
    return FunnelResponse(
        total_leads=total,
        stages=[FunnelStageItem(stage=stage, count=counts[stage], conversion_rate=_rate(counts[stage], total)) for stage in [*ACTIVE_STAGES, "dead"]],
    )


@router.get("/analytics/source-roi", response_model=list[SourceRoiItem])
async def get_source_roi(
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_session),
):
    rows = await _lead_rows(session, date_from=date_from, date_to=date_to)
    lead_ids = [lead.id for lead, *_ in rows]
    outcomes = await _outcomes_by_lead(session, lead_ids)

    groups: dict[str, dict] = {}
    for lead, _prop, _score, source_meta in rows:
        source_name = lead.source or (source_meta.name if source_meta else None) or "unknown"
        group = groups.setdefault(
            source_name,
            {
                "source": source_name,
                "vendor_name": source_meta.vendor_name if source_meta else None,
                "channel": source_meta.channel if source_meta else None,
                "cost_per_lead_cents": source_meta.cost_per_lead_cents if source_meta else None,
                "total_leads": 0,
                "contacted_count": 0,
                "appointment_count": 0,
                "offer_count": 0,
                "contract_count": 0,
                "closed_count": 0,
                "dead_count": 0,
            },
        )
        stages = _stage_set(lead, outcomes.get(lead.id, []))
        group["total_leads"] += 1
        group["contacted_count"] += 1 if _reached(stages, "contacted") else 0
        group["appointment_count"] += 1 if _reached(stages, "appointment") else 0
        group["offer_count"] += 1 if _reached(stages, "offer") else 0
        group["contract_count"] += 1 if _reached(stages, "contract") else 0
        group["closed_count"] += 1 if _reached(stages, "closed") else 0
        group["dead_count"] += 1 if _reached(stages, "dead") else 0

    items: list[SourceRoiItem] = []
    for group in groups.values():
        cost_per_lead_cents = group.pop("cost_per_lead_cents")
        total = group["total_leads"]
        spend = round((cost_per_lead_cents * total) / 100, 2) if cost_per_lead_cents is not None else None
        items.append(
            SourceRoiItem(
                **group,
                cost_per_lead_dollars=_dollars(cost_per_lead_cents),
                estimated_spend_dollars=spend,
                appointment_rate=_rate(group["appointment_count"], total),
                offer_rate=_rate(group["offer_count"], total),
                contract_rate=_rate(group["contract_count"], total),
                close_rate=_rate(group["closed_count"], total),
                cost_per_appointment_dollars=_cost(spend, group["appointment_count"]),
                cost_per_contract_dollars=_cost(spend, group["contract_count"]),
                cost_per_close_dollars=_cost(spend, group["closed_count"]),
            )
        )

    return sorted(items, key=lambda item: (item.closed_count, item.contract_count, item.appointment_rate or 0), reverse=True)


@router.get("/analytics/stale-leads", response_model=list[StaleLeadItem])
async def get_stale_leads(
    days: int = Query(default=7, ge=1, le=365),
    source: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    rows = await _lead_rows(session, source=source)
    lead_ids = [lead.id for lead, *_ in rows]
    outcomes = await _outcomes_by_lead(session, lead_ids)
    followups = await _followup_activity_by_lead(session, lead_ids)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    stale: list[StaleLeadItem] = []
    for lead, prop, _score, _source_meta in rows:
        lead_outcomes = outcomes.get(lead.id, [])
        stage = _lifecycle_stage(lead, lead_outcomes)
        if stage in TERMINAL_STAGES:
            continue
        latest = _latest_outcome(lead_outcomes)
        explicit_activity = [
            value
            for value in [
                _as_utc(latest.occurred_at) if latest else None,
                _as_utc(followups.get(lead.id)),
            ]
            if value is not None
        ]
        fallback_activity = [_as_utc(lead.updated_at), _as_utc(lead.created_at)]
        last_activity = max(explicit_activity or [value for value in fallback_activity if value is not None], default=None)
        if last_activity is None or last_activity > cutoff:
            continue
        stale_days = max((datetime.now(timezone.utc) - last_activity).days, days)
        stale.append(
            StaleLeadItem(
                lead_id=lead.id,
                lead_name=_lead_name(lead),
                source=lead.source,
                status=lead.status,
                lifecycle_stage=stage,
                last_activity_at=last_activity,
                stale_days=stale_days,
                property_address=prop.address if prop else None,
            )
        )

    return sorted(stale, key=lambda item: item.stale_days, reverse=True)[:limit]


@router.patch("/leads/{lead_id}/outcome", response_model=OutcomeResponse)
async def update_lead_outcome(
    lead_id: str,
    payload: OutcomeUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    stage = normalize_lifecycle_stage(payload.stage)
    lead = await session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    outcome = LeadOutcome(
        lead_id=lead.id,
        stage=stage,
        dead_reason=payload.dead_reason if stage == "dead" else None,
        notes=payload.notes,
        occurred_at=payload.occurred_at or datetime.now(timezone.utc),
    )
    session.add(outcome)
    lead.status = "new" if stage == "received" else stage
    await session.commit()
    await session.refresh(outcome)

    return OutcomeResponse(
        id=outcome.id,
        lead_id=lead.id,
        stage=outcome.stage,
        dead_reason=outcome.dead_reason,
        notes=outcome.notes,
        occurred_at=outcome.occurred_at,
        status=lead.status,
    )


@router.patch("/analytics/sources/{source_name}/cost", response_model=SourceCostResponse)
async def update_source_cost(
    source_name: str,
    payload: SourceCostUpdateRequest,
    session: AsyncSession = Depends(get_session),
):
    normalized_name = source_name.strip()
    if not normalized_name:
        raise HTTPException(status_code=422, detail="Source name is required")

    source = (
        await session.execute(select(LeadSource).where(func.lower(LeadSource.name) == normalized_name.lower()))
    ).scalar_one_or_none()
    if source is None:
        source = LeadSource(name=normalized_name)
        session.add(source)

    if payload.cost_per_lead_dollars is not None:
        source.cost_per_lead_cents = int(round(payload.cost_per_lead_dollars * 100))
    if payload.vendor_name is not None:
        source.vendor_name = payload.vendor_name
    if payload.channel is not None:
        source.channel = payload.channel

    await session.commit()
    return SourceCostResponse(
        source=source.name,
        vendor_name=source.vendor_name,
        channel=source.channel,
        cost_per_lead_dollars=_dollars(source.cost_per_lead_cents),
    )
