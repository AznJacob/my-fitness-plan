import { useEffect, useState } from "react";

import { ApiError } from "../auth/api";
import { getProfile, type Profile } from "../profile/api";
import {
  generatePlan,
  type ExercisePrescription,
  type GeneratedPlan,
  type WorkoutSession,
} from "./api";

type ProfileState =
  | { status: "loading" }
  | { status: "missing" }
  | { status: "error"; message: string }
  | { status: "ready"; profile: Profile };

type GenerationState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; plan: GeneratedPlan }
  | { status: "validation-error"; message: string }
  | { status: "provider-unavailable"; message: string }
  | { status: "error"; message: string };

const LABELS: Record<string, string> = {
  general_fitness: "General fitness",
  strength: "Strength",
  muscle_gain: "Muscle gain",
  endurance: "Endurance",
  weight_management: "Weight management",
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
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

function ProfileSummary({ profile }: { profile: Profile }) {
  const listValue = (values: string[]) =>
    values.length === 0 ? "None specified" : values.join(", ");

  return (
    <div className="mt-5">
      <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <SummaryItem label="Goal" value={LABELS[profile.fitness_goal]} />
        <SummaryItem label="Experience" value={LABELS[profile.experience_level]} />
        <SummaryItem
          label="Schedule"
          value={`${profile.days_per_week} days × ${profile.session_minutes} minutes`}
        />
        <SummaryItem label="Equipment" value={listValue(profile.equipment)} />
        <SummaryItem label="Diet" value={listValue(profile.dietary_preferences)} />
        <SummaryItem label="Constraints" value={listValue(profile.wellness_constraints)} />
      </dl>
    </div>
  );
}

function ExerciseList({ exercises }: { exercises: ExercisePrescription[] }) {
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

function WorkoutSessionCard({ session }: { session: WorkoutSession }) {
  return (
    <article className="rounded-xl border border-slate-200 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h4 className="font-semibold text-slate-900">
          {session.day_label}: {session.focus}
        </h4>
        <span className="text-sm text-slate-500">{session.duration_minutes} minutes</span>
      </div>
      <h5 className="mt-4 text-sm font-semibold text-slate-700">Warm-up</h5>
      <ExerciseList exercises={session.warm_up} />
      <h5 className="mt-4 text-sm font-semibold text-slate-700">Main workout</h5>
      <ExerciseList exercises={session.main_workout} />
      <h5 className="mt-4 text-sm font-semibold text-slate-700">Cool-down</h5>
      <ExerciseList exercises={session.cool_down} />
    </article>
  );
}

function GeneratedPlanDisplay({ plan }: { plan: GeneratedPlan }) {
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
            <WorkoutSessionCard key={`${session.day_label}-${index}`} session={session} />
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

export function PlanGenerationView({ onEditProfile }: { onEditProfile: () => void }) {
  const [profileState, setProfileState] = useState<ProfileState>({ status: "loading" });
  const [generationState, setGenerationState] = useState<GenerationState>({ status: "idle" });

  useEffect(() => {
    let active = true;
    void getProfile()
      .then((profile) => {
        if (active) {
          setProfileState(profile === null ? { status: "missing" } : { status: "ready", profile });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setProfileState({ status: "error", message: messageFromError(error) });
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleGenerate() {
    setGenerationState({ status: "loading" });
    try {
      setGenerationState({ status: "success", plan: await generatePlan() });
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "missing_profile") {
          setProfileState({ status: "missing" });
          setGenerationState({ status: "idle" });
          return;
        }
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
      <section aria-labelledby="plan-generation-heading">
        <h2 id="plan-generation-heading">Generate your plan</h2>
        <p className="mt-2 text-sm text-slate-600">
          Review the saved profile Claude will use. Generation may take up to a minute.
        </p>

        {profileState.status === "loading" ? (
          <p className="mt-5 text-slate-600" role="status">
            Loading your saved profile…
          </p>
        ) : profileState.status === "missing" ? (
          <div className="mt-5 rounded-lg bg-amber-50 p-4 text-amber-900" role="status">
            <p className="font-medium">Create a profile before generating a plan.</p>
            <button type="button" className="mt-3" onClick={onEditProfile}>
              Create profile
            </button>
          </div>
        ) : profileState.status === "error" ? (
          <p className="mt-5 rounded-lg bg-red-50 p-4 text-sm text-red-700" role="alert">
            {profileState.message}
          </p>
        ) : (
          <>
            <ProfileSummary profile={profileState.profile} />
            <div className="mt-5 flex flex-wrap gap-3">
              <button
                type="button"
                disabled={generationState.status === "loading"}
                onClick={() => void handleGenerate()}
              >
                {generationState.status === "loading" ? "Generating…" : "Generate plan"}
              </button>
              <button
                type="button"
                className="border border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
                disabled={generationState.status === "loading"}
                onClick={onEditProfile}
              >
                Edit profile
              </button>
            </div>
          </>
        )}

        {generationState.status === "loading" ? (
          <p className="mt-5 rounded-lg bg-blue-50 p-4 text-sm text-blue-800" role="status">
            Claude is creating and validating your plan…
          </p>
        ) : generationState.status === "validation-error" ? (
          <div className="mt-5 rounded-lg bg-amber-50 p-4 text-sm text-amber-900" role="alert">
            <p>{generationState.message}</p>
            <button type="button" className="mt-3" onClick={onEditProfile}>
              Review profile
            </button>
          </div>
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
        <GeneratedPlanDisplay plan={generationState.plan} />
      ) : null}
    </div>
  );
}
