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

## Current limitations

Stage 9.1 exposes only the backend generation workflow. The React generation experience and routed
navigation belong to Stage 9.2. End-to-end browser and authorized live-provider verification belong
to Stage 9.3. Generated plans are transient until Milestone 10 adds persistence and lifecycle APIs.

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
