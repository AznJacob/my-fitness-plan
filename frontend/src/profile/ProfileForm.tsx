import { useEffect, useState, type FormEvent } from "react";

import {
  getProfile,
  saveProfile,
  type ExperienceLevel,
  type FitnessGoal,
  type Profile,
} from "./api";

interface ProfileDraft {
  displayName: string;
  fitnessGoal: FitnessGoal;
  experienceLevel: ExperienceLevel;
  daysPerWeek: string;
  sessionMinutes: string;
  equipment: string;
  dietaryPreferences: string;
  wellnessConstraints: string;
}

const EMPTY_PROFILE: ProfileDraft = {
  displayName: "",
  fitnessGoal: "general_fitness",
  experienceLevel: "beginner",
  daysPerWeek: "3",
  sessionMinutes: "45",
  equipment: "",
  dietaryPreferences: "",
  wellnessConstraints: "",
};

function draftFromProfile(profile: Profile): ProfileDraft {
  return {
    displayName: profile.display_name ?? "",
    fitnessGoal: profile.fitness_goal,
    experienceLevel: profile.experience_level,
    daysPerWeek: String(profile.days_per_week),
    sessionMinutes: String(profile.session_minutes),
    equipment: profile.equipment.join("\n"),
    dietaryPreferences: profile.dietary_preferences.join("\n"),
    wellnessConstraints: profile.wellness_constraints.join("\n"),
  };
}

function listFromLines(value: string): string[] {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function profileFromDraft(draft: ProfileDraft): Profile {
  return {
    display_name: draft.displayName.trim() || null,
    fitness_goal: draft.fitnessGoal,
    experience_level: draft.experienceLevel,
    days_per_week: Number(draft.daysPerWeek),
    session_minutes: Number(draft.sessionMinutes),
    equipment: listFromLines(draft.equipment),
    dietary_preferences: listFromLines(draft.dietaryPreferences),
    wellness_constraints: listFromLines(draft.wellnessConstraints),
  };
}

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "The profile request could not be completed.";
}

export function ProfileForm() {
  const [draft, setDraft] = useState<ProfileDraft>(EMPTY_PROFILE);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [hasSavedProfile, setHasSavedProfile] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void getProfile()
      .then((profile) => {
        if (!active) {
          return;
        }
        if (profile !== null) {
          setDraft(draftFromProfile(profile));
          setHasSavedProfile(true);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(messageFromError(requestError));
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  function updateDraft<Key extends keyof ProfileDraft>(key: Key, value: ProfileDraft[Key]) {
    setDraft((current) => ({ ...current, [key]: value }));
    setSuccessMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const savedProfile = await saveProfile(profileFromDraft(draft));
      setDraft(draftFromProfile(savedProfile));
      setHasSavedProfile(true);
      setSuccessMessage("Profile saved.");
    } catch (requestError) {
      setError(messageFromError(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <section aria-labelledby="profile-heading">
        <h2 id="profile-heading">Your profile</h2>
        <p>Loading your profile…</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="profile-heading">
      <h2 id="profile-heading">{hasSavedProfile ? "Edit your profile" : "Create your profile"}</h2>
      <p className="mt-1 text-sm text-slate-600">
        Tell us about your general fitness preferences. This information does not replace medical
        advice.
      </p>
      <form
        className="mt-5 grid gap-x-6 sm:grid-cols-2"
        onSubmit={(event) => void handleSubmit(event)}
      >
        <p>
          <label htmlFor="display-name">Display name (optional)</label>
          <br />
          <input
            id="display-name"
            name="display-name"
            type="text"
            autoComplete="name"
            maxLength={100}
            value={draft.displayName}
            onChange={(event) => updateDraft("displayName", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="fitness-goal">Primary fitness goal</label>
          <br />
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
        <p>
          <label htmlFor="experience-level">Experience level</label>
          <br />
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
        <p>
          <label htmlFor="days-per-week">Available days per week</label>
          <br />
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
        <p>
          <label htmlFor="session-minutes">Minutes available per session</label>
          <br />
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
        <p>
          <label htmlFor="equipment">Available equipment (one item per line)</label>
          <br />
          <textarea
            id="equipment"
            name="equipment"
            rows={4}
            value={draft.equipment}
            onChange={(event) => updateDraft("equipment", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="dietary-preferences">Dietary preferences (one item per line)</label>
          <br />
          <textarea
            id="dietary-preferences"
            name="dietary-preferences"
            rows={4}
            value={draft.dietaryPreferences}
            onChange={(event) => updateDraft("dietaryPreferences", event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="wellness-constraints">
            Relevant general wellness constraints (one item per line)
          </label>
          <br />
          <textarea
            id="wellness-constraints"
            name="wellness-constraints"
            rows={4}
            value={draft.wellnessConstraints}
            onChange={(event) => updateDraft("wellnessConstraints", event.target.value)}
          />
        </p>
        {error === null ? null : (
          <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700 sm:col-span-2" role="alert">
            {error}
          </p>
        )}
        {successMessage === null ? null : (
          <p
            className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700 sm:col-span-2"
            role="status"
          >
            {successMessage}
          </p>
        )}
        <button className="w-fit sm:col-span-2" type="submit" disabled={submitting}>
          {submitting ? "Saving…" : "Save profile"}
        </button>
      </form>
    </section>
  );
}
