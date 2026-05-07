# GoHighLevel Integration

Clearpath ingests GoHighLevel contact events through `POST /webhooks/ghl`. The current implementation is intentionally webhook-first: GHL sends lead/contact data to this API, and the API upserts the lead plus property details into PostgreSQL. The app does not call the GHL API yet.

## Recommended Portfolio Setup

For this project stage, use a GoHighLevel Workflow Custom Webhook action. It is the simplest fit because Clearpath only needs outbound contact data from GHL into the API.

1. Create or edit a GHL workflow for new motivated-seller leads.
2. Add a Custom Webhook action.
3. Set method to `POST`.
4. Set the URL to the deployed endpoint:

```text
https://api.clearpathpropertygroup.com/webhooks/ghl
```

5. Send JSON with the mapped contact and property fields.
6. Add a shared secret header if enabled:

```text
X-Clearpath-Webhook-Secret: <secret value from Secrets Manager>
```

GHL custom workflow webhooks can send mapped values from contact fields, custom fields, and workflow context. The official HighLevel custom webhook support article is useful for configuring the workflow action: https://help.gohighlevel.com/support/solutions/articles/155000003305/

## Payload Contract

The API accepts the local demo shape:

```json
{
  "contact_id": "abc123",
  "first_name": "Jordan",
  "last_name": "Carter",
  "phone": "+14045550199",
  "email": "jordan@example.com",
  "source": "sms",
  "status": "warm",
  "custom_fields": {
    "property_address": "25 Demo Ridge",
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
  "source": "facebook",
  "status": "warm",
  "customFields": [
    { "key": "property_address", "field_value": "25 Demo Ridge" },
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
| `source` | `leads.source` |
| `status` | `leads.status` |
| `custom_fields.county` or `customFields[].key=county` | `leads.county`, `properties.county` |
| `custom_fields.property_address` or `customFields[].key=property_address` | `properties.address` |
| `custom_fields.city` | `properties.city` |
| `custom_fields.state` | `leads.state`, `properties.state` |
| `custom_fields.zip` | `properties.zip` |
| `custom_fields.situation` | `properties.situation` |

## Signature Model

The portfolio deployment uses a shared HMAC secret stored in Secrets Manager. Terraform creates the secret container at `clearpath/dev/ghl-webhook`, but the value is loaded out-of-band so it never lands in Terraform state.

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
    "id": "contact_demo_001",
    "firstName": "Jordan",
    "lastName": "Carter",
    "phone": "+14045550199",
    "source": "sms",
    "status": "warm",
    "customFields": [
      { "key": "property_address", "field_value": "25 Demo Ridge" },
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

## Later GHL API Work

If Clearpath needs two-way CRM sync later, add a separate GHL API client with:

- OAuth or private integration token storage in Secrets Manager
- scoped outbound calls for contact updates and opportunity status
- retries and dead-letter handling for failed CRM writes
- explicit rate-limit handling

That is intentionally out of scope for this portfolio build because the current business requirement is inbound lead capture, not full CRM synchronization.
