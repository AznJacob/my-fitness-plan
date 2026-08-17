import { ApiError, apiRequest, csrfProtectedMutation } from "../auth/api";

export type FitnessGoal =
  "general_fitness" | "strength" | "muscle_gain" | "endurance" | "weight_management";

export type ExperienceLevel = "beginner" | "intermediate" | "advanced";

export interface Profile {
  display_name: string | null;
  fitness_goal: FitnessGoal;
  experience_level: ExperienceLevel;
  days_per_week: number;
  session_minutes: number;
  equipment: string[];
  dietary_preferences: string[];
  wellness_constraints: string[];
}

export async function getProfile(): Promise<Profile | null> {
  try {
    const response = await apiRequest("/profile");
    return (await response.json()) as Profile;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

export async function saveProfile(profile: Profile): Promise<Profile> {
  const response = await csrfProtectedMutation("/profile", "PUT", profile);
  return (await response.json()) as Profile;
}
