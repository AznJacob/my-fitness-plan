import { useEffect, useRef, useState } from "react";

import { renderGoogleButton } from "./google-identity";

const GOOGLE_CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID ?? "").trim();

interface GoogleIdentityButtonProps {
  ariaLabel: string;
  pendingMessage: string;
  onCredential: (credential: string) => Promise<void>;
}

export function GoogleIdentityButton({
  ariaLabel,
  pendingMessage,
  onCredential,
}: GoogleIdentityButtonProps) {
  const buttonContainer = useRef<HTMLDivElement>(null);
  const credentialHandler = useRef(onCredential);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    credentialHandler.current = onCredential;
  }, [onCredential]);

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
      void credentialHandler
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
      <div ref={buttonContainer} aria-label={ariaLabel} />
      {loading ? <p>{pendingMessage}</p> : null}
      {loadError === null ? null : <p role="alert">{loadError}</p>}
    </div>
  );
}
