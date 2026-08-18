import { csrfProtectedMutation } from "../auth/api";
import type { PersistedPlan } from "../plans/api";

export interface LegacyExercisePrescription {
  name: string;
  sets: number | null;
  repetitions: string | null;
  duration_seconds: number | null;
  rest_seconds: number;
  instructions: string;
}

export interface LegacyWorkoutSession {
  day_label: string;
  focus: string;
  duration_minutes: number;
  warm_up: LegacyExercisePrescription[];
  main_workout: LegacyExercisePrescription[];
  cool_down: LegacyExercisePrescription[];
}

export interface LegacyWorkoutPlan {
  summary: string;
  sessions: LegacyWorkoutSession[];
  progression_guidance: string;
  recovery_guidance: string;
}

export interface LegacyMealSuggestion {
  meal_name: string;
  foods: string[];
  guidance: string;
}

export interface LegacyDailyNutritionTemplate {
  day_label: string;
  meals: LegacyMealSuggestion[];
}

export interface LegacyNutritionPlan {
  summary: string;
  daily_templates: LegacyDailyNutritionTemplate[];
  hydration_guidance: string;
  meal_timing_guidance: string;
  dietary_preference_notes: string;
}

export interface LegacyGeneratedPlan {
  schema_version: 1;
  title: string;
  overview: string;
  workout_plan: LegacyWorkoutPlan;
  nutrition_plan: LegacyNutritionPlan;
}

export interface ExercisePrescription {
  name: string;
  prescription: string;
}

export interface WorkoutSession {
  day_label: string;
  focus: string;
  duration_minutes: number;
  exercises: ExercisePrescription[];
}

export interface WorkoutPlan {
  sessions: WorkoutSession[];
  progression_guidance: string;
  recovery_guidance: string;
}

export interface MealSuggestion {
  meal_name: string;
  foods: string[];
}

export interface NutritionPlan {
  meal_ideas: MealSuggestion[];
  daily_guidance: string;
  hydration_guidance: string;
}

export interface CompactGeneratedPlan {
  schema_version: 2;
  title: string;
  overview: string;
  workout_plan: WorkoutPlan;
  nutrition_plan: NutritionPlan;
}

export type GeneratedPlan = LegacyGeneratedPlan | CompactGeneratedPlan;

export type FitnessGoal =
  "general_fitness" | "strength" | "muscle_gain" | "endurance" | "weight_management";

export type ExperienceLevel = "beginner" | "intermediate" | "advanced";

export interface PlanningPreferences {
  fitness_goal: FitnessGoal;
  experience_level: ExperienceLevel;
  days_per_week: number;
  session_minutes: number;
  equipment: string[];
  dietary_preferences: string[];
  wellness_constraints: string[];
}

export async function generatePlan(preferences: PlanningPreferences): Promise<PersistedPlan> {
  const response = await csrfProtectedMutation("/plans/generate", "POST", preferences);
  return (await response.json()) as PersistedPlan;
}
