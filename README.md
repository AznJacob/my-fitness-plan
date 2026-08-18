# MyFitnessPlan

MyFitnessPlan is a research-grounded general wellness application that will create personalized workout and nutrition plans from a user's goals, experience, availability, equipment, dietary preferences, and relevant constraints.

## Product scope

The planned workflow is:

1. A user signs in with an email and password or Google Sign-In.
2. The backend creates or retrieves the corresponding PostgreSQL user record.
3. The user submits fitness goals, experience, availability, equipment, dietary preferences, and relevant constraints.
4. FastAPI performs deterministic calculations and retrieves relevant fitness research.
5. Anthropic Claude produces a schema-validated workout and nutrition plan.
6. The plan and traceable research citations are stored in PostgreSQL.
7. Returning users can review previous plans, select an active plan, archive plans, or create a new one.

## Wellness and safety boundaries

MyFitnessPlan is a **general wellness application**, not a medical product. It will not diagnose medical conditions, treat injuries or diseases, provide rehabilitation programs, replace qualified healthcare professionals, or present generated content as medical advice.

Potentially unsafe inputs and generated outputs must be validated. Appropriate disclaimers will be displayed to users, and model output will be treated as untrusted until it passes application validation.

## Planned technology stack

- React frontend using TypeScript
- Tailwind CSS for basic, utility-first frontend styling
- FastAPI backend using Python and Pydantic
- PostgreSQL
- Docker Compose for local development
- First-party email and password authentication
- Google Sign-In using OAuth 2.0 and OpenID Connect
- Anthropic Claude API
- pgvector and retrieval-augmented generation in a later milestone

## Repository structure

```text
my-fitness-plan/
|-- backend/
|   |-- app/              # FastAPI application
|   |-- migrations/       # Versioned Alembic database schema changes
|   |-- tests/            # Backend tests
|   `-- Dockerfile        # Backend development image
|-- frontend/
|   |-- src/              # React application source
|   `-- Dockerfile        # Frontend development image
|-- docker-compose.yaml   # Local development services
|-- .env.example          # Committable configuration template
`-- README.md
```

## Development roadmap

Development follows small, dependency-ordered milestones:

1. Repository structure and development standards
2. Minimal FastAPI and React applications
3. Dockerized application and PostgreSQL environment
4. Database schema and migrations
5. First-party email/password and Google authentication
6. User profile persistence
7. Deterministic wellness calculations
8. Schema-validated Claude integration
9. Workout and nutrition plan generation
10. Plan persistence and lifecycle management
11. Research ingestion, pgvector retrieval, and traceable citations
12. Security, testing, CI/CD, deployment, and monitoring

A milestone is complete only when its behavior is implemented, tested, documented, and manually verified. Later capabilities should not be described as complete prematurely.

## Database model

The SQLAlchemy metadata currently defines five PostgreSQL tables:

- `users` provides the application-owned identity shared by all sign-in methods and owns a unique
  canonical normalized email.
- `authentication_identities` links one password and/or one Google identity to a user. It stores
  password hashes only for password identities and never stores plaintext passwords or Google
  tokens.
- `sessions` stores user ownership, SHA-256 session and CSRF token digests, absolute expiration,
  revocation, and lifecycle timestamps. Raw tokens exist only in browser cookies.
- `profiles` stores one current set of general-wellness planning preferences per user.
- `plans` stores validated workout and nutrition JSON documents with the profile snapshot that
  produced them. Relational ownership and status columns enforce lifecycle rules, including at
  most one active plan per user.

Foreign keys delete dependent private data with their owning user. Matching email addresses never
link accounts by themselves. Explicit linking requires an authenticated session, session-bound
CSRF validation, and fresh proof of the already connected method. Initial revision
`7768cfd3a397` creates the milestone 4 schema. Revision `b2f7c91d4e63` adds canonical emails and
sessions. The complete revision chain is tested against a disposable empty PostgreSQL database,
including model/schema drift detection.

## Docker development environment

Docker Compose is the canonical local development environment. It starts the React frontend,
FastAPI backend, and PostgreSQL database with health checks and persistent database storage.

From the repository root, create your ignored local environment file:

```bash
cp .env.example .env
```

Replace `POSTGRES_PASSWORD` in `.env` with a local development password. Do not commit `.env`.
Docker Compose constructs the backend's `DATABASE_URL` from these values and uses the internal
`postgres:5432` service address. FastAPI verifies that connection before startup completes.

Build and start the stack:

```bash
docker compose up --build
```

When all services are healthy, they are available at:

- Frontend: `http://localhost:5173`
- Backend health check: `http://localhost:8000/health`
- Backend API documentation: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5433` by default (`5432` inside the Compose network)

Inspect service state and health:

```bash
docker compose ps
```

Stop the containers without deleting PostgreSQL data:

```bash
docker compose down
```

To intentionally reset the local database, remove the named volume:

```bash
docker compose down --volumes
```

The volume deletion command permanently removes local PostgreSQL data.

## Database migrations

Run migration commands through the backend container from the repository root. Start PostgreSQL
first; Compose waits for its health check before running Alembic:

```bash
docker compose up -d postgres
docker compose build backend
```

Inspect the revision chain, available head, currently applied revision, and model/schema drift:

```bash
docker compose run --rm backend python -m alembic -c alembic.ini history
docker compose run --rm backend python -m alembic -c alembic.ini heads
docker compose run --rm backend python -m alembic -c alembic.ini current
docker compose run --rm backend python -m alembic -c alembic.ini check
```

Upgrade the database to the newest committed revision:

```bash
docker compose run --rm backend python -m alembic -c alembic.ini upgrade head
```

After changing SQLAlchemy metadata, generate and then review a proposed revision before applying
it:

```bash
docker compose run --rm backend python -m alembic -c alembic.ini revision --autogenerate -m "describe schema change"
```

Downgrade one revision with `downgrade -1`. Downgrading this project's initial revision to `base`
drops all four application tables and permanently deletes any data in them, so use it only when
that data can safely be discarded:

```bash
docker compose run --rm backend python -m alembic -c alembic.ini downgrade -1
docker compose run --rm backend python -m alembic -c alembic.ini downgrade base
```

PostgreSQL may retain an empty `alembic_version` bookkeeping table at `base`; this is normal. Run
`upgrade head` again after a local downgrade to restore a usable development schema.

Run the complete backend suite, including the isolated empty-database migration test:

```bash
docker compose --profile test run --rm --build backend-test
```

The test creates a uniquely named disposable database, applies all migrations, inspects the
resulting revision, tables, foreign keys, indexes, and metadata alignment, and removes that test
database without modifying normal development data.

The initial migration was manually verified on August 6, 2026 with this sequence:

```text
base -> upgrade head -> inspect -> downgrade base -> inspect -> upgrade head -> alembic check
```

The current migration head is `b2f7c91d4e63`, with `users`, `authentication_identities`,
`sessions`, `profiles`, and `plans` present after upgrade.

## Host-based local development

Running directly on the host remains useful for focused development and quality checks.

Install the backend and its development tools from the repository root:

```bash
cd backend
python -m pip install -e ".[dev]"
```

Start the FastAPI development server from `backend/`:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://myfitnessplan:your-password@localhost:5433/myfitnessplan"
python -m uvicorn app.main:app --reload
```

When FastAPI runs on the host, PostgreSQL must already be running and the URL uses the published
`localhost:5433` address. The application stops during startup if the database is unavailable.

The local backend is then available at:

- Health check: `http://127.0.0.1:8000/health`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

Install the frontend tooling from the repository root:

```bash
cd frontend
npm install
```

Start the Vite development server from `frontend/`:

```bash
npm run dev
```

The local frontend is then available at `http://127.0.0.1:5173/`.

The current development toolchain is:

- Python 3.14.6 (the backend accepts compatible Python 3.14 patch releases)
- Node.js 24.18.0 LTS (the frontend accepts compatible Node.js 24 releases)
- npm 11.16.0

The exact development defaults are recorded in `.python-version` and `.nvmrc`. The supported ranges are enforced by `backend/pyproject.toml` and `frontend/package.json`.

Configuration will be supplied through environment variables. Committable `.env.example` files will document required variable names using placeholder values; real `.env` files and credentials must never be committed.

The milestone 5 authentication design is recorded in
[`docs/authentication-architecture.md`](docs/authentication-architecture.md). It defines the planned
opaque-session, cookie, CORS, CSRF, expiration, and Google/email-collision behavior. Email/password
registration, login, logout, current-user lookup, reusable session protection, the basic React
authentication flow, and Google Sign-In are implemented and verified for the local portfolio
environment. This does not make the authentication system production-ready.

The local API exposes:

- `GET /auth/csrf` to issue the browser-readable double-submit CSRF cookie.
- `POST /auth/register` and `POST /auth/login` to establish an opaque HttpOnly cookie session.
- `POST /auth/google` to validate a Google ID token and establish the same application session.
- `POST /auth/logout` to validate CSRF, revoke the current session, and clear its cookies.
- `GET /auth/me` to restore authenticated user state without exposing the session token.
- `GET /auth/methods` to list the current user's connected password and Google methods.
- `POST /auth/link/google` to link Google after fresh password and Google verification.
- `POST /auth/link/password` to link a password after fresh verification of the owned Google
  subject.
- `GET /protected` as the minimal example of a route available to any authenticated user.
- `GET /profile` to retrieve the signed-in user's saved planning preferences.
- `PUT /profile` to create or replace those preferences with session-bound CSRF protection.

Profile ownership is derived only from the authenticated application session. Profile requests do
not accept a user ID, so a client cannot select or update another user's row. A missing profile
returns `404`; users create their initial profile with the same `PUT` used for later replacements.
The authenticated React view loads this profile on entry, renders a basic create or edit form, and
saves through the shared credentialed API client with session-bound CSRF protection. List fields use
one item per line. This flow captures preferences only; it does not generate a plan.

State-changing authentication requests must come from `http://localhost:5173` or
`http://127.0.0.1:5173`, include cookies, and copy the `mfp_csrf` cookie into the
`X-CSRF-Token` header. The backend permits credentialed CORS only from those two local origins and
marks API responses `Cache-Control: no-store`. The Stage 7 frontend performs this flow without ever
reading or storing `mfp_session`.

To test the current browser flow, start the stack and apply migrations:

```bash
docker compose up -d --build
docker compose exec backend python -m alembic -c alembic.ini upgrade head
```

Open `http://localhost:5173`, register with a valid email and a password containing at least eight
characters, and confirm the signed-in account view appears. Refresh to verify `/auth/me` restores
the session, then log out and verify the login form returns. You can then log in with the same
credentials. The forms intentionally use basic browser styling until the main application features
are complete.

### Local Google Sign-In setup

Follow Google's [Google Identity Services setup guide](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid)
to configure OAuth branding and create an OAuth 2.0 client with application type **Web application**.
Add these exact Authorized JavaScript origins:

```text
http://localhost
http://localhost:5173
http://127.0.0.1:5173
```

Copy `.env.example` to the ignored root `.env` file and set `GOOGLE_CLIENT_ID` to the resulting Web
client ID. A client ID is a public identifier; do not add or commit a Google client secret because
this flow does not use one. Recreate the backend and frontend so both receive the same ID:

```bash
docker compose up -d --build --force-recreate backend frontend
```

The simple authentication screen will then show Google's standard button. A Google account whose
normalized email is already claimed by a password account is deliberately rejected during normal
sign-in. Automatic linking based only on matching email could allow account takeover; linking is a
separate authenticated and freshly reauthenticated operation. The authenticated React view shows
connected methods and lets the user add the missing method through that explicit flow.

The automated security coverage, manual checks, scope decisions, and deferred deployment
protections are recorded in
[`docs/authentication-verification.md`](docs/authentication-verification.md).
Milestone 6 profile ownership, account-linking boundaries, frontend data flow, and remaining
hardening are summarized in
[`docs/milestone-6-architecture.md`](docs/milestone-6-architecture.md).

### Code quality checks

Run backend checks from `backend/`:

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy .
python -m pytest
```

Run frontend checks from `frontend/`:

```bash
npm run format:check
npm run lint
npm run typecheck
npm run build
```

Editor extensions may surface these tools while code is being written, but the commands above are the repository's reproducible checks.

## Engineering principles

- Keep frontend, backend, database, and external-provider responsibilities separate.
- Put business logic in services or domain modules rather than route handlers.
- Use Python type hints and Pydantic models at external boundaries.
- Perform deterministic calculations in Python rather than in LLM prompts.
- Validate all user input and all model output.
- Store only securely hashed passwords, never plaintext credentials.
- Validate Google identity tokens on the backend rather than trusting frontend claims.
- Keep authorization and resource ownership tied to one application user regardless of sign-in method.
- Use database migrations for schema changes.
- Handle database and external API failures explicitly.
- Prefer meaningful behavior tests over implementation-detail tests.
- Keep secrets out of source control and logs.

## Contributing workflow

Keep each change focused on one milestone. Before considering a change complete:

1. Run the relevant formatter and linter.
2. Run backend and frontend tests as applicable.
3. Run the relevant build.
4. Review security and data-model implications.
5. Update documentation to match actual behavior.

Do not commit secrets, local environment files, generated build output, or editor-specific state.

## License

No license has been selected yet. Unless a license is added, the repository should not be assumed to grant reuse or redistribution rights.
