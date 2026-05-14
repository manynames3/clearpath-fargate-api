import hashlib
import hmac
import json
import re

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import fetch_secret_string, get_settings
from src.county_resolver import normalize_zip, resolve_county
from src.database import get_session
from src.models import DuplicateLead, Lead, LeadOutcome, LeadScore, LeadSource, Property, WebhookEvent
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


STATE_ABBREVIATIONS = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}


def _text(value) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip() or None


def _field(fields: dict, *keys: str) -> str | None:
    for key in keys:
        value = _text(fields.get(key))
        if value:
            return value
    return None


def _normalize_state(value) -> str:
    state = (_text(value) or "GA").strip()
    if len(state) == 2:
        return state.upper()
    return STATE_ABBREVIATIONS.get(state.lower(), state[:2].upper())


def _zip_from_address(address: str | None) -> str | None:
    if not address:
        return None
    match = re.search(r"\b(\d{5})(?:-\d{4})?\b", address)
    return match.group(1) if match else None


def _has_any(value: str | None, *needles: str) -> bool:
    text = (value or "").lower()
    return any(needle in text for needle in needles)


def _lifecycle_stage_from_status(value: str | None) -> str | None:
    normalized = (value or "").lower().strip().replace(" ", "_").replace("-", "_")
    aliases = {
        "new": "received",
        "contact": "contacted",
        "called": "contacted",
        "appointment_set": "appointment",
        "offer_made": "offer",
        "under_contract": "contract",
        "closed_won": "closed",
        "lost": "dead",
    }
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in {"received", "contacted", "appointment", "offer", "contract", "closed", "dead"} else None


def _max_number(value: str | None) -> int | None:
    numbers = [int(match) for match in re.findall(r"\d+", value or "")]
    return max(numbers) if numbers else None


def _int_field(fields: dict, *keys: str) -> int | None:
    for key in keys:
        value = _field(fields, key)
        if not value:
            continue
        normalized = re.sub(r"[^0-9.]+", "", value)
        if not normalized:
            continue
        try:
            return int(float(normalized))
        except ValueError:
            continue
    return None


def _score_lead(lead: Lead, prop: Property | None, has_duplicate: bool) -> tuple[int, str, list[str], bool]:
    score = 35
    reasons: list[str] = []
    review_flag = False

    status_bonus = {
        "closed": 30,
        "hot": 20,
        "warm": 10,
        "new": 0,
        "dead": -25,
    }.get((lead.status or "new").lower(), 0)
    score += status_bonus
    reasons.append(f"Status is {lead.status or 'new'}")

    if lead.county:
        score += 4
        if prop and prop.county_resolution_method and prop.county_resolution_method != "provider":
            method = prop.county_resolution_method.replace("_", " ")
            reasons.append(f"County resolved from {method}: {lead.county}")
        else:
            reasons.append(f"County captured: {lead.county}")
    if prop and prop.zip:
        score += 4
        reasons.append(f"ZIP captured: {prop.zip}")

    situation = (prop.situation if prop else None) or ""
    situation_bonus = 0
    if _has_any(situation, "inherited", "probate"):
        situation_bonus = 14
    elif _has_any(situation, "tax", "delinquent"):
        situation_bonus = 12
    elif _has_any(situation, "foreclosure", "preforeclosure"):
        situation_bonus = 14
    elif _has_any(situation, "divorce"):
        situation_bonus = 10
    elif _has_any(situation, "tired landlord"):
        situation_bonus = 8
    if situation_bonus:
        score += situation_bonus
        reasons.append(f"Motivation signal: {situation}")

    occupancy = prop.occupancy if prop else None
    if _has_any(occupancy, "vacant"):
        score += 12
        reasons.append("Property is vacant")
    elif _has_any(occupancy, "tenant", "renter"):
        score += 4
        reasons.append("Tenant-occupied property")

    urgency = prop.selling_urgency if prop else None
    if _has_any(urgency, "asap", "urgent", "immediate", "now"):
        score += 18
        reasons.append(f"Urgency signal: {urgency}")
    elif _has_any(urgency, "soon", "30"):
        score += 10
        reasons.append(f"Near-term urgency: {urgency}")
    elif _has_any(urgency, "60", "90"):
        score += 4
        reasons.append(f"Medium-term urgency: {urgency}")
    elif _has_any(urgency, "no rush", "not urgent"):
        score -= 5
        reasons.append(f"Low urgency: {urgency}")

    seller_type = prop.seller_type if prop else None
    if _has_any(seller_type, "owner"):
        score += 8
        reasons.append("Seller is owner")
    elif _has_any(seller_type, "agent", "realtor", "wholesaler"):
        score -= 12
        review_flag = True
        reasons.append(f"Non-owner seller type: {seller_type}")

    listing_status = prop.listing_status if prop else None
    if _has_any(listing_status, "not listed", "off market"):
        score += 10
        reasons.append("Property is not listed")
    elif _has_any(listing_status, "listed", "mls", "under contract", "pending"):
        score -= 16
        review_flag = True
        reasons.append(f"Listing status needs review: {listing_status}")

    repair_scope = prop.repair_scope if prop else None
    if _has_any(repair_scope, "major", "roof", "kitchen", "bathroom", "foundation", "remodel"):
        score += 10
        reasons.append(f"Repair scope: {repair_scope}")
    elif _has_any(repair_scope, "repair", "deferred"):
        score += 8
        reasons.append(f"Repair need: {repair_scope}")
    elif _has_any(repair_scope, "cosmetic"):
        score += 4
        reasons.append(f"Cosmetic repair scope: {repair_scope}")
    elif _has_any(repair_scope, "turnkey", "move in"):
        score -= 4
        reasons.append(f"Limited distress signal: {repair_scope}")

    property_type = prop.property_type if prop else None
    if _has_any(property_type, "single family", "sfr"):
        score += 6
        reasons.append("Single-family property")
    elif _has_any(property_type, "land", "mobile", "condo", "townhome"):
        score -= 4
        reasons.append(f"Property type needs review: {property_type}")

    years_owned = _max_number(prop.years_owned if prop else None)
    if years_owned and years_owned >= 15:
        score += 7
        reasons.append(f"Long ownership: {prop.years_owned}")
    elif years_owned and years_owned >= 10:
        score += 5
        reasons.append(f"Established ownership: {prop.years_owned}")
    elif years_owned and years_owned >= 5:
        score += 3
        reasons.append(f"Ownership history: {prop.years_owned}")

    needs_review = score >= 70 or review_flag
    if has_duplicate:
        score -= 20
        needs_review = True
        reasons.append("Possible duplicate lead")

    score = max(0, min(100, score))
    if has_duplicate or review_flag:
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


async def upsert_lead_from_payload(
    session: AsyncSession,
    payload: GHLWebhookPayload,
    raw_payload: dict,
    provider: str = "gohighlevel",
) -> Lead:
    fields = payload.custom_fields

    result = await session.execute(select(Lead).where(Lead.ghl_id == payload.contact_id))
    lead = result.scalar_one_or_none()
    is_new_lead = lead is None
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
    explicit_county = _field(fields, "county")
    lead.county = explicit_county
    lead.state = _normalize_state(_field(fields, "state"))

    await session.flush()
    if is_new_lead:
        session.add(LeadOutcome(lead_id=lead.id, stage="received"))

    lifecycle_stage = _lifecycle_stage_from_status(payload.status)
    if lifecycle_stage and lifecycle_stage != "received":
        existing_outcome = await session.execute(
            select(LeadOutcome).where(LeadOutcome.lead_id == lead.id, LeadOutcome.stage == lifecycle_stage).limit(1)
        )
        if existing_outcome.scalar_one_or_none() is None:
            session.add(LeadOutcome(lead_id=lead.id, stage=lifecycle_stage))

    prop = None
    address = _field(fields, "property_address", "address")
    if address:
        property_result = await session.execute(select(Property).where(Property.lead_id == lead.id).limit(1))
        prop = property_result.scalar_one_or_none()
        if prop is None:
            prop = Property(lead_id=lead.id)
            session.add(prop)
        prop.address = address
        prop.city = _field(fields, "city")
        prop.state = lead.state
        prop.zip = normalize_zip(_field(fields, "zip") or _zip_from_address(address))
        prop.estimated_value = _int_field(fields, "estimated_value", "sold_comps")
        prop.situation = _field(fields, "situation")
        prop.occupancy = _field(fields, "occupancy")
        prop.selling_urgency = _field(fields, "selling_urgency")
        prop.seller_type = _field(fields, "seller_type")
        prop.listing_status = _field(fields, "listing_status")
        prop.repair_scope = _field(fields, "repair_scope")
        prop.property_type = _field(fields, "property_type")
        prop.years_owned = _field(fields, "years_owned")
        prop.apn = _field(fields, "apn")

    resolution = await resolve_county(
        explicit_county=explicit_county,
        address=prop.address if prop else _field(fields, "property_address", "address"),
        city=prop.city if prop else _field(fields, "city"),
        state=lead.state,
        zip_code=prop.zip if prop else _field(fields, "zip"),
    )
    lead.county = resolution.county
    lead.state = resolution.state or lead.state
    if prop:
        prop.county = resolution.county
        prop.state = lead.state
        prop.county_resolution_method = resolution.method
        prop.county_resolution_confidence = resolution.confidence

    should_record_event = True
    if provider == "csv-backfill":
        existing_event = await session.execute(
            select(WebhookEvent).where(
                WebhookEvent.provider == provider,
                WebhookEvent.external_id == payload.contact_id,
                WebhookEvent.event_type == "contact",
            )
        )
        should_record_event = existing_event.scalar_one_or_none() is None

    if should_record_event:
        session.add(
            WebhookEvent(
                provider=provider,
                external_id=payload.contact_id,
                lead_id=lead.id,
                event_type="contact",
                payload=raw_payload,
            )
        )
    has_duplicate = await _record_duplicate_matches(session, lead, prop)
    await _upsert_lead_score(session, lead, prop, has_duplicate)
    return lead


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
    lead = await upsert_lead_from_payload(session, payload, raw_payload)

    await session.commit()
    return {"status": "accepted", "lead_id": lead.id}
