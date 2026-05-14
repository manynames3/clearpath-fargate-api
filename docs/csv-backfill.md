# CSV Backfill

CSV import is the historical ingestion path. GoHighLevel webhooks keep new lead activity current, but CSV backfill lets the dashboard start with existing paid lead history from provider exports.

## Product Role

Use CSV import when:

- importing old paid lead purchases before the GHL webhook is connected
- testing source ROI with real historical provider data
- reconciling provider exports that did not originate in GHL
- refreshing cost/source metadata from a spreadsheet

Use GHL webhooks when:

- a new paid lead enters the CRM
- a lead moves to contacted, appointment, offer, contract, closed, or dead
- the analytics layer needs live workflow timestamps

Both paths write into the same PostgreSQL tables: `leads`, `properties`, `lead_sources`, `lead_outcomes`, `lead_scores`, and `webhook_events`.

## Dashboard Import

Open `/dashboard` and use the **CSV Backfill** panel:

1. Enter a default source/provider name, such as `ISTL Leads 2`.
2. Enter cost per lead if the file does not already include a cost column.
3. Choose a `.csv` file.
4. Click **Import CSV**.

The dashboard refreshes after import and the new rows appear in source ROI, funnel, stale leads, and the all-leads table.

## API Import

```bash
curl -X POST "http://localhost:8000/api/imports/leads/csv?source=ISTL%20Leads%202&cost_per_lead_dollars=55" \
  -H "Content-Type: text/csv" \
  --data-binary @leads.csv
```

Response:

```json
{
  "provider": "csv-backfill",
  "source": "ISTL Leads 2",
  "dry_run": false,
  "rows_received": 42,
  "imported": 42,
  "failed": 0,
  "source_cost_updates": 42,
  "sample_lead_ids": ["..."],
  "errors": []
}
```

Dry run:

```bash
curl -X POST "http://localhost:8000/api/imports/leads/csv?source=ISTL%20Leads%202&dry_run=true" \
  -H "Content-Type: text/csv" \
  --data-binary @leads.csv
```

## Supported Columns

The importer accepts common provider/export column names and maps them into the same normalized payload used by the GHL webhook receiver.

| CSV concept | Accepted examples |
|---|---|
| External ID | `id`, `lead_id`, `provider_lead_id`, `external_id`, `contact_id`, `ghl_id` |
| Source/provider | `source`, `lead_source`, `provider`, `vendor`, `lead_provider` |
| Name | `First Name`, `Last Name`, `first_name`, `last_name` |
| Contact | `Phone`, `Standard Seller Number`, `Email`, `E-mail (entered by seller)` |
| Property | `Property Address`, `City`, `State`, `ZIP code`, `County`, `APN` |
| Motivation | `Seller motivation`, `situation`, `repair_scope`, `listing_status`, `selling_urgency` |
| Lifecycle | `status`, `stage`, `lifecycle_stage`, `outcome` |
| Cost | `cost_per_lead`, `lead_cost`, `cpl` |

If no external ID is provided, the importer creates a stable `csv-...` ID from source, phone/email, and property address. Re-importing the same file updates the same lead instead of creating a second row.

## Boundary

CSV import is not meant to replace live workflow events. It is for backfill and reconciliation. Once the baseline is loaded, GHL should send the ongoing lead and lifecycle events so source ROI and stale-lead reporting stay current without spreadsheet maintenance.
