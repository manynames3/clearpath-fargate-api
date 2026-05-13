INSERT INTO lead_sources (name, vendor_name, channel, cost_per_lead_cents)
VALUES
    ('paid-lead-vendor-a', 'Vendor A', 'paid-lead-provider', 8500),
    ('facebook', 'Meta', 'paid-social', 4200),
    ('direct', 'Direct', 'organic', 0)
ON CONFLICT (name) DO NOTHING;

INSERT INTO leads (ghl_id, first_name, last_name, phone, email, status, source, county, state)
VALUES
    ('sample-ghl-001', 'John', 'Smith', '+14045550100', 'john.smith@example.com', 'warm', 'paid-lead-vendor-a', 'Gwinnett', 'GA'),
    ('sample-ghl-002', 'Maria', 'Johnson', '+16785550125', 'maria.johnson@example.com', 'hot', 'facebook', 'Cobb', 'GA'),
    ('sample-ghl-003', 'Angela', 'Brown', '+17705550199', 'angela.brown@example.com', 'new', 'direct', 'Fulton', 'GA'),
    ('sample-ghl-004', 'Caleb', 'Ward', '+14045550104', 'caleb.ward@example.com', 'warm', 'paid-lead-vendor-a', 'Gwinnett', 'GA')
ON CONFLICT (ghl_id) DO NOTHING;

UPDATE leads
SET source_id = lead_sources.id
FROM lead_sources
WHERE leads.source = lead_sources.name
  AND leads.source_id IS NULL;

INSERT INTO properties (
    lead_id, address, city, county, county_resolution_method, county_resolution_confidence,
    state, zip, estimated_value, situation,
    occupancy, selling_urgency, seller_type, listing_status, repair_scope,
    property_type, years_owned, apn
)
SELECT id, '123 Main St', 'Lawrenceville', 'Gwinnett', 'provider', 100,
       'GA', '30046', 285000, 'inherited',
       'Vacant', 'ASAP', 'Owner', 'Not listed', 'Major remodel: kitchen, bathroom, roof',
       'Single family', '15-19 years', 'sample-apn-001'
FROM leads WHERE ghl_id = 'sample-ghl-001'
ON CONFLICT DO NOTHING;

INSERT INTO properties (
    lead_id, address, city, county, county_resolution_method, county_resolution_confidence,
    state, zip, estimated_value, situation,
    occupancy, selling_urgency, seller_type, listing_status, repair_scope,
    property_type, years_owned, apn
)
SELECT id, '44 Pine Ridge Dr', 'Marietta', 'Cobb', 'provider', 100,
       'GA', '30060', 410000, 'vacant',
       'Vacant', '30 days', 'Owner', 'Not listed', 'Deferred maintenance',
       'Single family', '10-14 years', 'sample-apn-002'
FROM leads WHERE ghl_id = 'sample-ghl-002'
ON CONFLICT DO NOTHING;

INSERT INTO properties (
    lead_id, address, city, county, county_resolution_method, county_resolution_confidence,
    state, zip, estimated_value, situation,
    occupancy, selling_urgency, seller_type, listing_status, repair_scope,
    property_type, years_owned, apn
)
SELECT id, '411 Cascade Ave', 'Atlanta', 'Fulton', 'provider', 100,
       'GA', '30310', 310000, 'tax-delinquent',
       'Owner occupied', 'Soon', 'Owner', 'Not listed', 'Cosmetic repairs',
       'Single family', '5-9 years', 'sample-apn-003'
FROM leads WHERE ghl_id = 'sample-ghl-003'
ON CONFLICT DO NOTHING;

INSERT INTO properties (
    lead_id, address, city, county, county_resolution_method, county_resolution_confidence,
    state, zip, estimated_value, situation,
    occupancy, selling_urgency, seller_type, listing_status, repair_scope,
    property_type, years_owned, apn
)
SELECT id, '77 Beaver Ruin Rd', 'Norcross', 'Gwinnett', 'provider', 100,
       'GA', '30071', 305000, 'deferred-maintenance',
       'Tenant occupied', '60-90 days', 'Owner', 'Not listed', 'Major remodel',
       'Single family', '15-19 years', 'sample-apn-004'
FROM leads WHERE ghl_id = 'sample-ghl-004'
ON CONFLICT DO NOTHING;

INSERT INTO follow_ups (lead_id, method, notes, next_follow_up)
SELECT id, 'sms', 'Seller asked for a call next week.', CURRENT_DATE + INTERVAL '7 days'
FROM leads WHERE ghl_id = 'sample-ghl-001'
ON CONFLICT DO NOTHING;

INSERT INTO lead_scores (lead_id, score, priority, reasons, needs_review)
SELECT id, 96, 'high', '["Status is warm", "Urgency signal: ASAP", "Motivation signal: inherited", "Property is vacant", "Property is not listed"]'::jsonb, TRUE
FROM leads WHERE ghl_id = 'sample-ghl-001'
ON CONFLICT (lead_id) DO UPDATE SET score = EXCLUDED.score, priority = EXCLUDED.priority, reasons = EXCLUDED.reasons, needs_review = EXCLUDED.needs_review;

INSERT INTO lead_scores (lead_id, score, priority, reasons, needs_review)
SELECT id, 86, 'high', '["Status is hot", "Near-term urgency: 30 days", "Property is vacant", "Repair need: Deferred maintenance"]'::jsonb, TRUE
FROM leads WHERE ghl_id = 'sample-ghl-002'
ON CONFLICT (lead_id) DO UPDATE SET score = EXCLUDED.score, priority = EXCLUDED.priority, reasons = EXCLUDED.reasons, needs_review = EXCLUDED.needs_review;

INSERT INTO lead_scores (lead_id, score, priority, reasons, needs_review)
SELECT id, 82, 'medium', '["Status is new", "Motivation signal: tax-delinquent", "Property is not listed"]'::jsonb, TRUE
FROM leads WHERE ghl_id = 'sample-ghl-003'
ON CONFLICT (lead_id) DO UPDATE SET score = EXCLUDED.score, priority = EXCLUDED.priority, reasons = EXCLUDED.reasons, needs_review = EXCLUDED.needs_review;

INSERT INTO lead_scores (lead_id, score, priority, reasons, needs_review)
SELECT id, 78, 'medium', '["Status is warm", "Medium-term urgency: 60-90 days", "Repair scope: Major remodel"]'::jsonb, TRUE
FROM leads WHERE ghl_id = 'sample-ghl-004'
ON CONFLICT (lead_id) DO UPDATE SET score = EXCLUDED.score, priority = EXCLUDED.priority, reasons = EXCLUDED.reasons, needs_review = EXCLUDED.needs_review;

INSERT INTO webhook_events (provider, external_id, lead_id, event_type, payload)
SELECT 'gohighlevel', ghl_id, id, 'contact', jsonb_build_object('contact_id', ghl_id, 'source', source)
FROM leads
WHERE ghl_id IN ('sample-ghl-001', 'sample-ghl-002', 'sample-ghl-003', 'sample-ghl-004')
  AND NOT EXISTS (
      SELECT 1 FROM webhook_events WHERE webhook_events.external_id = leads.ghl_id
  );

INSERT INTO market_snapshots (county, state, median_price, avg_dom, snapshot_date)
VALUES
    ('Gwinnett', 'GA', 385000, 21, CURRENT_DATE),
    ('Cobb', 'GA', 430000, 18, CURRENT_DATE),
    ('Fulton', 'GA', 465000, 24, CURRENT_DATE)
ON CONFLICT (county, state, snapshot_date) DO NOTHING;
