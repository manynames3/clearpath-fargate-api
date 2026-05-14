from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import require_leads_api_key
from src.database import get_session
from src.models import LeadSource
from src.schemas import CsvImportError, CsvImportResponse, GHLWebhookPayload
from src.webhooks import upsert_lead_from_payload

router = APIRouter(prefix="/imports", dependencies=[Depends(require_leads_api_key)])


def _normalize_key(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (value or "").lower()).strip("_")


def _normalized_row(row: dict[str, str | None]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in row.items():
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        normalized[str(key)] = text
        normalized[_normalize_key(str(key))] = text
    return normalized


def _field(row: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key) or row.get(_normalize_key(key))
        if value not in (None, ""):
            return str(value).strip()
    return None


def _cost_cents(row: dict[str, str], fallback_dollars: float | None) -> int | None:
    raw_cost = _field(row, "cost_per_lead", "cost per lead", "lead_cost", "lead cost", "cpl")
    if raw_cost is None and fallback_dollars is None:
        return None

    try:
        amount = Decimal(str(raw_cost if raw_cost is not None else fallback_dollars).replace("$", "").replace(",", ""))
    except (InvalidOperation, AttributeError):
        return None
    if amount < 0:
        return None
    return int(amount * 100)


def _source(row: dict[str, str], default_source: str | None) -> str:
    return (
        default_source
        or _field(row, "source", "lead_source", "lead source", "provider", "vendor", "lead_provider", "lead provider")
        or "csv-backfill"
    )


def _stable_contact_id(row: dict[str, str], source: str, row_number: int) -> str:
    explicit_id = _field(
        row,
        "contact_id",
        "contact id",
        "ghl_id",
        "ghl id",
        "id",
        "lead_id",
        "lead id",
        "external_id",
        "external id",
        "provider_lead_id",
        "provider lead id",
    )
    if explicit_id:
        return explicit_id

    identity_parts = [
        _field(row, "phone", "standard_seller_number", "standard seller number", "seller phone"),
        _field(row, "email", "e_mail_entered_by_seller", "e-mail (entered by seller)", "seller email"),
        _field(row, "property_address", "property address", "address"),
        source,
    ]
    identity = "|".join(part or "" for part in identity_parts).lower()
    if identity.strip("|"):
        digest_source = identity
    else:
        digest_source = json.dumps(row, sort_keys=True) + f"|{row_number}"
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:20]
    return f"csv-{digest}"


def _payload_from_row(row: dict[str, str | None], *, default_source: str | None, row_number: int) -> dict:
    normalized = _normalized_row(row)
    source = _source(normalized, default_source)
    return {
        "id": _stable_contact_id(normalized, source, row_number),
        "firstName": _field(normalized, "first_name", "first name", "firstname"),
        "lastName": _field(normalized, "last_name", "last name", "lastname"),
        "phone": _field(normalized, "phone", "standard_seller_number", "standard seller number", "seller phone"),
        "email": _field(normalized, "email", "e_mail_entered_by_seller", "e-mail (entered by seller)", "seller email"),
        "source": source,
        "status": _field(normalized, "status", "lifecycle_stage", "lifecycle stage", "stage", "outcome") or "new",
        "customFields": dict(row),
    }


def _decode_csv(body: bytes) -> csv.DictReader:
    if not body.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV body is empty")

    text = body.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV header row is required")
    return reader


@router.post("/leads/csv", response_model=CsvImportResponse)
async def import_leads_csv(
    request: Request,
    source: str | None = Query(default=None, description="Default lead source/provider if the CSV does not include one"),
    cost_per_lead_dollars: float | None = Query(default=None, ge=0),
    dry_run: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
):
    reader = _decode_csv(await request.body())
    imported = 0
    failed = 0
    rows_received = 0
    source_cost_updates = 0
    sample_lead_ids: list[str] = []
    errors: list[CsvImportError] = []

    for row_number, row in enumerate(reader, start=2):
        rows_received += 1
        try:
            raw_payload = _payload_from_row(row, default_source=source, row_number=row_number)
            parsed = GHLWebhookPayload.model_validate(raw_payload)
            lead = await upsert_lead_from_payload(session, parsed, raw_payload, provider="csv-backfill")

            normalized = _normalized_row(row)
            cost_cents = _cost_cents(normalized, cost_per_lead_dollars)
            if cost_cents is not None and lead.source_id:
                source_meta = await session.get(LeadSource, lead.source_id)
                if source_meta:
                    source_meta.cost_per_lead_cents = cost_cents
                    source_cost_updates += 1

            await session.flush()
            imported += 1
            if len(sample_lead_ids) < 10:
                sample_lead_ids.append(lead.id)

            if dry_run:
                await session.rollback()
            else:
                await session.commit()
        except (ValidationError, ValueError) as exc:
            await session.rollback()
            failed += 1
            errors.append(CsvImportError(row_number=row_number, message=str(exc)))
        except Exception as exc:
            await session.rollback()
            failed += 1
            errors.append(CsvImportError(row_number=row_number, message=f"{type(exc).__name__}: {exc}"))

    return CsvImportResponse(
        provider="csv-backfill",
        source=source,
        dry_run=dry_run,
        rows_received=rows_received,
        imported=imported,
        failed=failed,
        source_cost_updates=source_cost_updates,
        sample_lead_ids=sample_lead_ids,
        errors=errors[:25],
    )
