# Milestone 6 architecture

Milestone 6 adds profile persistence and explicit identity linking to the application-controlled
user established in milestone 5. It does not generate workout or nutrition plans.

## Profile ownership and validation

`GET /profile` and `PUT /profile` never accept a user ID. FastAPI resolves the HttpOnly session,
loads its application user, and derives the profile primary key from that user. This keeps ownership
outside client control. `PUT` creates the one-to-one profile when absent and replaces its current
values when present.

Pydantic constrains goals, experience levels, availability, list sizes, item lengths, and duplicate
list values before persistence. PostgreSQL repeats the important enum, numeric, and JSON-shape
constraints so invalid rows cannot bypass the API boundary. Profile text remains general-wellness
input and is not treated as medical information or a request for treatment.

The authenticated React view calls `GET /profile` on mount. A `404` selects creation defaults; an
existing response populates the edit form. Both creation and editing use the same `PUT /profile`
request. The shared API client includes the HttpOnly session automatically and echoes only the
JavaScript-readable CSRF cookie in `X-CSRF-Token`.

## Explicit identity linking

Normal registration and login never merge accounts by email. Linking is a separate authenticated
operation:

- A password user adds Google by submitting the current MyFitnessPlan password and a freshly issued
  Google ID token for the same canonical email.
- A Google user adds a password by submitting a new password and a freshly issued Google ID token
  whose immutable subject already belongs to that user.

Both mutations require the active session's CSRF token. Google tokens must be issued within five
minutes. Provider-subject and per-user/provider uniqueness constraints prevent reassignment and
remain the final protection against concurrent requests.

React first loads `GET /auth/methods`, shows connected providers, and renders only the action for
the missing provider. Google Identity Services supplies the fresh token directly to the request
callback. React does not decode, persist, or place that token in component state.

## Session behavior

Linking does not replace the active session. Normal registration and login create independent
session rows; logout revokes only the current row. Revocation uses the later of the application
clock and the database-created session timestamp so small clock differences between processes
cannot violate the session lifecycle constraint.

## Remaining production hardening

This milestone is appropriate for the documented local portfolio environment, not an
internet-facing production claim. Later hardening still includes email verification, account
recovery, rate limiting, credential-stuffing detection, security-event audit logs, session-row
retention and cleanup, TLS and secure cookies, stronger response headers, monitoring, backups,
secret rotation, dependency and image scanning, and incident-response procedures.
