import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  changePassword,
  getConnectedMethods,
  linkGoogle,
  linkPassword,
  type ConnectedMethods,
} from "./account-linking-api";
import { GoogleIdentityButton } from "./GoogleIdentityButton";

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "The sign-in method could not be connected.";
}

function MethodStatus({ connected, label }: { connected: boolean; label: string }) {
  return (
    <li className="flex items-center justify-between gap-4 rounded-xl border border-slate-200 bg-slate-50/70 p-4">
      <span className="font-semibold text-slate-800">{label}</span>
      <span
        className={`rounded-full px-3 py-1 text-xs font-semibold ${
          connected ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
        }`}
      >
        {connected ? "Connected" : "Not connected"}
      </span>
    </li>
  );
}

export function AccountLinking() {
  const [methods, setMethods] = useState<ConnectedMethods | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changeCurrentPassword, setChangeCurrentPassword] = useState("");
  const [changedPassword, setChangedPassword] = useState("");
  const [changedPasswordConfirmation, setChangedPasswordConfirmation] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void getConnectedMethods()
      .then((connectedMethods) => {
        if (active) {
          setMethods(connectedMethods);
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(messageFromError(requestError));
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const handleGoogleLink = useCallback(
    async (idToken: string) => {
      setError(null);
      setSuccessMessage(null);
      if (currentPassword.length === 0) {
        setError("Enter your current MyFitnessPlan password before continuing with Google.");
        throw new Error("Current password required.");
      }

      try {
        const connectedMethods = await linkGoogle(currentPassword, idToken);
        setMethods(connectedMethods);
        setCurrentPassword("");
        setSuccessMessage("Google is now connected. You can use either method to sign in.");
      } catch (requestError) {
        setError(messageFromError(requestError));
        throw requestError;
      }
    },
    [currentPassword],
  );

  const handlePasswordLink = useCallback(
    async (googleIdToken: string) => {
      setError(null);
      setSuccessMessage(null);
      if (newPassword !== confirmPassword) {
        setError("The new passwords do not match.");
        throw new Error("Password confirmation failed.");
      }
      if (newPassword.length < 8 || newPassword.length > 128) {
        setError("Password must contain between 8 and 128 characters.");
        throw new Error("Password length is invalid.");
      }

      try {
        const connectedMethods = await linkPassword(newPassword, googleIdToken);
        setMethods(connectedMethods);
        setNewPassword("");
        setConfirmPassword("");
        setSuccessMessage("Your password is connected. You can use either method to sign in.");
      } catch (requestError) {
        setError(messageFromError(requestError));
        throw requestError;
      }
    },
    [confirmPassword, newPassword],
  );

  async function handlePasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSuccessMessage(null);
    if (changedPassword !== changedPasswordConfirmation) {
      setError("The new passwords do not match.");
      return;
    }
    setChangingPassword(true);
    try {
      await changePassword(changeCurrentPassword, changedPassword);
      setChangeCurrentPassword("");
      setChangedPassword("");
      setChangedPasswordConfirmation("");
      setSuccessMessage("Your password has been changed.");
    } catch (requestError) {
      setError(messageFromError(requestError));
    } finally {
      setChangingPassword(false);
    }
  }

  return (
    <div className="space-y-6">
      {error === null ? null : (
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}
      {successMessage === null ? null : (
        <p className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700" role="status">
          {successMessage}
        </p>
      )}

      <section aria-labelledby="password-heading">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">Security</p>
        <h2 id="password-heading" className="mt-2">
          Password
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Manage the password used to access your MyFitnessPlan account.
        </p>

        {methods === null ? (
          error === null ? (
            <p className="mt-4 text-slate-600">Loading password settings…</p>
          ) : null
        ) : methods.password ? (
          <form className="mt-6 max-w-xl" onSubmit={(event) => void handlePasswordChange(event)}>
            <h3>Change password</h3>
            <p className="mt-1 text-sm text-slate-600">
              Confirm your current password before choosing a new one.
            </p>
            <div className="mt-4 grid gap-4">
              <div>
                <label htmlFor="change-current-password">Current password</label>
                <input
                  id="change-current-password"
                  type="password"
                  autoComplete="current-password"
                  maxLength={128}
                  required
                  value={changeCurrentPassword}
                  onChange={(event) => setChangeCurrentPassword(event.target.value)}
                />
              </div>
              <div>
                <label htmlFor="changed-password">New password</label>
                <input
                  id="changed-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  required
                  value={changedPassword}
                  onChange={(event) => setChangedPassword(event.target.value)}
                />
              </div>
              <div>
                <label htmlFor="changed-password-confirmation">Confirm new password</label>
                <input
                  id="changed-password-confirmation"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  required
                  value={changedPasswordConfirmation}
                  onChange={(event) => setChangedPasswordConfirmation(event.target.value)}
                />
              </div>
            </div>
            <button className="mt-4" type="submit" disabled={changingPassword}>
              {changingPassword ? "Changing…" : "Change password"}
            </button>
          </form>
        ) : methods.google ? (
          <div className="mt-6">
            <h3>Add a password</h3>
            <p className="mt-1 text-sm text-slate-600">
              Step 1: Create the MyFitnessPlan password you want to use for future logins.
            </p>
            <div className="mt-4 grid max-w-2xl gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="link-new-password">New password</label>
                <input
                  id="link-new-password"
                  name="link-new-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                />
              </div>
              <div>
                <label htmlFor="link-confirm-password">Confirm new password</label>
                <input
                  id="link-confirm-password"
                  name="link-confirm-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  maxLength={128}
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                />
              </div>
            </div>
            <div className="mt-5 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
              <p className="text-sm font-medium text-indigo-900">
                Step 2: Use Google below to verify your account and finish adding the password.
              </p>
              <GoogleIdentityButton
                ariaLabel="Verify Google to add a password"
                pendingMessage="Adding password…"
                onCredential={handlePasswordLink}
              />
            </div>
          </div>
        ) : null}
      </section>

      <section aria-labelledby="sign-in-methods-heading">
        <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-600">Access</p>
        <h2 id="sign-in-methods-heading" className="mt-2">
          Sign-in methods
        </h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Connect both methods if you want to sign in with either Google or your password.
        </p>

        {methods === null ? (
          error === null ? (
            <p className="mt-4 text-slate-600">Loading connected methods…</p>
          ) : null
        ) : (
          <>
            <ul className="mt-4 grid gap-3 sm:grid-cols-2">
              <MethodStatus connected={methods.password} label="Password" />
              <MethodStatus connected={methods.google} label="Google" />
            </ul>

            {!methods.google && methods.password ? (
              <div className="mt-6 max-w-2xl border-t border-slate-200 pt-6">
                <h3>Connect Google</h3>
                <p className="mt-1 text-sm text-slate-600">
                  Step 1: Re-enter your current MyFitnessPlan password.
                </p>
                <div className="mt-4 max-w-md">
                  <label htmlFor="link-current-password">Current MyFitnessPlan password</label>
                  <input
                    id="link-current-password"
                    name="link-current-password"
                    type="password"
                    autoComplete="current-password"
                    maxLength={128}
                    value={currentPassword}
                    onChange={(event) => setCurrentPassword(event.target.value)}
                  />
                </div>
                <div className="mt-5 rounded-xl border border-indigo-200 bg-indigo-50 p-4">
                  <p className="text-sm font-medium text-indigo-900">
                    Step 2: Use Google below to verify and finish connecting it.
                  </p>
                  <GoogleIdentityButton
                    ariaLabel="Verify Google to connect it"
                    pendingMessage="Connecting Google…"
                    onCredential={handleGoogleLink}
                  />
                </div>
              </div>
            ) : null}
          </>
        )}
      </section>
    </div>
  );
}
