# ADR 0006: Use PostgreSQL as the Lead Intelligence Source of Truth

Date: 2026-05-12

Status: Accepted

## Context

GoHighLevel already owns the CRM workflow: pipeline stages, follow-up sequences, notifications, and the existing Notion handoff. The missing capability is paid-lead analytics: provider field normalization, source cost attribution, lifecycle outcome history, and stale lead visibility across paid lead vendors.

The main storage options were GHL custom fields, Notion, or the API's own database.

## Decision

Use PostgreSQL as the source of truth for lead intelligence and expose the results through API endpoints plus a read-focused internal dashboard.

## Rationale

PostgreSQL fits the data shape: raw webhook events join to normalized leads, properties, source metadata, lifecycle outcomes, lead scores, and market snapshots. Those relationships are awkward to maintain in GHL custom fields or Notion databases, especially when the goal is source accountability and historical reporting.

Notion remains useful as a downstream operating board, but it should receive compact summaries only. GHL can receive small operational flags later, but neither system should be the primary analytics store for cost-per-appointment, cost-per-contract, cost-per-close, or stale lead analysis.

## Consequences

- The API now owns the analytics data model, lifecycle outcome history, and reporting endpoints.
- `/dashboard` provides a human-facing view without requiring a separate frontend deployment.
- GHL remains the sales automation system, not the reporting backend.
- Notion remains optional downstream visibility, not the source of truth.
- Future integrations can push summaries outward without losing the PostgreSQL audit trail.
