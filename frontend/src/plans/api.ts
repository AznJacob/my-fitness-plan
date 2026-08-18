import { apiRequest, csrfProtectedMutation } from "../auth/api";
import type { FitnessGoal, GeneratedPlan, PlanningPreferences } from "../plan-generation/api";

export type PlanStatus = "inactive" | "active" | "archived";

export interface WellnessCalculationResult {
  calculation_version: 1;
  sessions_per_week: number;
  minutes_per_session: number;
  weekly_available_minutes: number;
  non_training_days_per_week: number;
}

export interface PlanProfileSnapshot {
  profile: PlanningPreferences;
  calculated_values: WellnessCalculationResult;
}

export interface PlanSummary {
  id: string;
  title: string;
  fitness_goal: FitnessGoal;
  status: PlanStatus;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
}

export type PersistedPlan = GeneratedPlan &
  PlanSummary & {
    profile_snapshot: PlanProfileSnapshot;
  };

export async function getPlanHistory(): Promise<PlanSummary[]> {
  const response = await apiRequest("/plans");
  return (await response.json()) as PlanSummary[];
}

export async function getPlan(planId: string): Promise<PersistedPlan> {
  const response = await apiRequest(`/plans/${encodeURIComponent(planId)}`);
  return (await response.json()) as PersistedPlan;
}

export async function activatePlan(planId: string): Promise<PersistedPlan> {
  const response = await csrfProtectedMutation(
    `/plans/${encodeURIComponent(planId)}/activate`,
    "POST",
  );
  return (await response.json()) as PersistedPlan;
}

export async function archivePlan(planId: string): Promise<PersistedPlan> {
  const response = await csrfProtectedMutation(
    `/plans/${encodeURIComponent(planId)}/archive`,
    "POST",
  );
  return (await response.json()) as PersistedPlan;
}
