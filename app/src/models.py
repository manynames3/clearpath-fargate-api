import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def uuid_str() -> str:
    return str(uuid.uuid4())


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    ghl_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source_id: Mapped[str | None] = mapped_column(ForeignKey("lead_sources.id", ondelete="SET NULL"))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="new")
    source: Mapped[str | None] = mapped_column(String(100))
    county: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(2), default="GA")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    properties: Mapped[list["Property"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    follow_ups: Mapped[list["FollowUp"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    source_meta: Mapped["LeadSource | None"] = relationship(back_populates="leads")
    webhook_events: Mapped[list["WebhookEvent"]] = relationship(back_populates="lead")
    score: Mapped["LeadScore | None"] = relationship(back_populates="lead", cascade="all, delete-orphan")


class LeadSource(Base):
    __tablename__ = "lead_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    channel: Mapped[str | None] = mapped_column(String(100))
    cost_per_lead_cents: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    leads: Mapped[list[Lead]] = relationship(back_populates="source_meta")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(100))
    county: Mapped[str | None] = mapped_column(String(100))
    county_resolution_method: Mapped[str | None] = mapped_column(String(50))
    county_resolution_confidence: Mapped[int | None] = mapped_column(Integer)
    state: Mapped[str | None] = mapped_column(String(2))
    zip: Mapped[str | None] = mapped_column(String(10))
    estimated_value: Mapped[int | None] = mapped_column(Integer)
    situation: Mapped[str | None] = mapped_column(String(100))
    occupancy: Mapped[str | None] = mapped_column(String(100))
    selling_urgency: Mapped[str | None] = mapped_column(String(100))
    seller_type: Mapped[str | None] = mapped_column(String(100))
    listing_status: Mapped[str | None] = mapped_column(String(100))
    repair_scope: Mapped[str | None] = mapped_column(String(255))
    property_type: Mapped[str | None] = mapped_column(String(100))
    years_owned: Mapped[str | None] = mapped_column(String(100))
    apn: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="properties")


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    contacted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    method: Mapped[str | None] = mapped_column(String(50))
    notes: Mapped[str | None] = mapped_column(Text)
    next_follow_up: Mapped[date | None] = mapped_column(Date)

    lead: Mapped[Lead] = relationship(back_populates="follow_ups")


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"
    __table_args__ = (UniqueConstraint("county", "state", "snapshot_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    county: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    median_price: Mapped[int | None] = mapped_column(Integer)
    avg_dom: Mapped[int | None] = mapped_column(Integer)
    snapshot_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    provider: Mapped[str] = mapped_column(String(100), default="gohighlevel")
    external_id: Mapped[str | None] = mapped_column(String(255))
    lead_id: Mapped[str | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(100), default="contact")
    payload: Mapped[dict | None] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped[Lead | None] = relationship(back_populates="webhook_events")


class LeadScore(Base):
    __tablename__ = "lead_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"), unique=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    priority: Mapped[str] = mapped_column(String(50), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    lead: Mapped[Lead] = relationship(back_populates="score")


class DuplicateLead(Base):
    __tablename__ = "duplicate_leads"
    __table_args__ = (UniqueConstraint("lead_id", "duplicate_lead_id", "match_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    duplicate_lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    match_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped[Lead] = relationship(foreign_keys=[lead_id])
    duplicate_lead: Mapped[Lead] = relationship(foreign_keys=[duplicate_lead_id])
