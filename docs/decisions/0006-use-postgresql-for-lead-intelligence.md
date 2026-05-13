# ADR 0006: Use PostgreSQL as the Lead Intelligence Source of Truth

Date: 2026-05-12

Status: Accepted

## Context

GoHighLevel already owns the CRM workflow: pipeline stages, follow-up sequences, notifications, and the existing Notion handoff. The missing capability is paid-lead intelligence: provider/source performance, explainable lead scoring, county trends, market context, and lightweight data-quality checks.

The main storage options were GHL custom fields, Notion, or the API's own database.

## Decision

Use PostgreSQL as the source of truth for lead intelligence and expose the results through API endpoints plus a read-focused internal dashboard.

## Rationale

PostgreSQL fits the data shape: raw webhook events join to normalized leads, properties, source metadata, lead scores, quality checks, and market snapshots. Those relationships are awkward to maintain in GHL custom fields or Notion databases, especially when the goal is source accountability and historical reporting.

Notion remains useful as a downstream operating board, but it should receive compact summaries only. GHL can receive small operational flags later, such as score, market-fit label, source quality signal, or review priority. Neither system should be the primary analytics store.

## Consequences

- The API now owns the intelligence data model and reporting endpoints.
- `/dashboard` provides a human-facing view without requiring a separate frontend deployment.
- GHL remains the sales automation system, not the reporting backend.
- Notion remains optional downstream visibility, not the source of truth.
- Future integrations can push summaries outward without losing the PostgreSQL audit trail.
