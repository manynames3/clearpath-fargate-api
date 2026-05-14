CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS lead_sources (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(100) UNIQUE NOT NULL,
    vendor_name         VARCHAR(255),
    channel             VARCHAR(100),
    cost_per_lead_cents INTEGER,
    active              BOOLEAN DEFAULT TRUE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leads (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ghl_id      VARCHAR(255) UNIQUE NOT NULL,
    source_id   UUID REFERENCES lead_sources(id) ON DELETE SET NULL,
    first_name  VARCHAR(255),
    last_name   VARCHAR(255),
    phone       VARCHAR(20),
    email       VARCHAR(255),
    status      VARCHAR(50) DEFAULT 'new',
    source      VARCHAR(100),
    county      VARCHAR(100),
    state       CHAR(2) DEFAULT 'GA',
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS properties (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id         UUID REFERENCES leads(id) ON DELETE CASCADE,
    address         TEXT,
    city            VARCHAR(100),
    county          VARCHAR(100),
    county_resolution_method VARCHAR(50),
    county_resolution_confidence INTEGER,
    state           CHAR(2),
    zip             VARCHAR(10),
    estimated_value INTEGER,
    situation       VARCHAR(100),
    occupancy       VARCHAR(100),
    selling_urgency VARCHAR(100),
    seller_type     VARCHAR(100),
    listing_status  VARCHAR(100),
    repair_scope    VARCHAR(255),
    property_type   VARCHAR(100),
    years_owned     VARCHAR(100),
    apn             VARCHAR(100),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS follow_ups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id         UUID REFERENCES leads(id) ON DELETE CASCADE,
    contacted_at    TIMESTAMPTZ DEFAULT NOW(),
    method          VARCHAR(50),
    notes           TEXT,
    next_follow_up  DATE
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    county        VARCHAR(100) NOT NULL,
    state         CHAR(2) NOT NULL,
    median_price  INTEGER,
    avg_dom       INTEGER,
    snapshot_date DATE DEFAULT CURRENT_DATE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(county, state, snapshot_date)
);

CREATE TABLE IF NOT EXISTS webhook_events (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider    VARCHAR(100) DEFAULT 'gohighlevel',
    external_id VARCHAR(255),
    lead_id     UUID REFERENCES leads(id) ON DELETE SET NULL,
    event_type  VARCHAR(100) DEFAULT 'contact',
    payload     JSONB,
    received_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_scores (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id      UUID UNIQUE REFERENCES leads(id) ON DELETE CASCADE,
    score        INTEGER NOT NULL,
    priority     VARCHAR(50) NOT NULL,
    reasons      JSONB DEFAULT '[]'::jsonb,
    needs_review BOOLEAN DEFAULT FALSE,
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS duplicate_leads (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id           UUID REFERENCES leads(id) ON DELETE CASCADE,
    duplicate_lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    match_type        VARCHAR(50) NOT NULL,
    confidence        INTEGER NOT NULL,
    reason            TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(lead_id, duplicate_lead_id, match_type)
);

CREATE TABLE IF NOT EXISTS lead_outcomes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id     UUID REFERENCES leads(id) ON DELETE CASCADE,
    stage       VARCHAR(50) NOT NULL,
    dead_reason VARCHAR(255),
    notes       TEXT,
    occurred_at TIMESTAMPTZ DEFAULT NOW(),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_source_id ON leads(source_id);
CREATE INDEX IF NOT EXISTS idx_leads_county ON leads(county);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_follow_ups_lead_id ON follow_ups(lead_id);
CREATE INDEX IF NOT EXISTS idx_follow_ups_next ON follow_ups(next_follow_up);
CREATE INDEX IF NOT EXISTS idx_webhook_events_lead_id ON webhook_events(lead_id);
CREATE INDEX IF NOT EXISTS idx_webhook_events_external_id ON webhook_events(external_id);
CREATE INDEX IF NOT EXISTS idx_lead_scores_score ON lead_scores(score);
CREATE INDEX IF NOT EXISTS idx_lead_scores_needs_review ON lead_scores(needs_review);
CREATE INDEX IF NOT EXISTS idx_duplicate_leads_lead_id ON duplicate_leads(lead_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_leads_duplicate_id ON duplicate_leads(duplicate_lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_outcomes_lead_id ON lead_outcomes(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_outcomes_stage ON lead_outcomes(stage);
CREATE INDEX IF NOT EXISTS idx_lead_outcomes_occurred_at ON lead_outcomes(occurred_at);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'clearpath_app') THEN
        CREATE ROLE clearpath_app LOGIN;
    END IF;
END
$$;

GRANT rds_iam TO clearpath_app;
GRANT CONNECT ON DATABASE clearpath TO clearpath_app;
GRANT USAGE ON SCHEMA public TO clearpath_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO clearpath_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO clearpath_app;
