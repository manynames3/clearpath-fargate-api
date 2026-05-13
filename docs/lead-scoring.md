# Lead Scoring

Clearpath lead scoring is intentionally rule-based and explainable. It is not trying to
predict close probability from a black-box model. The goal is to turn paid-lead provider
fields into a consistent review queue and source-quality report.

## What The Score Uses

Basic contact completeness is not part of the lead score. The paid-lead provider is
expected to send phone, email, and property address on every row, so those fields are
treated as ingestion requirements rather than scoring differentiators.

The score is driven by fields that affect acquisition priority:

| Signal | Examples | Effect |
|---|---|---|
| Urgency | `ASAP`, `urgent`, `30 days`, `60-90 days` | Higher urgency raises priority |
| Motivation | inherited, tax delinquent, foreclosure, probate, tired landlord | Strong distress signals raise priority |
| Occupancy | vacant, tenant occupied, owner occupied | Vacant properties score higher |
| Seller type | owner, agent, wholesaler | Owner direct is preferred; non-owner records require review |
| Listing status | not listed, listed, under contract | Off-market leads score higher |
| Repair scope | major remodel, deferred maintenance, cosmetic, turnkey | Larger repair needs raise priority |
| Property type | single family, condo, land, mobile home | Single-family properties are preferred |
| Ownership length | `15-19 years`, `10-14 years` | Longer ownership adds a small signal |
| County/ZIP | provider county, resolved address county, ZIP | Enables market context and provider reporting |

The score is capped between `0` and `100`. Current priority bands:

| Score | Priority |
|---|---|
| `80+` | `high` |
| `60-79` | `medium` |
| `<60` | `low` |
| Data-quality issue | `review` |

## Provider Field Mapping

The webhook parser accepts both API-style field names and human-readable provider labels.
For example, these provider fields map into normalized columns:

| Provider field | Stored field |
|---|---|
| `Standard Seller Number` | `leads.phone` |
| `E-mail (entered by seller)` | `leads.email` |
| `Property Address` | `properties.address` |
| `ZIP code` | `properties.zip` |
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

Full state names such as `Georgia` are normalized to two-letter codes such as `GA`.

## County Resolution

County Performance does not assume the county is already present in the address field.
During webhook ingestion and CSV backfill, the API resolves county in this order:

1. Use an explicit provider/GHL county field when supplied.
2. Use the property address with the U.S. Census geocoder when geocoding is enabled.
3. Fall back to a ZIP-to-county crosswalk for known operating ZIP codes.

The normalized county is written to both `leads.county` and `properties.county`, so
dashboard grouping and `/api/intelligence/county-performance` sort on structured data
instead of parsing display addresses. The property record also stores
`county_resolution_method` and `county_resolution_confidence` so lower-confidence ZIP
matches can be distinguished from provider-supplied or address-geocoded matches.

## Backfilling Existing Leads

The system does not need to wait for only future webhook traffic. Existing GHL, provider,
or Notion exports can be imported from CSV and scored with the same ingestion path used by
webhooks.

For Excel workbooks, export the lead sheet to CSV first. The importer intentionally reads a
flat CSV so the backfill path stays lightweight and does not add spreadsheet libraries to
the production container.

Local example:

```bash
ENVIRONMENT=local \
DATABASE_URL=sqlite+aiosqlite:///./clearpath-local.db \
LOCAL_CREATE_TABLES=true \
PYTHONPATH=app \
.venv/bin/python scripts/import_existing_leads.py \
  --csv ~/Downloads/existing-leads.csv \
  --source "Main Lead Provider"
```

Dry run:

```bash
ENVIRONMENT=local \
DATABASE_URL=sqlite+aiosqlite:///./clearpath-local.db \
LOCAL_CREATE_TABLES=true \
PYTHONPATH=app \
.venv/bin/python scripts/import_existing_leads.py \
  --csv ~/Downloads/existing-leads.csv \
  --source "Main Lead Provider" \
  --dry-run
```

The importer generates a stable CSV contact id when no GHL id exists by hashing phone,
email, and property address. That makes repeated imports idempotent for the same source
data.

## Next Scoring Upgrade

The next useful upgrade is market context. Redfin/Census-derived ZIP or county metrics can
add signals such as median sale price, days on market, inventory pressure, income context,
and market competitiveness. Those should be loaded into PostgreSQL as cached monthly data,
then joined to leads by ZIP/county during scoring.
