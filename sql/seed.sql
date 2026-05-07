INSERT INTO leads (ghl_id, first_name, last_name, phone, email, status, source, county, state)
VALUES
    ('demo-ghl-001', 'John', 'Smith', '+14045550100', 'john.smith@example.com', 'warm', 'sms', 'Gwinnett', 'GA'),
    ('demo-ghl-002', 'Maria', 'Johnson', '+16785550125', 'maria.johnson@example.com', 'hot', 'facebook', 'Cobb', 'GA'),
    ('demo-ghl-003', 'Angela', 'Brown', '+17705550199', 'angela.brown@example.com', 'new', 'direct', 'Fulton', 'GA')
ON CONFLICT (ghl_id) DO NOTHING;

INSERT INTO properties (lead_id, address, city, county, state, zip, estimated_value, situation)
SELECT id, '123 Main St', 'Lawrenceville', 'Gwinnett', 'GA', '30046', 285000, 'inherited'
FROM leads WHERE ghl_id = 'demo-ghl-001'
ON CONFLICT DO NOTHING;

INSERT INTO properties (lead_id, address, city, county, state, zip, estimated_value, situation)
SELECT id, '44 Pine Ridge Dr', 'Marietta', 'Cobb', 'GA', '30060', 410000, 'vacant'
FROM leads WHERE ghl_id = 'demo-ghl-002'
ON CONFLICT DO NOTHING;

INSERT INTO follow_ups (lead_id, method, notes, next_follow_up)
SELECT id, 'sms', 'Seller asked for a call next week.', CURRENT_DATE + INTERVAL '7 days'
FROM leads WHERE ghl_id = 'demo-ghl-001'
ON CONFLICT DO NOTHING;

INSERT INTO market_snapshots (county, state, median_price, avg_dom, snapshot_date)
VALUES
    ('Gwinnett', 'GA', 385000, 21, CURRENT_DATE),
    ('Cobb', 'GA', 430000, 18, CURRENT_DATE),
    ('Fulton', 'GA', 465000, 24, CURRENT_DATE)
ON CONFLICT (county, state, snapshot_date) DO NOTHING;
