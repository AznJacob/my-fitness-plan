# MyFitnessPlan

MyFitnessPlan is a research-grounded general wellness application that will create personalized workout and nutrition plans from a user's goals, experience, availability, equipment, dietary preferences, and relevant constraints.

The project is being built incrementally as an end-to-end Solutions Engineer portfolio project. It is intended to demonstrate requirements analysis, full-stack development, identity, API integration, data persistence, security, testing, deployment, monitoring, documentation, and technical communication.

> **Project status:** Milestones 1 through 4 are complete. The repository contains verified FastAPI and React/TypeScript applications, PostgreSQL connectivity, an initial relational schema, and tested Alembic migrations. Milestone 5, first-party and Google authentication, is next. The remaining capabilities described below are planned and should not be considered implemented until their corresponding milestones are completed and tested.

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

## Initial database model

The milestone 4 SQLAlchemy metadata defines four PostgreSQL tables:

- `users` provides the application-owned identity shared by all sign-in methods.
- `authentication_identities` links one password and/or one Google identity to a user. It stores
  password hashes only for password identities and never stores plaintext passwords or Google
  tokens.
- `profiles` stores one current set of general-wellness planning preferences per user.
- `plans` stores validated workout and nutrition JSON documents with the profile snapshot that
  produced them. Relational ownership and status columns enforce lifecycle rules, including at
  most one active plan per user.

Foreign keys delete dependent private data with their owning user. Matching email addresses do
not link accounts; future authentication code must verify provider credentials and require
reauthentication before linking identities. Initial revision `7768cfd3a397` creates and removes
these tables and has been tested against a disposable empty PostgreSQL database.

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

The final local state is revision `7768cfd3a397 (head)` with `users`,
`authentication_identities`, `profiles`, and `plans` present.

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
