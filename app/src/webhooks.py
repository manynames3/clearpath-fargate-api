import hashlib
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import fetch_secret_string, get_settings
from src.database import get_session
from src.models import Lead, Property
from src.schemas import GHLWebhookPayload

router = APIRouter()


def _verify_signature(body: bytes, signature: str | None) -> None:
    settings = get_settings()
    if not settings.ghl_webhook_secret:
        return

    secret = fetch_secret_string(settings.ghl_webhook_secret, settings.aws_region)
    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    provided = (signature or "").removeprefix("sha256=")
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")


@router.post("/ghl")
async def receive_ghl_webhook(
    request: Request,
    x_ghl_signature: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    body = await request.body()
    _verify_signature(body, x_ghl_signature)
    payload = GHLWebhookPayload.model_validate_json(body)
    fields = payload.custom_fields

    result = await session.execute(select(Lead).where(Lead.ghl_id == payload.contact_id))
    lead = result.scalar_one_or_none()
    if lead is None:
        lead = Lead(ghl_id=payload.contact_id)
        session.add(lead)

    lead.first_name = payload.first_name
    lead.last_name = payload.last_name
    lead.phone = payload.phone
    lead.email = payload.email
    lead.status = payload.status or "new"
    lead.source = payload.source
    lead.county = str(fields.get("county") or "") or None
    lead.state = str(fields.get("state") or "GA")

    await session.flush()

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

    await session.commit()
    return {"status": "accepted", "lead_id": lead.id}
