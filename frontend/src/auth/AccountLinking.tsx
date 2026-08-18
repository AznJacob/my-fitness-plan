import { useCallback, useEffect, useState } from "react";

import {
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
    <li className="flex items-center justify-between gap-4 rounded-lg bg-slate-50 px-4 py-3">
      <span className="font-medium">{label}</span>
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

  return (
    <section aria-labelledby="sign-in-methods-heading">
      <h2 id="sign-in-methods-heading">Sign-in methods</h2>
      <p className="mt-1 text-sm text-slate-600">
        Connect both methods if you want to sign in with either Google or a MyFitnessPlan password.
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
            <div className="mt-6 border-t border-slate-200 pt-6">
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
              <div className="mt-5 rounded-lg border border-blue-200 bg-blue-50 p-4">
                <p className="text-sm font-medium text-blue-900">
                  Step 2: Click the Google button below to verify and finish connecting Google.
                </p>
                <GoogleIdentityButton
                  ariaLabel="Verify Google to connect it"
                  pendingMessage="Connecting Google…"
                  onCredential={handleGoogleLink}
                />
              </div>
            </div>
          ) : null}

          {!methods.password && methods.google ? (
            <div className="mt-6 border-t border-slate-200 pt-6">
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
              <div className="mt-5 rounded-lg border border-blue-200 bg-blue-50 p-4">
                <p className="text-sm font-medium text-blue-900">
                  Step 2: Click “Continue as…” below. That Google button verifies your account and
                  finishes linking the password.
                </p>
                <GoogleIdentityButton
                  ariaLabel="Verify Google to add a password"
                  pendingMessage="Adding password…"
                  onCredential={handlePasswordLink}
                />
              </div>
            </div>
          ) : null}
        </>
      )}
      {error === null ? null : (
        <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}
      {successMessage === null ? null : (
        <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700" role="status">
          {successMessage}
        </p>
      )}
    </section>
  );
}
