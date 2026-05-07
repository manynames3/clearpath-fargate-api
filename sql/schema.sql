CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS leads (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ghl_id      VARCHAR(255) UNIQUE NOT NULL,
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
    state           CHAR(2),
    zip             VARCHAR(10),
    estimated_value INTEGER,
    situation       VARCHAR(100),
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

CREATE INDEX IF NOT EXISTS idx_leads_county ON leads(county);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_follow_ups_lead_id ON follow_ups(lead_id);
CREATE INDEX IF NOT EXISTS idx_follow_ups_next ON follow_ups(next_follow_up);

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
