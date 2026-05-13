#!/usr/bin/env python3
"""Import existing paid-lead CSV exports into the intelligence database."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from src.database import get_session_factory  # noqa: E402
from src.schemas import GHLWebhookPayload  # noqa: E402
from src.webhooks import upsert_lead_from_payload  # noqa: E402


SOURCE_COLUMNS = {
    "source",
    "lead_source",
    "lead provider",
    "lead_provider",
    "provider",
    "provider name",
    "provider_name",
    "vendor",
    "vendor name",
    "vendor_name",
    "tags",
}

ID_COLUMNS = {
    "contact_id",
    "contact id",
    "ghl_id",
    "ghl id",
    "id",
    "lead_id",
    "lead id",
    "external_id",
    "external id",
}


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _value(row: dict[str, str], *columns: str) -> str | None:
    lookup = {key.lower().strip(): value for key, value in row.items()}
    for column in columns:
        value = _clean(lookup.get(column.lower().strip()))
        if value:
            return value
    return None


def _contact_id(row: dict[str, str]) -> str:
    for column in ID_COLUMNS:
        value = _value(row, column)
        if value:
            return value

    fingerprint_parts = [
        _value(row, "phone", "standard seller number"),
        _value(row, "email", "e-mail (entered by seller)", "e_mail_entered_by_seller"),
        _value(row, "property address", "property_address", "address"),
    ]
    fingerprint = "|".join(part or "" for part in fingerprint_parts)
    return "csv-" + hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]


def _source(row: dict[str, str], default_source: str | None) -> str | None:
    for column in SOURCE_COLUMNS:
        value = _value(row, column)
        if value:
            return value
    return default_source


def row_to_payload(row: dict[str, str], default_source: str | None) -> dict:
    payload = {
        "id": _contact_id(row),
        "source": _source(row, default_source),
        "status": _value(row, "status", "stage", "pipeline stage") or "new",
        "customFields": [
            {"key": key, "field_value": value}
            for key, value in row.items()
            if _clean(value) is not None
        ],
    }

    for source_key, payload_key in [
        ("first_name", "firstName"),
        ("first name", "firstName"),
        ("last_name", "lastName"),
        ("last name", "lastName"),
        ("phone", "phone"),
        ("standard seller number", "phone"),
        ("email", "email"),
        ("e-mail (entered by seller)", "email"),
    ]:
        value = _value(row, source_key)
        if value and payload_key not in payload:
            payload[payload_key] = value

    return payload


async def import_csv(csv_path: Path, default_source: str | None, dry_run: bool) -> int:
    count = 0
    async with get_session_factory()() as session:
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                raw_payload = row_to_payload(row, default_source)
                payload = GHLWebhookPayload.model_validate(raw_payload)
                if dry_run:
                    print(f"[dry-run] {payload.contact_id} {payload.first_name or ''} {payload.last_name or ''}".strip())
                else:
                    await upsert_lead_from_payload(session, payload, raw_payload, provider="csv-backfill")
                count += 1

        if dry_run:
            await session.rollback()
        else:
            await session.commit()

    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill existing paid leads from a CSV export.")
    parser.add_argument("--csv", required=True, type=Path, help="Path to a GHL/provider/Notion CSV export.")
    parser.add_argument("--source", help="Default source/vendor name when the CSV has no source column.")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate rows without writing to the database.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    imported = asyncio.run(import_csv(args.csv, args.source, args.dry_run))
    action = "Validated" if args.dry_run else "Imported"
    print(f"{action} {imported} lead row(s).")


if __name__ == "__main__":
    main()
