# Milestone 6 architecture

Milestone 6 originally added planning-profile persistence and explicit identity linking. The
current application retains the identity-linking boundary while later product work replaced the
saved planning profile with private account details and per-request plan preferences.

## Current account-details ownership and validation

`GET /account/details` and `PUT /account/details` never accept a user ID. FastAPI resolves the
HttpOnly session and derives the account-details primary key from its application user. `PUT`
creates the one-to-one row when absent and replaces username, height, and weight when present.

Pydantic and PostgreSQL both constrain username length and plausible height and weight ranges.
Planning goals, availability, equipment, dietary preferences, and wellness constraints are no
longer persisted in this row; they are validated with each generation request.

The account screen calls `GET /account/details` on mount. A `404` selects empty defaults; an existing
response populates the form. The shared API client includes the HttpOnly session automatically and
echoes only the JavaScript-readable CSRF cookie in `X-CSRF-Token`.

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
