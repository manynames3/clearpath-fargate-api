import hashlib
import hmac
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import fetch_secret_string, get_settings
from src.database import get_session
from src.models import DuplicateLead, Lead, LeadScore, LeadSource, Property, WebhookEvent
from src.schemas import GHLWebhookPayload

router = APIRouter()


def _verify_signature(
    body: bytes,
    signature: str | None,
    shared_secret_header: str | None,
    authorization: str | None,
) -> None:
    settings = get_settings()
    if not settings.ghl_webhook_secret:
        return

    secret = fetch_secret_string(settings.ghl_webhook_secret, settings.aws_region)
    bearer_token = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer_token = authorization.removeprefix("Bearer ").removeprefix("bearer ").strip()

    if hmac.compare_digest(secret, shared_secret_header or "") or hmac.compare_digest(secret, bearer_token):
        return

    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    provided = (signature or "").removeprefix("sha256=")
    if hmac.compare_digest(expected, provided):
        return

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")


def _source_channel(source: str) -> str:
    normalized = source.lower()
    if "facebook" in normalized or "meta" in normalized:
        return "paid-social"
    if "sms" in normalized:
        return "sms"
    if "direct" in normalized:
        return "direct"
    if "vendor" in normalized or "lead" in normalized:
        return "paid-lead-provider"
    return "unknown"


async def _get_or_create_source(session: AsyncSession, source_name: str | None) -> LeadSource | None:
    if not source_name:
        return None

    normalized = source_name.strip()
    if not normalized:
        return None

    result = await session.execute(select(LeadSource).where(func.lower(LeadSource.name) == normalized.lower()))
    source = result.scalar_one_or_none()
    if source:
        return source

    source = LeadSource(name=normalized, vendor_name=normalized, channel=_source_channel(normalized))
    session.add(source)
    await session.flush()
    return source


def _score_lead(lead: Lead, prop: Property | None, has_duplicate: bool) -> tuple[int, str, list[str], bool]:
    score = 45
    reasons: list[str] = []

    status_bonus = {
        "closed": 35,
        "hot": 25,
        "warm": 15,
        "new": 5,
        "dead": -25,
    }.get((lead.status or "new").lower(), 0)
    score += status_bonus
    reasons.append(f"Status is {lead.status or 'new'}")

    if lead.phone:
        score += 5
        reasons.append("Phone present")
    if lead.email:
        score += 3
        reasons.append("Email present")
    if prop and prop.address:
        score += 10
        reasons.append("Property address present")
    if lead.county:
        score += 5
        reasons.append(f"County captured: {lead.county}")

    situation = (prop.situation if prop else None) or ""
    situation_bonus = {
        "inherited": 12,
        "vacant": 10,
        "tax-delinquent": 12,
        "tired landlord": 8,
    }.get(situation.lower(), 0)
    if situation_bonus:
        score += situation_bonus
        reasons.append(f"Motivation signal: {situation}")

    needs_review = score >= 70
    if has_duplicate:
        score -= 20
        needs_review = True
        reasons.append("Possible duplicate lead")

    score = max(0, min(100, score))
    if has_duplicate:
        priority = "review"
    elif score >= 80:
        priority = "high"
    elif score >= 60:
        priority = "medium"
    else:
        priority = "low"

    return score, priority, reasons, needs_review


async def _upsert_lead_score(session: AsyncSession, lead: Lead, prop: Property | None, has_duplicate: bool) -> None:
    score, priority, reasons, needs_review = _score_lead(lead, prop, has_duplicate)
    result = await session.execute(select(LeadScore).where(LeadScore.lead_id == lead.id))
    lead_score = result.scalar_one_or_none()
    if lead_score is None:
        lead_score = LeadScore(lead_id=lead.id)
        session.add(lead_score)

    lead_score.score = score
    lead_score.priority = priority
    lead_score.reasons = reasons
    lead_score.needs_review = needs_review


async def _record_duplicate_matches(session: AsyncSession, lead: Lead, prop: Property | None) -> bool:
    conditions = []
    if lead.phone:
        conditions.append(Lead.phone == lead.phone)
    if lead.email:
        conditions.append(func.lower(Lead.email) == lead.email.lower())
    if prop and prop.address:
        conditions.append(func.lower(Property.address) == prop.address.lower())
    if not conditions:
        return False

    rows = (
        await session.execute(
            select(Lead, Property)
            .outerjoin(Property, Property.lead_id == Lead.id)
            .where(Lead.id != lead.id)
            .where(or_(*conditions))
            .limit(10)
        )
    ).all()

    has_duplicate = False
    for duplicate_lead, duplicate_property in rows:
        match_type = "contact"
        confidence = 80
        reason = "Matched contact detail"
        if lead.phone and duplicate_lead.phone == lead.phone:
            match_type = "phone"
            confidence = 95
            reason = "Phone number matches an existing lead"
        elif lead.email and duplicate_lead.email and duplicate_lead.email.lower() == lead.email.lower():
            match_type = "email"
            confidence = 90
            reason = "Email matches an existing lead"
        elif prop and duplicate_property and prop.address and duplicate_property.address:
            if duplicate_property.address.lower() == prop.address.lower():
                match_type = "address"
                confidence = 85
                reason = "Property address matches an existing lead"

        existing = await session.execute(
            select(DuplicateLead).where(
                DuplicateLead.lead_id == lead.id,
                DuplicateLead.duplicate_lead_id == duplicate_lead.id,
                DuplicateLead.match_type == match_type,
            )
        )
        if existing.scalar_one_or_none() is None:
            session.add(
                DuplicateLead(
                    lead_id=lead.id,
                    duplicate_lead_id=duplicate_lead.id,
                    match_type=match_type,
                    confidence=confidence,
                    reason=reason,
                )
            )
        has_duplicate = True

    return has_duplicate


@router.post("/ghl")
async def receive_ghl_webhook(
    request: Request,
    x_clearpath_signature: str | None = Header(default=None),
    x_clearpath_webhook_secret: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    body = await request.body()
    _verify_signature(body, x_clearpath_signature, x_clearpath_webhook_secret, authorization)
    payload = GHLWebhookPayload.model_validate_json(body)
    raw_payload = json.loads(body)
    fields = payload.custom_fields

    result = await session.execute(select(Lead).where(Lead.ghl_id == payload.contact_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        lead = Lead(ghl_id=payload.contact_id)
        session.add(lead)

    source = await _get_or_create_source(session, payload.source)
    lead.source_id = source.id if source else None
    lead.first_name = payload.first_name
    lead.last_name = payload.last_name
    lead.phone = payload.phone
    lead.email = payload.email
    lead.status = payload.status or "new"
    lead.source = payload.source
    lead.county = str(fields.get("county") or "") or None
    lead.state = str(fields.get("state") or "GA")

    await session.flush()

    prop = None
    address = fields.get("property_address")
    if address:
        property_result = await session.execute(select(Property).where(Property.lead_id == lead.id).limit(1))
        prop = property_result.scalar_one_or_none()
        if prop is None:
            prop = Property(lead_id=lead.id)
            session.add(prop)
        prop.address = str(address)
        prop.city = str(fields.get("city") or "") or None
        prop.county = lead.county
        prop.state = lead.state
        prop.zip = str(fields.get("zip") or "") or None
        prop.situation = str(fields.get("situation") or "") or None

    session.add(
        WebhookEvent(
            provider="gohighlevel",
            external_id=payload.contact_id,
            lead_id=lead.id,
            event_type="contact",
            payload=raw_payload,
        )
    )
    has_duplicate = await _record_duplicate_matches(session, lead, prop)
    await _upsert_lead_score(session, lead, prop, has_duplicate)

    await session.commit()
    return {"status": "accepted", "lead_id": lead.id}
