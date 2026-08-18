# Authentication architecture

This document records the authentication design implemented through milestone 6 for the documented
local portfolio environment. It is not a claim of production readiness.

## Trust boundaries

`users` is the application-owned account. Each `authentication_identities` row records a sign-in
method and maps it to one user. The backend, never the browser, decides which user an authenticated
identity owns. Authentication proves who a caller is; authorization separately decides what that
authenticated user may access.

## Application-controlled sessions

Both password and Google sign-in establish the same database-backed opaque session. The backend
generates 256 random bits with Python's `secrets` module. The raw token is returned only
in a cookie; PostgreSQL stores only its SHA-256 digest. A fast digest is appropriate because this
token is uniformly random and unguessable. Human-chosen passwords require a deliberately slow,
memory-hard Argon2id hash instead.

Sessions have a seven-day absolute lifetime and do not slide on activity. Logout revokes the current
session in PostgreSQL and clears its cookies. The revocation timestamp is never allowed to precede
the database-created session timestamp, which tolerates small clock differences between the
application and PostgreSQL processes. Multiple devices may hold independent sessions. A session is
rejected when its token is missing, malformed, unknown, expired, or revoked. Automated cleanup of
old rows is deferred until production operations work.

## Cookies, CORS, and CSRF

The single supported local configuration uses an `mfp_session` cookie with `Path=/`, `HttpOnly`,
`SameSite=Lax`, and no `Domain` attribute. `Secure` is disabled because the current application is
served over local HTTP; JavaScript still cannot read the session cookie. React sends requests with
`credentials: "include"` and never copies the session token into JavaScript storage. Any future
HTTPS deployment must set `SESSION_COOKIE_SECURE=true` before it can be considered safe.

SameSite is defense in depth rather than the only CSRF control. Before authentication,
`GET /auth/csrf` issues a random non-HttpOnly cookie; registration, login, and Google sign-in
require the identical value in `X-CSRF-Token` (the double-submit pattern). After authentication, a
fresh CSRF token replaces it, its digest is stored with the new session, and unsafe authenticated
requests must echo the raw cookie value in the same header. The backend will also require an exact
allowed `Origin`. Logout and all later state-changing endpoints use these protections; safe HTTP
methods never change state. All API responses use `Cache-Control: no-store` so authentication data
cannot be reused from a browser or intermediary cache.

CORS permits credentials only for exact frontend origins. Wildcard origins, methods, and headers
are not used. This local-only application permits both `http://localhost:5173` and
`http://127.0.0.1:5173`. The API explicitly allows only the methods and headers it needs,
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

Email input is parsed with `email-validator`, normalized, and converted to a lowercase canonical
lookup value before database access. Leading and trailing whitespace is removed. DNS deliverability
checks are intentionally disabled because this milestone does not send verification email and login
must not depend on network access. SMTPUTF8 local parts are not accepted so canonical lowercasing is
predictable with the current PostgreSQL constraint.

New passwords must contain 8 through 128 characters. The application does not trim passwords or
require uppercase letters, numbers, or symbols; passphrases, whitespace, and Unicode are accepted.
Passwords are hashed by `pwdlib` with Argon2id using 19 MiB of memory, two iterations, one lane, and
a unique random salt. Verification can return an upgraded hash if those parameters change later.

Login performs an Argon2id verification against a fixed non-secret dummy hash when no password
identity exists. Unknown accounts and wrong passwords receive the same generic response, while both
paths perform expensive password work to reduce timing-based account discovery.
Malformed stored hashes fail closed. Plaintext passwords are never stored or logged.

## First-party authentication API

`POST /auth/register` validates the submitted email and password, then creates the application user,
password identity, and first session in one request transaction. The service performs a friendly
email-collision check and the database uniqueness constraints remain the final defense against
concurrent registrations. A successful response contains only the user ID and canonical email; the
opaque session token is returned only through the HttpOnly cookie.

`POST /auth/login` returns the same `401 Invalid email or password` response for unknown accounts
and incorrect passwords. A successful login upgrades an outdated Argon2id hash when necessary and
creates a fresh independent application session. It does not reuse a caller-supplied identifier.

`POST /auth/logout` requires the active session plus its matching CSRF token, revokes that session,
and expires both browser cookies. `GET /auth/me` resolves a valid, unexpired, unrevoked cookie
session to its application user. Authentication failures do not reveal whether a session once
existed.

The reusable `CurrentSession` dependency validates the opaque token and loads its database row.
`CurrentUser` builds on it and gives protected routes the application-owned user without duplicating
cookie or session queries. `GET /protected` demonstrates authentication: any signed-in user may call
it. Authorization is a separate decision about what that user may do, such as requiring a plan's
`user_id` to equal the authenticated user's ID; ownership authorization belongs with the future
resource endpoints.

Tokens are accepted only in their canonical 43-character URL-safe form before hashing and querying
PostgreSQL. Missing, malformed, unknown, expired, and revoked session cookies all return the same
generic `401 Authentication required` response.

## Frontend authentication state

React wraps the application in a small `AuthProvider`. On startup it calls `GET /auth/me` with
`credentials: "include"`; a valid cookie restores the user after a refresh, while `401` selects the
unauthenticated view. Successful registration and login place the safe user response in memory.
Logout revokes the backend session and returns the application to the login form.

The frontend API client reads only the non-HttpOnly `mfp_csrf` cookie so it can echo that value in
`X-CSRF-Token`. It cannot read `mfp_session`, and it never copies authentication state into local or
session storage. The API hostname follows the Vite page hostname so cookies work consistently when
the local application is opened through either `localhost` or `127.0.0.1`.

## Google identity policy

The frontend loads Google Identity Services directly from `accounts.google.com` and renders its
standard button. The GIS callback sends the returned ID token to `POST /auth/google`; React does not
decode, persist, or log it. The endpoint has the same Origin and double-submit CSRF requirements as
password login.

The backend uses Google's supported `google-auth` Python library to validate the token signature,
audience, issuer, and expiration. It then independently requires the configured audience, an
accepted Google issuer, a future expiration, a valid issued-at time, a non-empty immutable `sub`, a
valid email, and the boolean `email_verified=true` claim. Only
`(provider="google", provider_subject=sub)` identifies a returning Google user; an email address is
not a stable provider identifier. Failure to fetch Google's public signing keys produces a
temporary-unavailability response rather than accepting an unverified token.

Matching emails never cause automatic linking:

- An existing Google `sub` signs in to its existing user and receives a fresh application session.
- A new Google `sub` with an unclaimed normalized email creates a user, Google identity, and session
  in one transaction.
- A new Google `sub` whose normalized email is already claimed is rejected without creating data.
- Password registration whose normalized email is already claimed by any provider is also rejected.
- Responses do not reveal which provider owns an existing email.

Secure identity linking uses separate milestone 6 endpoints. Both require an authenticated session
and session-bound CSRF token. A password user links Google only after submitting the current
password and a valid Google ID token issued within five minutes; the Google identity must represent
the user's canonical email. A Google user links a new password only after submitting a Google ID
token issued within five minutes whose immutable subject is already owned by that application user.
The new password is validated and Argon2id-hashed before storage.

Neither path authorizes a link from email equality alone. A Google subject already owned by another
user is never reassigned. The service performs explicit ownership checks, while the unique
provider-subject and per-user/provider constraints remain the final defense against concurrent
races. `GET /auth/methods` reports the connected methods for the authenticated user without exposing
credential details.

The authenticated React view displays those connected methods and only the action for the missing
provider. It reuses Google Identity Services for the required fresh Google proof. The returned token
is passed directly to the linking request and is not decoded, persisted, or stored in React state.

## Typed configuration

The backend validates a bounded session lifetime, the cookie `Secure` flag, and an optional Google
client ID at startup. The two exact CORS origins are application constants because this project has
one documented local environment. The settings model stays focused on values the application
actually consumes. Secrets and connection strings are excluded from settings representations.
Google configuration remains optional so password authentication runs independently. When a Web
client ID is supplied, Docker Compose passes the same public identifier to GIS and FastAPI. No
Google client secret is used or required for this ID-token sign-in flow.

## Deferred production protections

Milestone 5 will not by itself make authentication production-ready. Deployment work still needs
TLS termination and trusted-proxy configuration, rate limiting, credential-stuffing monitoring,
password-email ownership verification, secret rotation, session-row retention/cleanup, security
headers, dependency and image scanning, audit logging that excludes credentials, alerting, backups,
and an incident-response process.
