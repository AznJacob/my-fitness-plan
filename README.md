# MyFitnessPlan

MyFitnessPlan is a research-grounded general wellness application that will create personalized workout and nutrition plans from a user's goals, experience, availability, equipment, dietary preferences, and relevant constraints.

The project is being built incrementally as an end-to-end Solutions Engineer portfolio project. It is intended to demonstrate requirements analysis, full-stack development, identity, API integration, data persistence, security, testing, deployment, monitoring, documentation, and technical communication.

> **Project status:** Initial repository setup. The capabilities described below are planned and should not be considered implemented until their corresponding milestones are completed and tested.

## Product scope

The planned workflow is:

1. A user signs in with Microsoft Entra ID.
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

- React frontend
- FastAPI backend using Python and Pydantic
- PostgreSQL
- Docker Compose for local development
- Microsoft Entra ID using OAuth 2.0 and OpenID Connect
- Anthropic Claude API
- pgvector and retrieval-augmented generation in a later milestone
- Optional Microsoft Graph integration after the core product is complete

## Repository structure

```text
my-fitness-plan/
|-- backend/             # FastAPI application and backend tests
|-- frontend/            # React application and frontend tests
|-- docs/                # Architecture and engineering documentation
|-- docker-compose.yaml  # Local services (planned)
`-- README.md
```

The application directories are currently placeholders. Their internal structures will be introduced with the backend and frontend initialization milestones.

## Development roadmap

Development follows small, dependency-ordered milestones:

1. Repository structure and development standards
2. Minimal FastAPI and React applications
3. Dockerized application and PostgreSQL environment
4. Database schema and migrations
5. Microsoft Entra ID authentication
6. User profile persistence
7. Deterministic wellness calculations
8. Schema-validated Claude integration
9. Workout and nutrition plan generation
10. Plan persistence and lifecycle management
11. Research ingestion, pgvector retrieval, and traceable citations
12. Security, testing, CI/CD, deployment, and monitoring

A milestone is complete only when its behavior is implemented, tested, documented, and manually verified. Later capabilities should not be described as complete prematurely.

## Local development

Local setup commands are not available yet. They will be documented here after the Python and Node projects and Docker services have been initialized.

The current development toolchain is:

- Python 3.14.6 (the backend accepts compatible Python 3.14 patch releases)
- Node.js 24.18.0 LTS (the frontend accepts compatible Node.js 24 releases)
- npm 11

The exact development defaults are recorded in `.python-version` and `.nvmrc`. The supported ranges are enforced by `backend/pyproject.toml` and `frontend/package.json`. Docker will become the canonical reproducible environment when the container milestone is implemented.

Configuration will be supplied through environment variables. Committable `.env.example` files will document required variable names using placeholder values; real `.env` files and credentials must never be committed.

## Engineering principles

- Keep frontend, backend, database, and external-provider responsibilities separate.
- Put business logic in services or domain modules rather than route handlers.
- Use Python type hints and Pydantic models at external boundaries.
- Perform deterministic calculations in Python rather than in LLM prompts.
- Validate all user input and all model output.
- Derive identity and authorization from validated access tokens, never frontend claims.
- Use database migrations for schema changes.
- Handle database and external API failures explicitly.
- Prefer meaningful behavior tests over implementation-detail tests.
- Keep secrets out of source control and logs.

## Documentation

Architecture decisions, data models, authentication flows, security considerations, and operational guidance will live in `docs/` as those parts of the system are designed and implemented.

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
