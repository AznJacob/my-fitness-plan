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

- 35-second timeout, accepted range 5-300 seconds.
- 1,000 maximum output tokens, accepted range 512-10,000.
- Zero automatic retries by default, with at most one configurable retry.
- Temperature 0.2, accepted range 0-1.

Anthropic's SDK normally retries selected failures twice and uses a much longer default timeout.
The application overrides both behaviors so a single user action has predictable latency and cannot
silently become several billable requests. Stage 8.1 constructs this client but does not send an API
request. See Anthropic's [Python SDK documentation](https://platform.claude.com/docs/en/cli-sdks-libraries/sdks/python)
and [model versioning documentation](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions).

## Structured plan boundary

New generations use the concise `GeneratedPlan` schema version 2. It contains a title and overview,
the exact scheduled workout sessions, two-to-three compact exercise prescriptions per session,
three-to-four meal ideas, and short progression, recovery, daily-food, and hydration guidance.
Every model rejects undeclared fields, sessions remain within the application's 10-180 minute range,
and tight collection sizes support the 1,000-token response ceiling. Persisted schema-version-1
plans retain a separate legacy validator and renderer so changing the provider contract does not
invalidate history.

The provider-facing JSON schema uses short aliases for version-2 field names to reduce output-token
overhead. Pydantic immediately converts those aliases back to descriptive application field names,
and FastAPI responses, persistence, and the React UI never expose the abbreviated representation.

The nutrition schema intentionally contains food suggestions and hydration guidance rather than
individualized calorie or macronutrient targets. It has no fields for diagnosis, treatment,
supplements, or citations. The workout schema has no rehabilitation or medical-treatment fields.
Application-owned disclaimers are also excluded because trusted application text should not come
from the model.

`ClaudePlanRequest` keeps four inputs named separately before provider serialization:

- System instructions define non-negotiable behavior and safety rules.
- Application context explains the requested planning task.
- Calculated values contain deterministic Python results.
- Profile data contains bounded but untrusted user preferences.

Stage 8.2 serializes these sections, calls Anthropic structured outputs, validates the returned
content again with Pydantic, and maps provider and validation failures into application errors.
Anthropic documents structured outputs for Claude Haiku 4.5 in its
[structured outputs guide](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

## Stage 8.2: generation and validation

`generate_structured_plan` owns one provider attempt. It creates the bounded client, sends the
application's transformed `GeneratedPlan` JSON Schema through `output_config.format`, validates the
response, and always closes the SDK client. The Anthropic SDK's public `transform_schema` helper
removes schema features unsupported by constrained decoding; the application still applies the full
Pydantic model afterward, so provider compatibility does not weaken the acceptance boundary.

The system prompt contains a fixed application-owned safety and prompt-injection boundary followed
by the caller's bounded system instructions. The user message contains three plainly labeled
sections: application context, calculated-values JSON, and profile-data JSON. Profile strings remain
JSON-encoded data. Instructions embedded in those fields are not moved into the system prompt.

The response must contain exactly one non-empty text block with one JSON value. Markdown fences,
multiple text blocks, partial output, and other malformed formats are rejected rather than stripped,
combined, retried, or repaired. Parsed JSON is treated as untrusted and must pass `GeneratedPlan`
validation again before it can leave the service.

Failures use stable application codes for missing configuration, timeout, network failure, provider
rejection or refusal, empty output, invalid JSON, schema violations, truncation, and unexpected
response structure. Public messages do not contain provider response bodies, API keys, or profile
data. Milestone 9 will map these codes to explicit protected-API responses.

## Current limitations

Milestone 8 has no FastAPI generation endpoint, React workflow, plan persistence, research
retrieval, or citations. The provider interaction is verified with deterministic mocks; no paid API
request has been made. A real Haiku call requires explicit approval during later end-to-end
verification. Schema validation establishes structural correctness, while milestone 9 must still
validate generated text against the general-wellness content boundary.
