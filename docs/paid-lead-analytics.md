# Paid Lead Analytics V2

Clearpath Lead Intelligence API is positioned as a GHL-connected paid lead analytics dashboard for real estate acquisitions teams. It is not a CRM replacement and it is not an Airtable clone.

## Product Boundary

GoHighLevel remains responsible for lead intake, pipeline stages, texting/calling, follow-up sequences, notifications, and existing Notion handoff workflows.

This service owns the reporting layer that GHL and spreadsheets do not handle cleanly:

- normalize paid-lead provider fields into one schema
- track lead lifecycle outcomes over time
- attach source cost inputs to each provider
- calculate source ROI through the acquisition funnel
- surface stale leads that have not moved recently
- keep raw webhook events for audit/debugging

## Why This Beats Excel/GHL Alone

Excel can calculate ROI after the data has already been exported, cleaned, reconciled, and updated by hand. GHL can run follow-up workflows, but it is not designed for cross-provider cost attribution.

The useful automation here is the pipeline:

```text
GHL/provider event -> normalized lead/property/source record -> lifecycle outcome history -> ROI analytics dashboard
```

That matters when there are multiple paid providers with different field names, different lead costs, and different conversion quality.

## Lifecycle Stages

The analytics layer tracks these stages:

| Stage | Meaning |
|---|---|
| `received` | Lead entered the system from GHL, CSV backfill, or provider import |
| `contacted` | Someone reached or attempted to reach the seller |
| `appointment` | A property walkthrough or seller appointment was set |
| `offer` | An offer was made |
| `contract` | Deal went under contract |
| `closed` | Deal closed |
| `dead` | Lead is no longer active; optional dead reason can be stored |

The endpoint `PATCH /api/leads/{lead_id}/outcome` appends outcome history and updates the lead's current status.

## Source ROI

Source ROI uses `lead_sources.cost_per_lead_cents` as the current cost input. This keeps V2 practical: a source cost can be entered manually or updated from a provider invoice/import without building a full billing system.

The endpoint `GET /api/analytics/source-roi` returns:

- total leads by source
- estimated spend
- contacted, appointment, offer, contract, closed, and dead counts
- appointment, offer, contract, and close rates
- cost per appointment
- cost per contract
- cost per closed deal

This is the core product value because it answers: which paid source is worth buying again?

## Stale Lead Detection

`GET /api/analytics/stale-leads?days=7` returns active leads whose latest explicit lifecycle/follow-up activity is older than the threshold.

This is not a replacement for GHL reminders. It is an analytics guardrail that shows operational leakage by source: leads were purchased, but did not move through the funnel.

## Dashboard

`/dashboard` is the operator-facing product surface. It shows:

- source ROI scorecard
- acquisition funnel
- stale lead queue
- filterable all-leads table
- county market context as supporting information

Market context stays secondary. The primary product is paid lead source performance.

## Current Limits

- Cost input is source-level cost per lead, not invoice-level campaign accounting.
- Outcome tracking depends on GHL workflow events, CSV updates, or manual/API updates being recorded consistently.
- Scoring is rules-based and explainable; it is not ML.
- Dashboard access is protected through the API key used by data endpoints when `CLEARPATH_API_KEY_SECRET` is configured. A production tenant/team auth layer would be a later product concern.
