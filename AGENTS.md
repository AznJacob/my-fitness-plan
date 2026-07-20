# MyFitnessPlan — Codex Instructions

## Project objective

Build MyFitnessPlan, a research-grounded general wellness application that creates personalized workout and nutrition plans.

This project is also intended to demonstrate end-to-end Solutions Engineer skills, including requirements analysis, full-stack development, authentication, API integration, data persistence, security, testing, deployment, monitoring, documentation, and technical communication.

## Technology stack

- React frontend
- FastAPI backend
- Python
- PostgreSQL
- pgvector in a later milestone
- Docker Compose
- Anthropic Claude API
- Microsoft Entra ID with OAuth 2.0 and OpenID Connect
- Optional Microsoft Graph integration
- Git and GitHub

Do not introduce additional frameworks, infrastructure, or services unless they solve a clear current requirement.

## Product workflow

1. A user signs in using Microsoft Entra ID.
2. The backend creates or retrieves the corresponding PostgreSQL user record.
3. The user enters fitness goals, experience, availability, equipment, diet preferences, and relevant constraints.
4. FastAPI performs deterministic calculations and retrieves relevant fitness research.
5. Claude generates a schema-validated workout and nutrition plan.
6. The plan and its research citations are persisted in PostgreSQL.
7. Returning users can review previous plans, mark a plan active, archive plans, or create a new plan.
8. Later versions may add workout logging, progress tracking, and adaptive plan updates.

## Wellness and safety boundaries

This is a general wellness application.

Do not implement features that:

- Diagnose medical conditions
- Treat injuries or diseases
- Provide rehabilitation plans
- Replace physicians, physical therapists, or registered dietitians
- Present generated content as professional medical advice

Use appropriate disclaimers and validation for potentially unsafe user inputs.

## Development priorities

Build incrementally and prioritize a working vertical slice.

Use this order unless the current task explicitly says otherwise:

1. Repository and project structure
2. Dockerized React, FastAPI, and PostgreSQL setup
3. Database schema and migrations
4. Microsoft Entra ID authentication and protected API endpoints
5. User profile persistence
6. Basic Claude API integration
7. Structured plan generation and validation
8. Plan history and plan-detail pages
9. Research ingestion, embeddings, pgvector, RAG, and citations
10. Tests, logging, error handling, security review, and documentation
11. Workout logging and adaptive updates

Do not implement future milestones prematurely.

## Engineering expectations

- Prefer straightforward, production-minded implementations over clever abstractions.
- Keep frontend, backend, and database responsibilities clearly separated.
- Use Python type hints.
- Use Pydantic models for request, response, configuration, and LLM-output validation.
- Use dependency injection where FastAPI naturally supports it.
- Keep business logic outside route handlers.
- Use database migrations instead of manually editing production schemas.
- Validate all external input.
- Never trust identity or authorization data supplied directly by the frontend.
- Never commit secrets, tokens, passwords, connection strings, or private keys.
- Keep secrets in environment variables and document them in `.env.example` using placeholders.
- Use least-privilege authorization.
- Handle API failures, timeouts, malformed LLM output, and database errors explicitly.
- Add tests for meaningful behavior rather than implementation details.
- Use structured logging rather than scattered print statements.
- Update documentation when architecture or behavior changes.

## LLM integration expectations

- Deterministic calculations belong in Python, not in the prompt.
- Use schema-validated structured output.
- Treat model output as untrusted input until validation succeeds.
- Do not silently accept malformed output.
- Separate system instructions, application context, retrieved research, and user data.
- Preserve research-source metadata so generated citations can be traced.
- Consider prompt injection when retrieved documents or user text are included.
- Do not claim that RAG, pgvector, structured generation, or another feature is complete until it is genuinely implemented and tested.

## How Codex should work

Before editing:

1. Inspect the relevant files.
2. State the intended change and important assumptions.
3. Keep the task limited to the requested milestone.
4. Identify security or data-model implications.

While editing:

- Make small, reviewable changes.
- Do not rewrite unrelated files.
- Preserve existing working behavior.
- Explain unfamiliar dependencies before adding them.
- Avoid generating large amounts of code that the developer cannot reasonably review.
- Include comments only where they explain non-obvious decisions.

After editing:

1. Run the relevant formatter, linter, tests, and build commands.
2. Report which checks passed or failed.
3. Summarize files changed and important decisions.
4. Distinguish completed behavior from planned behavior.
5. Explain what the developer should be able to describe in an interview.
6. Suggest an accurate Git commit message.

## Mentoring expectations

The repository owner is learning FastAPI, production Python development, Microsoft Entra ID, LLM integration, deployment, monitoring, and system-design communication.

When generating code:

- Explain how major FastAPI concepts compare with Spring Boot when useful.
- Explain authentication versus authorization clearly.
- Explain important architectural trade-offs.
- Do not conceal complexity behind generated code.
- Prefer implementations the repository owner can confidently explain during an interview.
- Challenge unsupported claims that a feature is production-ready.

## Git expectations

- Work on one focused change at a time.
- Do not commit automatically unless explicitly requested.
- Do not push automatically unless explicitly requested.
- Do not modify Git history.
- Do not include secrets or local environment files.
- Recommend concise conventional commit messages such as:
  - `chore: initialize project structure`
  - `feat: add FastAPI health endpoint`
  - `test: add user service tests`
  - `docs: document authentication flow`

## Current project status

The project is at the initial setup stage.

Unless repository files show otherwise, assume that application features have not yet been implemented. Inspect the repository before describing anything as complete.
