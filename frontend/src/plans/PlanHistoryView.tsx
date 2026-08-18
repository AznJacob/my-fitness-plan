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
      <section aria-labelledby="plan-history-heading">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 id="plan-history-heading">Plan history</h2>
            <p className="mt-2 text-sm text-slate-600">
              Review saved plans, select one as active, or retain older plans as archived history.
            </p>
          </div>
          <button type="button" className="w-fit" onClick={onGenerate}>
            Generate new plan
          </button>
        </div>
      </section>

      {activePlan === undefined ? (
        <section aria-labelledby="active-plan-heading">
          <h2 id="active-plan-heading">Active plan</h2>
          <p className="mt-2 text-sm text-slate-600">No plan is currently selected as active.</p>
        </section>
      ) : (
        <section aria-labelledby="active-plan-heading" className="border-emerald-200 bg-emerald-50">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="active-plan-heading">Active plan</h2>
              <p className="mt-1 text-slate-700">{activePlan.title}</p>
            </div>
            <button type="button" onClick={() => onViewPlan(activePlan.id)}>
              View active plan
            </button>
          </div>
        </section>
      )}

      <section aria-labelledby="all-plans-heading">
        <h2 id="all-plans-heading">All saved plans</h2>
        {state.plans.length === 0 ? (
          <div className="mt-4 rounded-lg bg-slate-50 p-4">
            <p className="text-sm text-slate-600">You have not generated a plan yet.</p>
            <button type="button" className="mt-3" onClick={onGenerate}>
              Generate your first plan
            </button>
          </div>
        ) : (
          <ul className="mt-4 space-y-3">
            {state.plans.map((plan) => (
              <li
                key={plan.id}
                className={`rounded-xl border p-4 ${
                  plan.status === "active"
                    ? "border-emerald-300 bg-emerald-50"
                    : "border-slate-200 bg-white"
                }`}
              >
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h3>{plan.title}</h3>
                      <PlanStatusBadge status={plan.status} />
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      Generated {formatDate(plan.created_at)}
                    </p>
                  </div>
                  <button type="button" className="w-fit" onClick={() => onViewPlan(plan.id)}>
                    View details
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
