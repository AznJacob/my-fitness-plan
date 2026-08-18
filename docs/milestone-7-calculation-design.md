# Milestone 7 calculation and safety design

Milestone 7 implements a narrow deterministic boundary for general-wellness planning. It does not
expose a standalone API route because the current frontend has no independent calculation workflow;
the protected plan-generation service will consume these functions directly in milestone 9.

## Supported inputs and calculations

The saved profile currently contains two numeric inputs suitable for exact calculations:

| Input | Unit | Accepted range | Meaning |
| --- | --- | --- | --- |
| `days_per_week` | days per seven-day week | 1-7 | Days the user says are available |
| `session_minutes` | whole minutes per available day | 10-180 | Time the user says is available per session |

The calculation service produces only:

- `weekly_available_minutes = days_per_week * session_minutes`
- `non_training_days_per_week = 7 - days_per_week`

These values describe availability, not a recommended dose of exercise. A generated plan may use
less than the available time. Version `1` of the result schema makes persisted plan snapshots and
future prompt inputs explainable if calculation policy changes.

The 10-180 minute session range is an MVP product boundary, not a medical threshold. It avoids
creating implausibly short or all-day generated sessions while retaining a broad range of normal
planning preferences. The API, SQLAlchemy metadata, PostgreSQL constraint, and React input enforce
the same range. The migration deliberately stops with an actionable error instead of silently
changing an existing out-of-range profile.

## Safety boundary

Safety assessment is separate from arithmetic. Its typed result contains a Boolean eligibility
decision and stable issue codes. The service rejects out-of-scope session durations and explicit
requests for diagnosis, injury treatment, disease treatment, pregnancy-specific planning, eating
disorder guidance, or rehabilitation before any future Claude request. It returns an explanation
directing the user to an appropriately qualified professional.

Free-text constraints remain untrusted input. Deterministic phrase screening can catch explicit
out-of-scope requests but cannot diagnose a condition, determine medical clearance, or prove that a
request is safe. It must therefore be conservative, transparent, and backed by generated-output
validation and a visible general-wellness disclaimer in later milestones. Constraints such as a
preference for low-impact movement are not themselves medical requests.

No age, body measurements, sex-related inputs, diagnoses, medications, wearable data, or measured
performance are collected. No new fields are required for the supported schedule calculations, so
Stage 7.1 does not expand the sensitive-data footprint.

## Intentionally unsupported calculations

The application will not calculate BMI, BMR, TDEE, calorie or macronutrient targets, body-fat
percentage, heart-rate zones, one-repetition maximum, injury risk, readiness, or rehabilitation
progress from the current profile. Those outputs either require data the product does not collect,
depend on measurements the product does not have, or cross the intended general-wellness boundary.
Claude must not be asked to invent them in later milestones.

## Separation of responsibilities

`app.wellness.schemas` is independent of FastAPI routes and future provider prompts. Pydantic
validates the calculation input, validates internal consistency of derived results, and represents
safety failures in a stable form. `app.wellness.service` contains pure Python functions that adapt a
validated profile, perform the arithmetic, and assess the scope. A protected calculation endpoint
can be added later only if a real client workflow needs it; milestone 9 can call the service without
an unnecessary HTTP round trip.

All stored and calculated durations remain whole minutes. No unit conversion is performed because
the profile collects only minutes and the downstream workflow does not need another unit. Keeping a
single canonical unit avoids floating-point rounding and ambiguous hour representations.

## Remaining limitations

Phrase matching is deliberately a narrow first-line scope filter. It is case-insensitive and handles
common medical and rehabilitation wording, but natural language is too broad for a keyword list to
prove safety. It may reject ambiguous text, and novel wording may not match. Later generated-output
validation and the visible wellness disclaimer remain required. No model provider is called in this
milestone.
