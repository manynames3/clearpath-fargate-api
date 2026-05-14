# GoHighLevel Integration

Clearpath exposes a GoHighLevel-compatible receiver at `POST /webhooks/ghl`. The current implementation is intentionally webhook-first: a configured GHL workflow can send lead/contact data to this API, and the API stores the raw event, upserts the lead plus property details, tracks source/vendor metadata, records lifecycle outcomes, and calculates paid-source ROI in PostgreSQL. The app does not call the GHL API yet.

## Where This Fits

Clearpath's current operating workflow is:

```text
Paid lead provider -> GoHighLevel CRM -> GHL workflows -> Notion / notifications / follow-up sequences
```

This API is an additional workflow action, not a replacement for GHL. GHL continues to own CRM pipelines, automatic follow-up sequences, notifications, and the Notion handoff. Clearpath Lead Intelligence API receives a copy of the lead event so the business has an independent reporting store for paid-lead source accountability, provider field normalization, lifecycle outcomes, stale lead visibility, and source ROI.

The best live proof is a paid-lead-style event already entering GHL, followed by a GHL Workflow Custom Webhook delivery to this API with a `200` response.

## Current Status

The repository includes the receiving endpoint, payload mapping, shared-secret validation, local tests, analytics endpoints, dashboard, and AWS infrastructure needed to accept GHL-style webhook payloads. A live GoHighLevel workflow has not been connected or captured as evidence yet.

To prove the external integration, configure a GHL Workflow Custom Webhook during a future validation window, send a real lead-intake workflow event to the deployed CloudFront URL, and capture the GHL delivery log plus the resulting lead query from this API.

## Recommended Setup

For this project stage, use a GoHighLevel Workflow Custom Webhook action. It is the simplest fit because Clearpath only needs outbound contact data from GHL into the API.

1. Confirm access to the correct GHL account/location.
2. Create or edit the GHL workflow that already runs after a paid lead provider creates a contact.
3. Keep the existing GHL actions for notifications, follow-up sequences, and Notion.
4. Add a second Custom Webhook action that sends the same lead event to Clearpath API.
5. Set method to `POST`.
6. Set the URL to the deployed endpoint. For the default no-domain validation path, read the base URL from Terraform:

```bash
export API_BASE_URL="$(terraform -chdir=terraform/environments/dev output -raw api_base_url)"
echo "$API_BASE_URL/webhooks/ghl"
```

7. Send JSON with the mapped contact, source, and property fields.
8. Add a shared secret header if enabled:

```text
X-Clearpath-Webhook-Secret: <secret value from Secrets Manager>
```

GHL custom workflow webhooks can send mapped values from contact fields, custom fields, and workflow context. The official HighLevel custom webhook support article is useful for configuring the workflow action: https://help.gohighlevel.com/support/solutions/articles/155000003305/

## Trigger Event

Use the same trigger that represents the real paid lead path in the GHL account. Good options:

- `Contact Created` when the paid lead provider creates a new contact in GHL.
- The existing provider-specific workflow trigger, if the account already separates leads by source, tag, pipeline, or campaign.
- `Form Submitted` only if the validation lead is being entered through a GHL form rather than a paid lead provider webhook.

For portfolio evidence, the strongest event is a paid-lead-style test contact from the real intake path, with source/vendor fields visible enough to show why the reporting layer exists. Avoid presenting this as another follow-up workflow; the API is for analytics and source accountability.

## Payload Contract

The API accepts the local sample shape:

```json
{
  "contact_id": "abc123",
  "first_name": "Jordan",
  "last_name": "Carter",
  "phone": "+14045550199",
  "email": "jordan@example.com",
  "source": "paid-lead-vendor-a",
  "status": "warm",
  "custom_fields": {
    "property_address": "25 Sample Ridge",
    "city": "Lawrenceville",
    "county": "Gwinnett",
    "state": "GA",
    "situation": "inherited"
  }
}
```

It also accepts HighLevel-style field names commonly seen in webhook payloads:

```json
{
  "id": "contact_abc123",
  "firstName": "Jordan",
  "lastName": "Carter",
  "phone": "+14045550199",
  "email": "jordan@example.com",
  "source": "paid-lead-vendor-a",
  "status": "warm",
  "customFields": [
    { "key": "property_address", "field_value": "25 Sample Ridge" },
    { "key": "city", "field_value": "Lawrenceville" },
    { "key": "county", "field_value": "Gwinnett" },
    { "key": "state", "field_value": "GA" },
    { "key": "situation", "field_value": "inherited" }
  ]
}
```

Field mapping:

| Incoming field | Stored column |
|---|---|
| `contact_id`, `contactId`, or `id` | `leads.ghl_id` |
| `first_name` or `firstName` | `leads.first_name` |
| `last_name` or `lastName` | `leads.last_name` |
| `phone` | `leads.phone` |
| `email` | `leads.email` |
| `source` | `leads.source`, normally the paid lead vendor, campaign, or channel |
| `status` | `leads.status` |
| `custom_fields.county` or `customFields[].key=county` | `leads.county`, `properties.county`; optional because the API can resolve county from address/ZIP |
| `custom_fields.property_address` or `customFields[].key=property_address` | `properties.address` |
| `custom_fields.city` | `properties.city` |
| `custom_fields.state` | `leads.state`, `properties.state` |
| `custom_fields.zip` | `properties.zip` |
| `custom_fields.situation` | `properties.situation` |
| `Standard Seller Number` | `leads.phone` |
| `E-mail (entered by seller)` | `leads.email` |
| `Who's living in the property?` | `properties.occupancy` |
| `Anyone living in the house?` | `properties.occupancy` |
| `Selling urgency` | `properties.selling_urgency` |
| `How fast they want to sell` | `properties.selling_urgency` |
| `Seller motivation` | `properties.situation` |
| `Seller: owner or agent?` | `properties.seller_type` |
| `Owner or Agent/Wholesaler?` | `properties.seller_type` |
| `Listing status` | `properties.listing_status` |
| `Is your property listed with a real estate agent?` | `properties.listing_status` |
| `Repair scope` | `properties.repair_scope` |
| `What kind of repairs and maintenance does the property NEED?` | `properties.repair_scope` |
| `Property type` | `properties.property_type` |
| `Type of Property` | `properties.property_type` |
| `Years of ownership` | `properties.years_owned` |
| `How long have you owned the property in years?` | `properties.years_owned` |
| `Sold comps` | `properties.estimated_value` |
| `APN` | `properties.apn` |

State names such as `Georgia` are normalized to `GA` before storage. If the lead provider
does not send county, the ingestion path resolves county from the property address first
and falls back to ZIP for known operating areas. The stored property includes
`county_resolution_method` and `county_resolution_confidence` so reporting can show whether
County Performance is based on provider data, address geocoding, or a lower-confidence ZIP
match.

On successful ingestion, the API also writes:

| Intelligence record | Purpose |
|---|---|
| `webhook_events` | Raw delivery audit trail for source accountability and debugging |
| `lead_sources` | Source/vendor/channel metadata for scorecards |
| `lead_outcomes` | Lifecycle history used for source ROI and funnel analytics |
| `lead_scores` | Simple explainable score, priority, and needs-review flag |
| `duplicate_leads` | Optional data-quality guardrail for unusual same-contact or same-property matches |

## Signature Model

The ephemeral deployment uses a shared HMAC secret stored in Secrets Manager. Terraform creates the secret container at `clearpath/dev/ghl-webhook`, but the value is loaded out-of-band so it never lands in Terraform state.

```bash
aws secretsmanager put-secret-value \
  --secret-id clearpath/dev/ghl-webhook \
  --secret-string "$GHL_WEBHOOK_SECRET"
```

When `GHL_WEBHOOK_SECRET` is set in the container environment, the API requires one of these authentication methods:

- `X-Clearpath-Webhook-Secret: <secret>` for GoHighLevel Workflow Custom Webhook setup
- `Authorization: Bearer <secret>` if using GHL's bearer-token header option
- `X-Clearpath-Signature: sha256=<hmac-sha256-body-signature>` for clients that can compute a body HMAC

For a future Marketplace app integration, HighLevel documents signed webhook verification with `X-GHL-Signature` using Ed25519 and legacy `X-WH-Signature` using RSA. That path is separate from the workflow-webhook setup and would be the next security upgrade if Clearpath publishes a Marketplace app. Official reference: https://marketplace.gohighlevel.com/docs/webhook/WebhookIntegrationGuide/

## Local Test

```bash
curl -X POST http://localhost:8000/webhooks/ghl \
  -H "Content-Type: application/json" \
  -H "X-Clearpath-Webhook-Secret: dev-secret-if-enabled" \
  -d '{
    "id": "contact_sample_001",
    "firstName": "Jordan",
    "lastName": "Carter",
    "phone": "+14045550199",
    "source": "paid-lead-vendor-a",
    "status": "warm",
    "customFields": [
      { "key": "property_address", "field_value": "25 Sample Ridge" },
      { "key": "county", "field_value": "Gwinnett" },
      { "key": "state", "field_value": "GA" },
      { "key": "situation", "field_value": "inherited" }
    ]
  }'
```

Then confirm the upsert:

```bash
curl -f "http://localhost:8000/api/leads?county=Gwinnett&status=warm"
```

Confirm the intelligence layer:

```bash
curl -f "http://localhost:8000/api/intelligence/summary"
curl -f "http://localhost:8000/api/analytics/source-roi"
curl -f "http://localhost:8000/api/analytics/funnel"
```

Open the dashboard:

```text
http://localhost:8000/dashboard
```

In the deployed environment, lead queries are protected. Include `X-Clearpath-API-Key` with the value stored in the `clearpath/dev/api-key` Secrets Manager secret.

## Evidence To Capture Later

During a short paid AWS/GHL validation window, capture:

- GHL workflow overview showing the existing CRM/Notion actions plus the Clearpath Custom Webhook action.
- Custom Webhook action showing `POST` to `$API_BASE_URL/webhooks/ghl`; hide the secret header value.
- Workflow execution or delivery log showing the Clearpath webhook returned `200`.
- Protected `/api/leads` query showing the same GHL contact/source/property data stored in PostgreSQL.
- `/api/analytics/source-roi` or `/dashboard` showing the same source included in the paid-lead ROI scorecard.
- `/api/analytics/funnel` or `PATCH /api/leads/{lead_id}/outcome` showing lifecycle outcome tracking.
- Optional Notion screenshot showing the existing workflow still receives the lead, proving the API is additive rather than a replacement.

## Later GHL API Work

If Clearpath needs two-way CRM sync later, add a separate GHL API client with:

- OAuth or private integration token storage in Secrets Manager
- scoped outbound calls for contact updates and opportunity status
- retries and dead-letter handling for failed CRM writes
- explicit rate-limit handling

That is intentionally out of scope for the current build because the current business requirement is inbound lead capture, not full CRM synchronization.
