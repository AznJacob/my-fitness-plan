# Milestone 9 plan-generation architecture

## Stage 9.1 backend workflow

`POST /plans/generate` is a state-changing, protected operation. It accepts no request body and no
user identifier. The backend resolves the application user from the opaque HttpOnly session and
requires the existing origin-bound, session-bound CSRF proof before any profile lookup or Claude
request can occur.

The application workflow performs these steps in order:

1. Load the profile owned by the authenticated user. A missing profile returns a machine-readable
   `404 missing_profile` response.
2. Revalidate the stored row as a `ProfileInput` and run the deterministic general-wellness scope
   assessment. Out-of-scope medical or rehabilitation requests return `422 unsafe_profile` and do
   not reach Claude.
3. Calculate the exact schedule facts in Python: sessions per week, minutes per session, weekly
   available minutes, and non-training days. Claude receives these results as data and does not
   calculate or replace them.
4. Submit the separated system instructions, application context, calculated values, and profile
   data through the Stage 8 structured-generation service.
5. Treat the schema-valid result as still untrusted. A deterministic output gate checks that the
   session count and duration fit the calculated availability and rejects medical content,
   calorie or macronutrient prescriptions, supplement or medication directives, and instructions
   to ignore or push through pain.
6. Return the validated workout and nutrition plan. Stage 9.1 does not create a `plans` row.

The output gate is deliberately a narrow defense-in-depth control, not a medical-safety classifier
or proof that free-form model text is safe. It catches specific prohibited categories the product
can explain and test. Phrases such as advice to stop when an activity causes pain remain allowed.

## API failure contract

Generation failures use a JSON `detail` object with a stable `code` and a safe `message`. Scope
failures may also include stable issue codes. Missing Claude configuration is distinguished from a
temporarily unavailable provider; provider rejection is distinguished from JSON/schema/output
failure. Raw provider responses, profile contents, configuration values, and API keys are not
placed in client errors.

## Stage 9.1 boundaries

Stage 9.1 exposed only the backend generation workflow. The React generation experience and routed
navigation were added in Stage 9.2. Generated plans remained transient through Milestone 9; Stage
10.1 subsequently added persistence and lifecycle APIs.

Research retrieval, pgvector, research citations, and source attribution are not implemented. The
workflow explicitly tells Claude not to invent research or citations. MyFitnessPlan remains a
general-wellness application and is not production-ready.

## Stage 9.2 React generation experience

Authenticated users now have separate browser-history routes for plan generation (`/plans/new`),
profile editing (`/profile`), and account settings (`/account`). The small route matcher uses the
native History API because these three static views do not yet justify another frontend dependency.
Normal links still contain real paths, modified clicks continue to behave like browser links, and
back/forward navigation updates the rendered view. Milestone 10 can extend the matcher for plan
history and plan-detail identifiers.

The generation view reloads the authenticated user's saved profile from the backend and shows the
goal, experience, schedule, equipment, dietary preferences, and constraints before enabling the
paid action. Generation uses the shared credentialed client, which copies the readable CSRF cookie
into the request header without reading the HttpOnly session cookie.

The interface distinguishes initial profile loading, missing profile, generation in progress,
profile scope rejection, provider unavailability, other generation failures, and success. A
successful transient result renders all workout sessions, exercise prescriptions, progression and
recovery guidance, meal templates, hydration, timing, and dietary-preference notes. A visible
general-wellness disclaimer remains alongside the action and result.

Generated output is intentionally held only in React memory in this stage. Refreshing the page
restores authentication and the saved profile but not the generated plan. Persistence, history,
active selection, and archiving remain Milestone 10 responsibilities.

## Stage 9.3 completed workflow

Milestone 9 now provides one complete transient generation path:

```text
authenticated session + CSRF proof
  -> authenticated user's saved profile
  -> deterministic profile safety assessment
  -> Python schedule calculations
  -> separated Claude request sections
  -> strict JSON and Pydantic validation
  -> deterministic generated-content safety assessment
  -> typed API response
  -> React workout and nutrition presentation
```

The repository owner manually confirmed the routed local interface and working behavior on August
17, 2026. Automated integration coverage exercises authentication, session-bound CSRF, ownership,
missing and unsafe profiles, calculated prompt data, provider unavailability and rejection,
malformed model output, generated-content rejection, successful typed API responses, and the rule
that Stage 9 creates no `plans` row. Frontend compilation checks the typed rendering boundary.
Provider behavior is mocked during automated checks, so those checks cannot consume Anthropic
credits or expose a real key.

Authentication restoration reloads the application user through `/auth/me`, and each routed view
then loads private data for that authenticated identity. A refresh therefore restores the session
and saved profile. The transient generated result is intentionally cleared because persistence is
not part of Milestone 9.

## Milestone 9 completion boundaries

- At Milestone 9 completion, generated plans were not stored. Stage 10.1 subsequently added backend
  persistence, history, details, active-plan selection, and archiving APIs.
- The deterministic text gate is a narrow defense-in-depth check, not a medical-safety classifier.
- Research retrieval, pgvector, source attribution, and citations are not implemented. Generated
  plans contain no claimed research citations.
- Automated checks do not make paid Claude requests. A real provider call should remain an explicit
  developer action because it consumes account credits.
- The application is a local professional working version, not a production-ready system.
- Broader UI polish remains deferred until the complete Milestone 10 working version is functional.
