# Milestone 8 Claude integration

## Stage 8.1: schemas, configuration, and client

The backend uses Anthropic's official Python SDK and defaults to the pinned Claude Haiku 4.5 model
ID `claude-haiku-4-5-20251001`. A pinned ID keeps the model snapshot stable; the shorter
`claude-haiku-4-5` alias can move to a later snapshot. The model remains environment-configurable so
an intentional model change does not require a code edit.

The client factory requires `ANTHROPIC_API_KEY` only when Claude functionality is requested. The
rest of FastAPI can start without it. Pydantic stores the key as `SecretStr`, excludes it from the
settings representation, and treats an empty environment value as unconfigured. No key is logged,
returned through an API, or committed to the repository.

Provider requests are bounded by configuration:

- 60-second timeout, accepted range 5-300 seconds.
- 6,000 maximum output tokens, accepted range 512-10,000.
- Zero automatic retries by default, with at most one configurable retry.
- Temperature 0.2, accepted range 0-1.

Anthropic's SDK normally retries selected failures twice and uses a much longer default timeout.
The application overrides both behaviors so a single user action has predictable latency and cannot
silently become several billable requests. Stage 8.1 constructs this client but does not send an API
request. See Anthropic's [Python SDK documentation](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)
and [model versioning documentation](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions).

## Structured plan boundary

`GeneratedPlan` is the only accepted provider-output shape. It contains a versioned title and
overview, bounded workout sessions, exercise prescriptions, and bounded nutrition templates. Every
model rejects undeclared fields. Exercises require repetitions or a duration, sessions stay within
the application's 10-180 minute range, and collection sizes prevent unexpectedly large output.

The nutrition schema intentionally contains meal suggestions, hydration guidance, meal timing, and
dietary-preference notes. It has no fields for calorie targets, macronutrient targets, diagnosis,
treatment, supplements, or citations. The workout schema has no rehabilitation or medical-treatment
fields. Application-owned disclaimers are also excluded because trusted application text should not
come from the model.

`ClaudePlanRequest` keeps four inputs named separately before provider serialization:

- System instructions define non-negotiable behavior and safety rules.
- Application context explains the requested planning task.
- Calculated values contain deterministic Python results.
- Profile data contains bounded but untrusted user preferences.

Stage 8.2 will serialize these sections, call Anthropic structured outputs, validate the returned
content again with Pydantic, and map provider and validation failures into application errors.
Anthropic documents structured outputs for Claude Haiku 4.5 in its
[structured outputs guide](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
