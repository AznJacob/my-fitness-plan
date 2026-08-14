# Authentication verification

Milestone 5 is complete for MyFitnessPlan's documented local portfolio environment. This record
separates tested behavior from protections that would still be required for an internet-facing
deployment.

## Automated coverage

The backend suite verifies:

- Argon2id hashing, successful verification, invalid passwords, malformed stored hashes, and hash
  upgrades.
- Email validation and normalization, password length boundaries, duplicate registration, and
  generic login failures for both unknown users and incorrect passwords.
- Transactional creation of users, password or Google identities, and application sessions.
- Opaque token shape, hashed token storage, fresh sessions, logout revocation, and missing,
  malformed, unknown, expired, or revoked session rejection.
- HttpOnly session-cookie attributes, the JavaScript-readable CSRF cookie, exact Origin checks,
  double-submit CSRF checks, session-bound logout CSRF, credentialed CORS, and `no-store` responses.
- Protected-route access with a valid session and generic rejection without one.
- Mocked Google-library validation of audience, issuer, expiration, verified email, immutable `sub`,
  invalid signatures, and public-key retrieval failures.
- New and returning Google identities, both directions of password/Google email collision, absence
  of automatic linking, missing Google configuration, and use of the same application session.
- The complete Alembic revision chain and model/schema alignment against an isolated empty
  PostgreSQL database.

Frontend checks enforce formatting, lint rules, strict TypeScript, and a production Vite build. The
React flow keeps only the safe user response in memory, restores it through `/auth/me`, includes
credentials on API requests, and reads only the CSRF cookie—not the HttpOnly session cookie.

## Manual local verification

On August 13, 2026, the repository owner verified the Docker Compose browser flow locally:

- Password registration reached the authenticated account view.
- Refresh restored authentication through `/auth/me`.
- Logout returned to the unauthenticated form.
- Existing password credentials could log in again.
- Google Identity Services completed a real Google sign-in using the configured Web client ID.

Automated integration tests, rather than a real external account, verify collision and provider
failure cases so those tests remain deterministic.

## Scope decision

**Required now:** No remaining work for milestone 5 in the supported local environment.

**Valuable next:** Milestone 6 profile APIs and forms should reuse `CurrentUser` and enforce that
every profile operation belongs to that authenticated user. Secure identity linking can be designed
there as a separate reauthentication flow.

**Defer:** An internet-facing deployment would still require TLS and `Secure` cookies, trusted-proxy
configuration, rate limiting and credential-stuffing defenses, stronger security headers,
password-email ownership verification, signing-key cache and timeout tuning, session cleanup, audit
events, monitoring and alerting, secret rotation, backups, dependency/image scanning, and
incident-response procedures.
