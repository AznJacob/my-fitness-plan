# Milestone 10 plan persistence and lifecycle

## Stage 10.1 persistence model

`POST /plans/generate` now persists the result in the same request transaction after the complete
Milestone 9 workflow succeeds. Provider output is never written before JSON decoding, strict
Pydantic validation, schedule validation, and the generated-content wellness assessment have all
completed.

Each stored plan contains:

- lifecycle metadata and authenticated user ownership;
- the validated title, overview, schema version, workout plan, and nutrition plan;
- the exact validated profile used for generation; and
- the versioned deterministic calculation result supplied to Claude.

The snapshot is independent of the user's current profile. Later profile edits therefore do not
rewrite the historical inputs associated with an existing plan. The generation response adds plan
identity, status, snapshot, and timestamps while retaining the existing top-level workout and
nutrition fields, so the Stage 9 React result remains compatible until Stage 10.2 adds lifecycle
views.

Revision `c7e91a4b2d65` adds the missing non-null `overview` column to `plans`. The initial schema
already contained the remaining ownership, JSON, status, archive timestamp, and partial unique
index structures. Existing pre-migration rows receive a neutral legacy overview during migration;
the default is removed immediately so all new application writes must supply validated content.

## Protected API contract

- `POST /plans/generate` generates, validates, persists, and returns a new inactive plan.
- `GET /plans` returns the authenticated user's plan history, newest first.
- `GET /plans/{plan_id}` returns the complete owned plan and generation snapshot.
- `POST /plans/{plan_id}/activate` selects the owned non-archived plan as the user's only active
  plan.
- `POST /plans/{plan_id}/archive` archives an owned plan, including an active plan.

Read endpoints require authentication. Generation, activation, and archiving additionally require
the existing origin- and session-bound CSRF proof. No endpoint accepts a user ID. A plan belonging
to another user returns the same `404 plan_not_found` response as an unknown identifier, avoiding
resource enumeration.

## Lifecycle and transaction rules

New plans start as `inactive`; generation does not silently replace the user's active selection.
Activation takes a PostgreSQL row lock on the owning user, demotes any currently active plan, and
activates the selected plan in one request transaction. This serializes concurrent lifecycle
changes for that user. The existing partial unique index on `plans.user_id WHERE status = 'active'`
remains the database-level final guarantee that a user has at most one active plan.

Archiving is idempotent and sets `archived_at`. If the plan was active, the user is left with no
active plan. Archived plans cannot become active again; they remain readable for history and audit
context. This terminal rule keeps lifecycle meaning simple and avoids silently reviving an old
profile snapshot.

## Current limitations

Stage 10.1 exposes backend persistence and lifecycle APIs only. The current React generation view
still displays the returned plan in memory and does not yet load history, details, active status, or
archived status after refresh. Those views and actions belong to Stage 10.2.

Research retrieval, pgvector, source attribution, and citations remain unimplemented. Persisted
plans contain no claimed research citations. This local working version is not production-ready.
