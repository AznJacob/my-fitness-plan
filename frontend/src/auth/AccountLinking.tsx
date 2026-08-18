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

export function AccountLinking() {
  const [methods, setMethods] = useState<ConnectedMethods | null>(null);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

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
      if (currentPassword.length === 0) {
        setError("Enter your current MyFitnessPlan password before continuing with Google.");
        throw new Error("Current password required.");
      }

      try {
        const connectedMethods = await linkGoogle(currentPassword, idToken);
        setMethods(connectedMethods);
        setCurrentPassword("");
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
      {methods === null ? (
        error === null ? (
          <p>Loading connected methods…</p>
        ) : null
      ) : (
        <>
          <ul>
            <li>Password: {methods.password ? "Connected" : "Not connected"}</li>
            <li>Google: {methods.google ? "Connected" : "Not connected"}</li>
          </ul>

          {!methods.google && methods.password ? (
            <div>
              <h3>Connect Google</h3>
              <p>Re-enter your current password, then verify the Google account you want to add.</p>
              <label htmlFor="link-current-password">Current MyFitnessPlan password</label>
              <br />
              <input
                id="link-current-password"
                name="link-current-password"
                type="password"
                autoComplete="current-password"
                maxLength={128}
                value={currentPassword}
                onChange={(event) => setCurrentPassword(event.target.value)}
              />
              <GoogleIdentityButton
                ariaLabel="Verify Google to connect it"
                pendingMessage="Connecting Google…"
                onCredential={handleGoogleLink}
              />
            </div>
          ) : null}

          {!methods.password && methods.google ? (
            <div>
              <h3>Add a password</h3>
              <p>Create a MyFitnessPlan password, then verify your connected Google account.</p>
              <p>
                <label htmlFor="link-new-password">New password</label>
                <br />
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
              </p>
              <p>
                <label htmlFor="link-confirm-password">Confirm new password</label>
                <br />
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
              </p>
              <GoogleIdentityButton
                ariaLabel="Verify Google to add a password"
                pendingMessage="Adding password…"
                onCredential={handlePasswordLink}
              />
            </div>
          ) : null}
        </>
      )}
      {error === null ? null : <p role="alert">{error}</p>}
    </section>
  );
}
