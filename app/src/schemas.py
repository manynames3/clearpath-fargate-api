from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class GHLWebhookPayload(BaseModel):
    contact_id: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    source: str | None = None
    status: str = "new"
    custom_fields: dict[str, str | int | None] = Field(default_factory=dict)


class PropertyResponse(BaseModel):
    address: str | None = None
    city: str | None = None
    county: str | None = None
    state: str | None = None
    zip: str | None = None
    estimated_value: int | None = None
    situation: str | None = None

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
