from datetime import date, datetime
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _first_present(data: dict, *keys: str):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize_custom_fields(value) -> dict[str, str | int | None]:
    if value is None:
        return {}

    def canonical_key(key: str) -> str:
        normalized = re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
        aliases = {
            "e_mail_entered_by_seller": "email",
            "standard_seller_number": "phone",
            "property_address": "property_address",
            "zip_code": "zip",
            "zipcode": "zip",
            "postal_code": "zip",
            "who_s_living_in_the_property": "occupancy",
            "whos_living_in_the_property": "occupancy",
            "seller_motivation": "situation",
            "seller_owner_or_agent": "seller_type",
            "seller_owner_agent": "seller_type",
            "listing_status": "listing_status",
            "selling_urgency": "selling_urgency",
            "conversation_notes": "conversation_notes",
            "repair_scope": "repair_scope",
            "property_type": "property_type",
            "square_footage": "square_footage",
            "year_built": "year_built",
            "years_of_ownership": "years_owned",
            "years_ownership": "years_owned",
            "lot_size": "lot_size",
        }
        return aliases.get(normalized, normalized)

    if isinstance(value, dict):
        fields = {}
        for key, field_value in value.items():
            fields[str(key)] = field_value
            fields.setdefault(canonical_key(str(key)), field_value)
        return fields

    if not isinstance(value, list):
        return {}

    fields: dict[str, str | int | None] = {}
    for item in value:
        if not isinstance(item, dict):
            continue

        key = _first_present(item, "key", "fieldKey", "name", "fieldName", "id")
        field_value = _first_present(item, "value", "field_value", "fieldValue")
        if key and field_value is not None:
            fields[str(key)] = field_value
            fields.setdefault(canonical_key(str(key)), field_value)

    return fields


class GHLWebhookPayload(BaseModel):
    contact_id: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    status: str = "new"
    custom_fields: dict[str, str | int | None] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_highlevel_payload(cls, data):
        if not isinstance(data, dict):
            return data

        contact = data.get("contact")
        if not isinstance(contact, dict):
            contact = {}

        fields = _normalize_custom_fields(_first_present(data, "custom_fields", "customFields"))
        top_level_property_fields = {
            "property_address": _first_present(data, "property_address", "propertyAddress"),
            "city": data.get("city"),
            "county": data.get("county"),
            "state": data.get("state"),
            "zip": _first_present(data, "zip", "zip_code", "zipCode", "postalCode"),
            "situation": data.get("situation"),
            "occupancy": data.get("occupancy"),
            "selling_urgency": _first_present(data, "selling_urgency", "sellingUrgency"),
            "seller_type": _first_present(data, "seller_type", "sellerType"),
            "listing_status": _first_present(data, "listing_status", "listingStatus"),
            "repair_scope": _first_present(data, "repair_scope", "repairScope"),
            "property_type": _first_present(data, "property_type", "propertyType"),
            "years_owned": _first_present(data, "years_owned", "yearsOwned"),
            "apn": _first_present(data, "apn", "APN"),
        }
        for key, value in top_level_property_fields.items():
            if value not in (None, "") and key not in fields:
                fields[key] = value

        return {
            "contact_id": _first_present(data, "contact_id", "contactId", "id") or _first_present(contact, "id"),
            "first_name": _first_present(data, "first_name", "firstName")
            or _first_present(contact, "first_name", "firstName")
            or fields.get("first_name"),
            "last_name": _first_present(data, "last_name", "lastName")
            or _first_present(contact, "last_name", "lastName")
            or fields.get("last_name"),
            "phone": data.get("phone") or contact.get("phone") or fields.get("phone"),
            "email": data.get("email") or contact.get("email") or fields.get("email"),
            "source": data.get("source") or contact.get("source"),
            "status": data.get("status") or contact.get("status") or "new",
            "custom_fields": fields,
        }


class PropertyResponse(BaseModel):
    address: str | None = None
    city: str | None = None
    county: str | None = None
    county_resolution_method: str | None = None
    county_resolution_confidence: int | None = None
    state: str | None = None
    zip: str | None = None
    estimated_value: int | None = None
    situation: str | None = None
    occupancy: str | None = None
    selling_urgency: str | None = None
    seller_type: str | None = None
    listing_status: str | None = None
    repair_scope: str | None = None
    property_type: str | None = None
    years_owned: str | None = None
    apn: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LeadResponse(BaseModel):
    id: str
    ghl_id: str
    first_name: str | None = None
    last_name: str | None = None
    status: str
    source: str | None = None
    county: str | None = None
    state: str
    property: PropertyResponse | None = None
    last_contacted_at: datetime | None = None
    next_follow_up: date | None = None


class LeadsPage(BaseModel):
    count: int
    limit: int
    leads: list[LeadResponse]


class MarketSnapshotResponse(BaseModel):
    county: str
    state: str
    median_price: int | None
    avg_dom: int | None
    snapshot_date: date
    cache_ttl: int = 3600

    model_config = ConfigDict(from_attributes=True)


class BreakdownItem(BaseModel):
    label: str
    count: int


class IntelligenceSummary(BaseModel):
    total_leads: int
    total_sources: int
    total_duplicates: int
    needs_review_count: int
    average_score: float | None
    status_counts: list[BreakdownItem]
    top_counties: list[BreakdownItem]
    recent_webhook_events: int


class SourcePerformanceItem(BaseModel):
    source: str
    vendor_name: str | None = None
    channel: str | None = None
    total_leads: int
    hot_leads: int
    warm_leads: int
    closed_leads: int
    dead_leads: int
    duplicate_count: int
    needs_review_count: int
    average_score: float | None
    estimated_spend_dollars: float | None = None


class DuplicateLeadItem(BaseModel):
    id: str
    lead_id: str
    duplicate_lead_id: str
    match_type: str
    confidence: int
    reason: str | None = None
    lead_name: str
    duplicate_name: str
    created_at: datetime


class LeadScoreItem(BaseModel):
    lead_id: str
    lead_name: str
    source: str | None = None
    county: str | None = None
    status: str
    score: int
    priority: str
    reasons: list[str]
    needs_review: bool
    property_address: str | None = None
    updated_at: datetime


class CountyPerformanceItem(BaseModel):
    county: str
    state: str
    total_leads: int
    hot_leads: int
    warm_leads: int
    duplicate_count: int
    needs_review_count: int
    average_score: float | None
    median_price: int | None = None
    avg_dom: int | None = None
