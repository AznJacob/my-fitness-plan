import { useState, type FormEvent } from "react";

import { ApiError } from "../auth/api";
import {
  generatePlan,
  type ExperienceLevel,
  type ExercisePrescription,
  type FitnessGoal,
  type GeneratedPlan,
  type LegacyExercisePrescription,
  type LegacyGeneratedPlan,
  type LegacyWorkoutSession,
  type PlanningPreferences,
  type WorkoutSession,
} from "./api";
import type { PersistedPlan } from "../plans/api";

type GenerationState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; plan: PersistedPlan }
  | { status: "validation-error"; message: string }
  | { status: "provider-unavailable"; message: string }
  | { status: "error"; message: string };

interface PreferencesDraft {
  fitnessGoal: FitnessGoal;
  experienceLevel: ExperienceLevel;
  daysPerWeek: string;
  sessionMinutes: string;
  equipment: string;
  dietaryPreferences: string;
  wellnessConstraints: string;
}

const INITIAL_PREFERENCES: PreferencesDraft = {
  fitnessGoal: "general_fitness",
  experienceLevel: "beginner",
  daysPerWeek: "3",
  sessionMinutes: "45",
  equipment: "",
  dietaryPreferences: "",
  wellnessConstraints: "",
};

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "The request could not be completed.";
}

function SummaryItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm text-slate-900">{value}</dd>
    </div>
  );
}

function listFromLines(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function preferencesFromDraft(draft: PreferencesDraft): PlanningPreferences {
  return {
    fitness_goal: draft.fitnessGoal,
    experience_level: draft.experienceLevel,
    days_per_week: Number(draft.daysPerWeek),
    session_minutes: Number(draft.sessionMinutes),
    equipment: listFromLines(draft.equipment),
    dietary_preferences: listFromLines(draft.dietaryPreferences),
    wellness_constraints: listFromLines(draft.wellnessConstraints),
  };
}

function LegacyExerciseList({ exercises }: { exercises: LegacyExercisePrescription[] }) {
  return (
    <ul className="mt-2 space-y-2">
      {exercises.map((exercise, index) => {
        const prescription = [
          exercise.sets === null ? null : `${exercise.sets} sets`,
          exercise.repetitions,
          exercise.duration_seconds === null ? null : `${exercise.duration_seconds} seconds`,
          `${exercise.rest_seconds} seconds rest`,
        ]
          .filter((value) => value !== null)
          .join(" · ");
        return (
          <li key={`${exercise.name}-${index}`} className="rounded-lg bg-slate-50 p-3">
            <p className="font-medium text-slate-900">{exercise.name}</p>
            <p className="mt-1 text-xs font-medium text-slate-500">{prescription}</p>
            <p className="mt-1 text-sm text-slate-700">{exercise.instructions}</p>
          </li>
        );
      })}
    </ul>
  );
}

function LegacyWorkoutSessionCard({ session }: { session: LegacyWorkoutSession }) {
  return (
    <article className="rounded-xl border border-slate-200 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="font-semibold text-slate-900">
          {session.day_label}: {session.focus}
        </h4>
        <span className="text-sm text-slate-500">{session.duration_minutes} minutes</span>
      </div>
      <h5 className="mt-4 text-sm font-semibold text-slate-700">Warm-up</h5>
      <LegacyExerciseList exercises={session.warm_up} />
      <h5 className="mt-4 text-sm font-semibold text-slate-700">Main workout</h5>
      <LegacyExerciseList exercises={session.main_workout} />
      <h5 className="mt-4 text-sm font-semibold text-slate-700">Cool-down</h5>
      <LegacyExerciseList exercises={session.cool_down} />
    </article>
  );
}

function LegacyGeneratedPlanDisplay({ plan }: { plan: LegacyGeneratedPlan }) {
  return (
    <div className="space-y-6">
      <section aria-labelledby="generated-plan-heading">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">
          Generated plan
        </p>
        <h2 id="generated-plan-heading" className="mt-1">
          {plan.title}
        </h2>
        <p className="mt-3 text-slate-700">{plan.overview}</p>
      </section>

      <section aria-labelledby="workout-plan-heading">
        <h2 id="workout-plan-heading">Workout plan</h2>
        <p className="mt-2 text-slate-700">{plan.workout_plan.summary}</p>
        <div className="mt-5 space-y-4">
          {plan.workout_plan.sessions.map((session, index) => (
            <LegacyWorkoutSessionCard key={`${session.day_label}-${index}`} session={session} />
          ))}
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <SummaryItem label="Progression" value={plan.workout_plan.progression_guidance} />
          <SummaryItem label="Recovery" value={plan.workout_plan.recovery_guidance} />
        </div>
      </section>

      <section aria-labelledby="nutrition-plan-heading">
        <h2 id="nutrition-plan-heading">Nutrition plan</h2>
        <p className="mt-2 text-slate-700">{plan.nutrition_plan.summary}</p>
        <div className="mt-5 space-y-4">
          {plan.nutrition_plan.daily_templates.map((template, templateIndex) => (
            <article
              key={`${template.day_label}-${templateIndex}`}
              className="rounded-xl border border-slate-200 p-4"
            >
              <h4 className="font-semibold text-slate-900">{template.day_label}</h4>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                {template.meals.map((meal, mealIndex) => (
                  <div
                    key={`${meal.meal_name}-${mealIndex}`}
                    className="rounded-lg bg-slate-50 p-3"
                  >
                    <h5 className="font-medium text-slate-900">{meal.meal_name}</h5>
                    <p className="mt-1 text-sm text-slate-700">{meal.foods.join(", ")}</p>
                    <p className="mt-2 text-sm text-slate-600">{meal.guidance}</p>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <SummaryItem label="Hydration" value={plan.nutrition_plan.hydration_guidance} />
          <SummaryItem label="Meal timing" value={plan.nutrition_plan.meal_timing_guidance} />
          <SummaryItem
            label="Dietary preferences"
            value={plan.nutrition_plan.dietary_preference_notes}
          />
        </div>
      </section>
    </div>
  );
}

function CompactExerciseList({ exercises }: { exercises: ExercisePrescription[] }) {
  return (
    <ul className="mt-3 space-y-2">
      {exercises.map((exercise, index) => (
        <li key={`${exercise.name}-${index}`} className="rounded-lg bg-slate-50 p-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <p className="font-medium text-slate-900">{exercise.name}</p>
            <p className="text-xs font-semibold text-slate-500">{exercise.prescription}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function CompactWorkoutSessionCard({ session }: { session: WorkoutSession }) {
  return (
    <article className="rounded-xl border border-slate-200 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="font-semibold text-slate-900">
          {session.day_label}: {session.focus}
        </h4>
        <span className="text-sm text-slate-500">{session.duration_minutes} minutes</span>
      </div>
      <CompactExerciseList exercises={session.exercises} />
    </article>
  );
}

function CompactGeneratedPlanDisplay({
  plan,
}: {
  plan: Extract<GeneratedPlan, { schema_version: 2 }>;
}) {
  return (
    <div className="space-y-6">
      <section aria-labelledby="generated-plan-heading">
        <p className="text-sm font-semibold uppercase tracking-wide text-blue-700">
          Generated plan
        </p>
        <h2 id="generated-plan-heading" className="mt-1">
          {plan.title}
        </h2>
        <p className="mt-3 text-slate-700">{plan.overview}</p>
      </section>
      <section aria-labelledby="workout-plan-heading">
        <h2 id="workout-plan-heading">Workout plan</h2>
        <div className="mt-5 space-y-4">
          {plan.workout_plan.sessions.map((session, index) => (
            <CompactWorkoutSessionCard key={`${session.day_label}-${index}`} session={session} />
          ))}
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <SummaryItem label="Progression" value={plan.workout_plan.progression_guidance} />
          <SummaryItem label="Recovery" value={plan.workout_plan.recovery_guidance} />
        </div>
      </section>
      <section aria-labelledby="nutrition-plan-heading">
        <h2 id="nutrition-plan-heading">Nutrition ideas</h2>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {plan.nutrition_plan.meal_ideas.map((meal, index) => (
            <article key={`${meal.meal_name}-${index}`} className="rounded-lg bg-slate-50 p-3">
              <h3 className="font-medium text-slate-900">{meal.meal_name}</h3>
              <p className="mt-1 text-sm text-slate-700">{meal.foods.join(", ")}</p>
            </article>
          ))}
        </div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <SummaryItem label="Daily guidance" value={plan.nutrition_plan.daily_guidance} />
          <SummaryItem label="Hydration" value={plan.nutrition_plan.hydration_guidance} />
        </div>
      </section>
    </div>
  );
}

export function GeneratedPlanDisplay({ plan }: { plan: GeneratedPlan }) {
  return plan.schema_version === 1 ? (
    <LegacyGeneratedPlanDisplay plan={plan} />
  ) : (
    <CompactGeneratedPlanDisplay plan={plan} />
  );
}

export function PlanGenerationView({ onViewPlan }: { onViewPlan: (planId: string) => void }) {
  const [draft, setDraft] = useState<PreferencesDraft>(INITIAL_PREFERENCES);
  const [generationState, setGenerationState] = useState<GenerationState>({ status: "idle" });

  function updateDraft<Key extends keyof PreferencesDraft>(key: Key, value: PreferencesDraft[Key]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  async function handleGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setGenerationState({ status: "loading" });
    try {
      setGenerationState({
        status: "success",
        plan: await generatePlan(preferencesFromDraft(draft)),
      });
    } catch (error) {
      if (error instanceof ApiError) {
        if (
          error.code === "unsafe_profile" ||
          error.code === "invalid_model_output" ||
          error.code === "unsafe_model_output"
        ) {
          setGenerationState({ status: "validation-error", message: error.message });
          return;
        }
        if (error.code === "claude_unavailable" || error.code === "provider_unavailable") {
          setGenerationState({ status: "provider-unavailable", message: error.message });
          return;
        }
      }
      setGenerationState({ status: "error", message: messageFromError(error) });
    }
  }

  return (
    <div className="space-y-6">
      <section aria-labelledby="plan-generation-heading" className="page-hero">
        <p className="page-eyebrow">Plan builder</p>
        <h1
          id="plan-generation-heading"
          className="mt-3 text-3xl font-black tracking-tight sm:text-4xl"
        >
          Build a plan that fits your week.
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
          Choose the goals, schedule, and preferences for this plan. These choices are used for this
          generation only and are not saved to your account.
        </p>
        <div className="mt-7 grid max-w-xl grid-cols-3 gap-3 text-left">
          {[
            ["01", "Your goal"],
            ["02", "Your schedule"],
            ["03", "Your preferences"],
          ].map(([number, label]) => (
            <div key={number} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <span className="block text-xs font-bold text-indigo-600">{number}</span>
              <span className="mt-1 block text-xs font-medium text-slate-600 sm:text-sm">
                {label}
              </span>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="preferences-heading">
        <div className="max-w-2xl">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">
            Plan preferences
          </p>
          <h2 id="preferences-heading" className="mt-2">
            Tell us what works for you
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            There are no perfect answers. Choose what feels realistic for the week ahead.
          </p>
        </div>

        <form
          className="mt-7 grid gap-4 sm:grid-cols-2"
          onSubmit={(event) => void handleGenerate(event)}
        >
          <p className="mb-0 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <label htmlFor="fitness-goal">Primary fitness goal</label>
            <select
              id="fitness-goal"
              name="fitness-goal"
              value={draft.fitnessGoal}
              onChange={(event) => updateDraft("fitnessGoal", event.target.value as FitnessGoal)}
            >
              <option value="general_fitness">General fitness</option>
              <option value="strength">Strength</option>
              <option value="muscle_gain">Muscle gain</option>
              <option value="endurance">Endurance</option>
              <option value="weight_management">Weight management</option>
            </select>
          </p>
          <p className="mb-0 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <label htmlFor="experience-level">Experience level</label>
            <select
              id="experience-level"
              name="experience-level"
              value={draft.experienceLevel}
              onChange={(event) =>
                updateDraft("experienceLevel", event.target.value as ExperienceLevel)
              }
            >
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </p>
          <p className="mb-0 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <label htmlFor="days-per-week">Available days per week</label>
            <input
              id="days-per-week"
              name="days-per-week"
              type="number"
              min={1}
              max={7}
              required
              value={draft.daysPerWeek}
              onChange={(event) => updateDraft("daysPerWeek", event.target.value)}
            />
          </p>
          <p className="mb-0 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <label htmlFor="session-minutes">Minutes available per session</label>
            <input
              id="session-minutes"
              name="session-minutes"
              type="number"
              min={10}
              max={180}
              required
              value={draft.sessionMinutes}
              onChange={(event) => updateDraft("sessionMinutes", event.target.value)}
            />
          </p>
          <p className="mb-0 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <label htmlFor="equipment">Available equipment (one item per line)</label>
            <textarea
              id="equipment"
              name="equipment"
              rows={4}
              value={draft.equipment}
              onChange={(event) => updateDraft("equipment", event.target.value)}
            />
          </p>
          <p className="mb-0 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <label htmlFor="dietary-preferences">Dietary preferences (one item per line)</label>
            <textarea
              id="dietary-preferences"
              name="dietary-preferences"
              rows={4}
              value={draft.dietaryPreferences}
              onChange={(event) => updateDraft("dietaryPreferences", event.target.value)}
            />
          </p>
          <p className="mb-0 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70 sm:col-span-2">
            <label htmlFor="wellness-constraints">
              Relevant general wellness constraints (one item per line)
            </label>
            <textarea
              id="wellness-constraints"
              name="wellness-constraints"
              rows={3}
              value={draft.wellnessConstraints}
              onChange={(event) => updateDraft("wellnessConstraints", event.target.value)}
            />
          </p>
          <button
            type="submit"
            className="mt-2 w-full py-3.5 text-base sm:col-span-2"
            disabled={generationState.status === "loading"}
          >
            {generationState.status === "loading" ? "Generating…" : "Generate plan"}
          </button>
        </form>

        {generationState.status === "loading" ? (
          <p className="mt-5 rounded-lg bg-blue-50 p-4 text-sm text-blue-800" role="status">
            Creating and validating your personalized plan…
          </p>
        ) : generationState.status === "validation-error" ? (
          <p className="mt-5 rounded-lg bg-amber-50 p-4 text-sm text-amber-900" role="alert">
            {generationState.message} Review the planning preferences above and try again.
          </p>
        ) : generationState.status === "provider-unavailable" ? (
          <p className="mt-5 rounded-lg bg-amber-50 p-4 text-sm text-amber-900" role="alert">
            {generationState.message} Please try again later.
          </p>
        ) : generationState.status === "error" ? (
          <p className="mt-5 rounded-lg bg-red-50 p-4 text-sm text-red-700" role="alert">
            {generationState.message}
          </p>
        ) : null}

        <p className="mt-5 border-t border-slate-200 pt-4 text-xs leading-5 text-slate-500">
          MyFitnessPlan provides general wellness information, not medical advice. Stop activities
          that cause pain and consult an appropriately qualified professional for medical care,
          injury treatment, rehabilitation, or individualized clinical nutrition advice.
        </p>
      </section>

      {generationState.status === "success" ? (
        <>
          <section
            aria-labelledby="saved-plan-heading"
            className="border-emerald-200 bg-gradient-to-r from-emerald-50 to-lime-50"
          >
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 id="saved-plan-heading">Plan saved</h2>
                <p className="mt-1 text-sm text-emerald-900">
                  This plan is inactive until you choose to make it your active plan.
                </p>
              </div>
              <button type="button" onClick={() => onViewPlan(generationState.plan.id)}>
                Manage saved plan
              </button>
            </div>
          </section>
          <GeneratedPlanDisplay plan={generationState.plan} />
        </>
      ) : null}
    </div>
  );
}
