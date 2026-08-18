import { csrfProtectedMutation } from "../auth/api";

export interface ExercisePrescription {
  name: string;
  sets: number | null;
  repetitions: string | null;
  duration_seconds: number | null;
  rest_seconds: number;
  instructions: string;
}

export interface WorkoutSession {
  day_label: string;
  focus: string;
  duration_minutes: number;
  warm_up: ExercisePrescription[];
  main_workout: ExercisePrescription[];
  cool_down: ExercisePrescription[];
}

export interface WorkoutPlan {
  summary: string;
  sessions: WorkoutSession[];
  progression_guidance: string;
  recovery_guidance: string;
}

export interface MealSuggestion {
  meal_name: string;
  foods: string[];
  guidance: string;
}

export interface DailyNutritionTemplate {
  day_label: string;
  meals: MealSuggestion[];
}

export interface NutritionPlan {
  summary: string;
  daily_templates: DailyNutritionTemplate[];
  hydration_guidance: string;
  meal_timing_guidance: string;
  dietary_preference_notes: string;
}

export interface GeneratedPlan {
  schema_version: 1;
  title: string;
  overview: string;
  workout_plan: WorkoutPlan;
  nutrition_plan: NutritionPlan;
}

export async function generatePlan(): Promise<GeneratedPlan> {
  const response = await csrfProtectedMutation("/plans/generate", "POST");
  return (await response.json()) as GeneratedPlan;
}
