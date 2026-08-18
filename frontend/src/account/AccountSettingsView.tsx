import { useEffect, useState, type FormEvent } from "react";

import { AccountLinking } from "../auth/AccountLinking";
import { getAccountDetails, saveAccountDetails, type AccountDetails } from "./api";

interface AccountDraft {
  username: string;
  heightCm: string;
  weightKg: string;
}

const EMPTY_DRAFT: AccountDraft = { username: "", heightCm: "", weightKg: "" };

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "The account request could not be completed.";
}

function draftFromDetails(details: AccountDetails): AccountDraft {
  return {
    username: details.username ?? "",
    heightCm: details.height_cm ?? "",
    weightKg: details.weight_kg ?? "",
  };
}

export function AccountSettingsView({
  email,
  error: authenticationError,
  logout,
}: {
  email: string;
  error: string | null;
  logout: () => Promise<void>;
}) {
  const [draft, setDraft] = useState<AccountDraft>(EMPTY_DRAFT);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void getAccountDetails()
      .then((details) => {
        if (active && details !== null) setDraft(draftFromDetails(details));
      })
      .catch((requestError: unknown) => {
        if (active) setError(messageFromError(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  function updateDraft(key: keyof AccountDraft, value: string) {
    setDraft((current) => ({ ...current, [key]: value }));
    setSuccessMessage(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const saved = await saveAccountDetails({
        username: draft.username.trim() || null,
        height_cm: draft.heightCm || null,
        weight_kg: draft.weightKg || null,
      });
      setDraft(draftFromDetails(saved));
      setSuccessMessage("Account details saved.");
    } catch (requestError) {
      setError(messageFromError(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-6">
      <section aria-labelledby="account-heading" className="page-hero">
        <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="page-eyebrow">Account settings</p>
            <h1
              id="account-heading"
              className="mt-3 text-3xl font-black tracking-tight sm:text-4xl"
            >
              Your account, your way.
            </h1>
            <p className="mt-3 text-sm text-slate-600">Signed in as {email}</p>
          </div>
          <button
            type="button"
            className="button-secondary w-fit"
            onClick={() => void logout().catch(() => undefined)}
          >
            Log out
          </button>
        </div>
      </section>

      <section aria-labelledby="personal-details-heading">
        <div className="max-w-2xl">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">
            Personal details
          </p>
          <h2 id="personal-details-heading" className="mt-2">
            The basics
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Keep your core account information accurate. Height and weight are stored privately with
            your account.
          </p>
        </div>

        {loading ? (
          <p className="mt-5 text-sm text-slate-600" role="status">
            Loading account details…
          </p>
        ) : (
          <form
            className="mt-7 grid gap-4 sm:grid-cols-3"
            onSubmit={(event) => void handleSubmit(event)}
          >
            <p className="mb-0 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="nickname"
                maxLength={100}
                value={draft.username}
                onChange={(event) => updateDraft("username", event.target.value)}
              />
            </p>
            <p className="mb-0 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
              <label htmlFor="height-cm">Height (cm)</label>
              <input
                id="height-cm"
                name="height-cm"
                type="number"
                min={50}
                max={260}
                step="0.1"
                value={draft.heightCm}
                onChange={(event) => updateDraft("heightCm", event.target.value)}
              />
            </p>
            <p className="mb-0 rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200/70">
              <label htmlFor="weight-kg">Weight (kg)</label>
              <input
                id="weight-kg"
                name="weight-kg"
                type="number"
                min={20}
                max={400}
                step="0.1"
                value={draft.weightKg}
                onChange={(event) => updateDraft("weightKg", event.target.value)}
              />
            </p>
            {error === null && authenticationError === null ? null : (
              <p
                className="rounded-lg bg-red-50 p-3 text-sm text-red-700 sm:col-span-3"
                role="alert"
              >
                {error ?? authenticationError}
              </p>
            )}
            {successMessage === null ? null : (
              <p
                className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700 sm:col-span-3"
                role="status"
              >
                {successMessage}
              </p>
            )}
            <button
              className="mt-2 w-full py-3 sm:col-span-3 sm:w-fit"
              type="submit"
              disabled={submitting}
            >
              {submitting ? "Saving…" : "Save details"}
            </button>
          </form>
        )}
      </section>
      <AccountLinking />
    </div>
  );
}
