import { useEffect, useState } from "react";

import { ApiError } from "../auth/api";
import { GeneratedPlanDisplay } from "../plan-generation/PlanGenerationView";
import { activatePlan, archivePlan, getPlan, type PersistedPlan } from "./api";
import { PlanStatusBadge } from "./PlanStatusBadge";

type DetailState =
  | { status: "loading" }
  | { status: "not-found" }
  | { status: "error"; message: string }
  | { status: "ready"; plan: PersistedPlan };

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "The plan request could not be completed.";
}

function listValue(values: string[]): string {
  return values.length === 0 ? "None specified" : values.join(", ");
}

export function PlanDetailView({ planId, onBack }: { planId: string; onBack: () => void }) {
  const [state, setState] = useState<DetailState>({ status: "loading" });
  const [pendingAction, setPendingAction] = useState<"activate" | "archive" | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void getPlan(planId)
      .then((plan) => {
        if (active) {
          setState({ status: "ready", plan });
        }
      })
      .catch((error: unknown) => {
        if (!active) {
          return;
        }
        setState(
          error instanceof ApiError && error.status === 404
            ? { status: "not-found" }
            : { status: "error", message: messageFromError(error) },
        );
      });
    return () => {
      active = false;
    };
  }, [planId]);

  async function handleActivate() {
    setPendingAction("activate");
    setActionError(null);
    try {
      setState({ status: "ready", plan: await activatePlan(planId) });
    } catch (error) {
      setActionError(messageFromError(error));
    } finally {
      setPendingAction(null);
    }
  }

  async function handleArchive() {
    if (!window.confirm("Archive this plan? Archived plans cannot be made active again.")) {
      return;
    }
    setPendingAction("archive");
    setActionError(null);
    try {
      setState({ status: "ready", plan: await archivePlan(planId) });
    } catch (error) {
      setActionError(messageFromError(error));
    } finally {
      setPendingAction(null);
    }
  }

  if (state.status === "loading") {
    return (
      <section aria-labelledby="plan-detail-heading">
        <h2 id="plan-detail-heading">Plan details</h2>
        <p className="mt-3 text-slate-600" role="status">
          Loading saved plan…
        </p>
      </section>
    );
  }

  if (state.status === "not-found") {
    return (
      <section aria-labelledby="plan-detail-heading">
        <h2 id="plan-detail-heading">Plan not found</h2>
        <p className="mt-2 text-sm text-slate-600">
          This plan does not exist or is not available to this account.
        </p>
        <button type="button" className="mt-4" onClick={onBack}>
          Return to plan history
        </button>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section aria-labelledby="plan-detail-heading">
        <h2 id="plan-detail-heading">Plan details</h2>
        <p className="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700" role="alert">
          {state.message}
        </p>
        <button type="button" className="mt-4" onClick={onBack}>
          Return to plan history
        </button>
      </section>
    );
  }

  const { plan } = state;
  const profile = plan.profile_snapshot.profile;
  const calculations = plan.profile_snapshot.calculated_values;

  return (
    <div className="space-y-6">
      <section aria-labelledby="plan-detail-heading" className="page-hero">
        <button type="button" className="button-secondary" onClick={onBack}>
          Back to plan history
        </button>
        <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 id="plan-detail-heading" className="text-3xl font-black tracking-tight">
                {plan.title}
              </h1>
              <PlanStatusBadge status={plan.status} />
            </div>
            <p className="mt-2 text-sm text-slate-500">
              Saved {new Date(plan.created_at).toLocaleString()}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {plan.status === "inactive" ? (
              <button
                type="button"
                className="button-secondary"
                disabled={pendingAction !== null}
                onClick={() => void handleActivate()}
              >
                {pendingAction === "activate" ? "Selecting…" : "Set active"}
              </button>
            ) : null}
            {plan.status !== "archived" ? (
              <button
                type="button"
                className="button-secondary"
                disabled={pendingAction !== null}
                onClick={() => void handleArchive()}
              >
                {pendingAction === "archive" ? "Archiving…" : "Archive plan"}
              </button>
            ) : null}
          </div>
        </div>
        {actionError === null ? null : (
          <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">
            {actionError}
          </p>
        )}
        {plan.status === "archived" ? (
          <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
            This plan is archived and cannot be selected as active again.
          </p>
        ) : null}
      </section>

      <section aria-labelledby="plan-snapshot-heading">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">Plan inputs</p>
        <h2 id="plan-snapshot-heading" className="mt-2">
          Generation snapshot
        </h2>
        <p className="mt-2 text-sm text-slate-600">
          These are the saved inputs and calculated schedule used to create this plan.
        </p>
        <dl className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <dt className="text-xs font-semibold uppercase text-slate-500">Goal</dt>
            <dd className="mt-1 text-sm">{profile.fitness_goal.replaceAll("_", " ")}</dd>
          </div>
          <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <dt className="text-xs font-semibold uppercase text-slate-500">Experience</dt>
            <dd className="mt-1 text-sm">{profile.experience_level}</dd>
          </div>
          <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <dt className="text-xs font-semibold uppercase text-slate-500">Schedule</dt>
            <dd className="mt-1 text-sm">
              {calculations.sessions_per_week} sessions · {calculations.minutes_per_session} minutes
            </dd>
          </div>
          <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <dt className="text-xs font-semibold uppercase text-slate-500">Equipment</dt>
            <dd className="mt-1 text-sm">{listValue(profile.equipment)}</dd>
          </div>
          <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <dt className="text-xs font-semibold uppercase text-slate-500">Diet</dt>
            <dd className="mt-1 text-sm">{listValue(profile.dietary_preferences)}</dd>
          </div>
          <div className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
            <dt className="text-xs font-semibold uppercase text-slate-500">Constraints</dt>
            <dd className="mt-1 text-sm">{listValue(profile.wellness_constraints)}</dd>
          </div>
        </dl>
      </section>

      <GeneratedPlanDisplay plan={plan} />

      <p className="rounded-xl border border-slate-200 bg-white p-4 text-xs leading-5 text-slate-500 shadow-sm">
        MyFitnessPlan provides general wellness information, not medical advice. Consult an
        appropriately qualified professional for medical care, injury treatment, rehabilitation, or
        individualized clinical nutrition advice.
      </p>
    </div>
  );
}
