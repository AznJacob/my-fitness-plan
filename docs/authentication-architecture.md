# Authentication architecture

This document records the security design for milestone 5. It is an implementation contract, not
a claim that authentication is complete or production-ready.

## Trust boundaries

`users` is the application-owned account. Each `authentication_identities` row records a sign-in
method and maps it to one user. The backend, never the browser, decides which user an authenticated
identity owns. Authentication proves who a caller is; authorization separately decides what that
authenticated user may access.

## Application-controlled sessions

Both password and Google sign-in establish the same database-backed opaque session. The backend
will generate at least 256 random bits with Python's `secrets` module. The raw token is returned only
in a cookie; PostgreSQL stores only its SHA-256 digest. A fast digest is appropriate because this
token is uniformly random and unguessable. Human-chosen passwords require a deliberately slow,
memory-hard Argon2id hash instead.

Sessions have a seven-day absolute lifetime and do not slide on activity. Logout revokes the current
session in PostgreSQL and clears its cookies. Multiple devices may hold independent sessions. A
session is rejected when its token is missing, malformed, unknown, expired, or revoked. Automated
cleanup of old rows is deferred until production operations work.

## Cookies, CORS, and CSRF

The single supported local configuration uses an `mfp_session` cookie with `Path=/`, `HttpOnly`,
`SameSite=Lax`, and no `Domain` attribute. `Secure` is disabled because the current application is
served over local HTTP; JavaScript still cannot read the session cookie. React sends requests with
`credentials: "include"` and never copies the session token into JavaScript storage. Any future
HTTPS deployment must set `SESSION_COOKIE_SECURE=true` before it can be considered safe.

SameSite is defense in depth rather than the only CSRF control. Before authentication, a CSRF
bootstrap endpoint will issue a random non-HttpOnly cookie; registration, login, and Google sign-in
require the identical value in `X-CSRF-Token` (the double-submit pattern). After authentication, a
fresh CSRF token replaces it, its digest is stored with the new session, and unsafe authenticated
requests must echo the raw cookie value in the same header. The backend will also require an exact
allowed `Origin`. Logout and all later state-changing endpoints use these protections; safe HTTP
methods never change state. Authentication and protected responses use `Cache-Control: no-store`.

CORS permits credentials only for configured exact frontend origins. Wildcard origins, methods, and
headers are not used. The current application permits both `http://localhost:5173` and
`http://127.0.0.1:5173`. The API will explicitly allow only the methods and headers it needs,
including `Content-Type` and `X-CSRF-Token`.

## Session expiration and rotation

Successful registration or sign-in creates fresh session and CSRF tokens. Authentication never
accepts a caller-supplied session identifier, which prevents session fixation. This milestone uses
an absolute expiration rather than refresh tokens or rotating sliding sessions because it is easier
to audit and revoke for this portfolio application.

## Database transaction boundary

FastAPI creates one synchronous SQLAlchemy `Session` for each request that declares the database
dependency. A successful route commits once; an exception or commit failure rolls back; cleanup
always closes the session. The dependency uses function scope so transaction completion occurs
before the response is sent. Route handlers delegate queries and mutations to services and do not
own commit or rollback. Services may call `flush()` when they need database-generated values or
early constraint detection while keeping the request atomic.

The SQLAlchemy session factory is created once from the application engine during FastAPI startup
and stored in application state. The factory is safe to reuse; each produced `Session` is not and is
therefore confined to one request.

## Password authentication

Email input will be validated and normalized before lookup. Passwords will be hashed with a vetted
Argon2id implementation and never stored or logged in plaintext. Login will perform a dummy password
hash verification when no password identity exists and return the same generic failure for an
unknown email and a wrong password, reducing account-enumeration and timing signals.

## Google identity policy

The frontend will use Google Identity Services and send its ID token to FastAPI. The backend will
use Google's supported Python library to validate signature, audience, issuer, expiration, verified
identity claims, and the immutable `sub`. Only `(provider="google", provider_subject=sub)` identifies
a returning Google user; an email address is not a stable provider identifier.

Matching emails never cause automatic linking:

- An existing Google `sub` signs in to its existing user.
- A new Google `sub` with an unclaimed normalized email creates a user and Google identity in one
  transaction.
- A new Google `sub` whose normalized email is already claimed is rejected without creating data.
- Password registration whose normalized email is already claimed by any provider is also rejected.
- Responses do not reveal which provider owns an existing email.

Secure identity linking requires an authenticated session plus reauthentication and belongs to
milestone 6. To make concurrent cross-provider registrations safe at the database boundary, stage 2
adds a required, unique canonical normalized email to `users`. Every identity linked to a user must
represent that canonical email. The service layer will still perform friendly pre-insert collision
checks, while the unique constraint is the final defense against races.

## Typed configuration

The backend validates exact CORS origins, a bounded session lifetime, the cookie `Secure` flag, and
an optional Google client ID at startup. The settings model stays focused on values the application
actually consumes. Secrets and connection strings are excluded from settings representations.
Google configuration remains optional until stage 8 so the earlier password-authentication stages
can run independently.

## Deferred production protections

Milestone 5 will not by itself make authentication production-ready. Deployment work still needs
TLS termination and trusted-proxy configuration, rate limiting, credential-stuffing monitoring,
secret rotation, session-row retention/cleanup, security headers, dependency and image scanning,
audit logging that excludes credentials, alerting, backups, and an incident-response process.
