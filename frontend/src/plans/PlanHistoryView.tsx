import { useEffect, useState } from "react";

import { getPlanHistory, type PlanSummary } from "./api";
import { PlanStatusBadge } from "./PlanStatusBadge";

type HistoryState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; plans: PlanSummary[] };

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "Plan history could not be loaded.";
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

const PLAN_COLOR_CLASSES: Record<PlanSummary["fitness_goal"], string> = {
  strength: "border-orange-300 bg-orange-50/90",
  endurance: "border-emerald-300 bg-emerald-50/90",
  muscle_gain: "border-amber-300 bg-amber-50/90",
  general_fitness: "border-indigo-300 bg-indigo-50/90",
  weight_management: "border-sky-300 bg-sky-50/90",
};

const ACTIVE_PLAN_COLOR_CLASSES: Record<PlanSummary["fitness_goal"], string> = {
  strength: "border-orange-800 bg-gradient-to-r from-orange-950 to-amber-900",
  endurance: "border-emerald-800 bg-gradient-to-r from-emerald-950 to-teal-900",
  muscle_gain: "border-amber-800 bg-gradient-to-r from-amber-950 to-orange-900",
  general_fitness: "border-indigo-800 bg-gradient-to-r from-indigo-950 to-slate-900",
  weight_management: "border-sky-800 bg-gradient-to-r from-sky-950 to-cyan-900",
};

function formatGoal(goal: PlanSummary["fitness_goal"]): string {
  return goal.replaceAll("_", " ");
}

export function PlanHistoryView({
  onGenerate,
  onViewPlan,
}: {
  onGenerate: () => void;
  onViewPlan: (planId: string) => void;
}) {
  const [state, setState] = useState<HistoryState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    void getPlanHistory()
      .then((plans) => {
        if (active) {
          setState({ status: "ready", plans });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({ status: "error", message: messageFromError(error) });
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (state.status === "loading") {
    return (
      <section aria-labelledby="plan-history-heading">
        <h2 id="plan-history-heading">Plan history</h2>
        <p className="mt-3 text-slate-600" role="status">
          Loading saved plans…
        </p>
      </section>
    );
  }

  if (state.status === "error") {
    return (
      <section aria-labelledby="plan-history-heading">
        <h2 id="plan-history-heading">Plan history</h2>
        <p className="mt-4 rounded-lg bg-red-50 p-4 text-sm text-red-700" role="alert">
          {state.message}
        </p>
      </section>
    );
  }

  const activePlan = state.plans.find((plan) => plan.status === "active");

  return (
    <div className="space-y-6">
      <div className="px-1">
        <div>
          <h1 id="plan-history-heading" className="text-3xl font-black tracking-tight sm:text-4xl">
            Plan history
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600 sm:text-base">
            View and manage your previously generated plans.
          </p>
        </div>
      </div>

      {activePlan === undefined ? (
        <section aria-labelledby="active-plan-heading" className="border-dashed bg-slate-50/70">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">
            Active plan
          </p>
          <h2 id="active-plan-heading" className="mt-2">
            No active plan
          </h2>
          <p className="mt-2 text-sm text-slate-600">
            Select a saved plan below to set it as active.
          </p>
        </section>
      ) : (
        <section
          aria-labelledby="active-plan-heading"
          className={`overflow-hidden text-white ${ACTIVE_PLAN_COLOR_CLASSES[activePlan.fitness_goal]}`}
        >
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-white/70">
                Active plan · {formatGoal(activePlan.fitness_goal)}
              </p>
              <h2 id="active-plan-heading" className="mt-2 text-2xl">
                {activePlan.title}
              </h2>
            </div>
            <button
              type="button"
              className="bg-white text-slate-950 hover:bg-slate-100"
              onClick={() => onViewPlan(activePlan.id)}
            >
              View active plan
            </button>
          </div>
        </section>
      )}

      <section aria-labelledby="all-plans-heading">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">
              Plan history
            </p>
            <h2 id="all-plans-heading" className="mt-2">
              All saved plans
            </h2>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
            {state.plans.length} {state.plans.length === 1 ? "plan" : "plans"}
          </span>
        </div>
        {state.plans.length === 0 ? (
          <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center">
            <p className="font-semibold text-slate-800">No saved plans</p>
            <p className="mt-2 text-sm text-slate-600">
              Generate a plan to add it to your history.
            </p>
            <button type="button" className="mt-5" onClick={onGenerate}>
              Generate your first plan
            </button>
          </div>
        ) : (
          <ul className="mt-5 grid gap-4 md:grid-cols-2">
            {state.plans.map((plan) => (
              <li
                key={plan.id}
                className={`flex min-h-48 flex-col rounded-2xl border p-5 transition hover:-translate-y-0.5 hover:shadow-lg ${
                  plan.status === "active"
                    ? `${PLAN_COLOR_CLASSES[plan.fitness_goal]} shadow-md ring-2 ring-emerald-500/30`
                    : `${PLAN_COLOR_CLASSES[plan.fitness_goal]} shadow-sm`
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="text-xs font-bold uppercase tracking-[0.14em] text-slate-600">
                    {formatGoal(plan.fitness_goal)}
                  </span>
                  <PlanStatusBadge status={plan.status} />
                </div>
                <h3 className="mt-5 text-lg">{plan.title}</h3>
                <p className="mt-2 text-xs text-slate-500">
                  Generated {formatDate(plan.created_at)}
                </p>
                <button
                  type="button"
                  className="button-secondary mt-auto w-full"
                  onClick={() => onViewPlan(plan.id)}
                >
                  View plan
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
