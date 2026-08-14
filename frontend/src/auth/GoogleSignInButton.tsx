import { useEffect, useRef, useState } from "react";

import { renderGoogleButton } from "./google-identity";
import { useAuth } from "./useAuth";

const GOOGLE_CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "").trim();

export function GoogleSignInButton() {
  const { loginWithGoogle } = useAuth();
  const buttonContainer = useRef<HTMLDivElement>(null);
  const loginHandler = useRef(loginWithGoogle);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    loginHandler.current = loginWithGoogle;
  }, [loginWithGoogle]);

  useEffect(() => {
    const container = buttonContainer.current;
    if (container === null || GOOGLE_CLIENT_ID === "") {
      return;
    }

    let active = true;
    void renderGoogleButton(container, GOOGLE_CLIENT_ID, (credential) => {
      if (!active) {
        return;
      }
      setLoading(true);
      void loginHandler
        .current(credential)
        .catch(() => undefined)
        .finally(() => {
          if (active) {
            setLoading(false);
          }
        });
    }).catch((error: unknown) => {
      if (active) {
        setLoadError(
          error instanceof Error ? error.message : "Google Sign-In could not be loaded.",
        );
      }
    });

    return () => {
      active = false;
      container.replaceChildren();
    };
  }, []);

  if (GOOGLE_CLIENT_ID === "") {
    return <p>Google Sign-In is not configured.</p>;
  }

  return (
    <div>
      <p>Or</p>
      <div ref={buttonContainer} aria-label="Google Sign-In" />
      {loading ? <p>Signing in with Google…</p> : null}
      {loadError === null ? null : <p role="alert">{loadError}</p>}
    </div>
  );
}
