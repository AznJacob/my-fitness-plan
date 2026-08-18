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
nutrition fields used by the generation and lifecycle views.

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

## Stage 10.2 React lifecycle

The authenticated React application exposes two additional browser-history routes:

- `/plans` loads the signed-in user's persisted history, calls out the current active plan, and
  links to every inactive, active, or archived plan.
- `/plans/{plan_id}` reloads the complete persisted plan and generation snapshot from the API. It
  allows an inactive plan to become active and allows any non-archived plan to be archived.

`/plans/new` still reviews the current profile before generation, but its successful response now
links directly to the saved plan detail. The history and detail views do not depend on in-memory
generation state, so a page refresh or a direct detail URL restores the data from PostgreSQL through
the authenticated API. Mutations use the existing credentialed, CSRF-protected client. The browser
never supplies user ownership, and the detail view uses the backend's indistinguishable not-found
response for unknown and other-user plan identifiers.

Status controls follow the backend lifecycle contract rather than inventing client-only behavior.
Only inactive plans show the active-selection action. Archived plans are readable but terminal, and
the interface confirms that consequence before sending an archive request. Archiving an active plan
intentionally leaves the user with no active plan.

## Stage 10.3 final verification

The complete workflow is verified against an isolated migrated PostgreSQL database with Claude
replaced by a deterministic mock. This exercises user ownership, safety calculations, validated
generation, persistence, history and detail restoration, active-plan replacement, terminal
archiving, and immutable profile snapshots without consuming API credits. It also verifies that a
second authenticated user receives the same not-found result for another user's plan as for an
unknown plan, and that generation, activation, archiving, and logout reject missing or mismatched
session-bound CSRF proof.

Authentication coverage verifies session restoration through `/auth/me`, fresh sessions after
login, server-side revocation and cookie removal during logout, and rejection of expired, revoked,
malformed, or unknown sessions. Migration checks build the schema from an empty database and test
the existing-plan backfill. The frontend production build covers the routed history/detail types,
and the running Vite service returns the application shell for direct `/plans` and
`/plans/{plan_id}` requests so refreshes can restore API-backed state.

No paid Claude request is part of this verification. Provider behavior remains covered through
mocks, including invalid output and failure states.

## Current limitations

Milestone 10 completes the local working-version lifecycle. Styling remains deliberately
lightweight and can be refined separately without changing persistence or authorization behavior.
The application has not undergone production security review, deployment hardening, operational
monitoring, or real-world load testing.

Research retrieval, pgvector, source attribution, and citations remain unimplemented. Persisted
plans contain no claimed research citations. This local working version is not production-ready.
