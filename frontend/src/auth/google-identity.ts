export interface GoogleCredentialResponse {
  credential: string;
  select_by: string;
}

interface GoogleAccountsId {
  initialize: (configuration: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
  }) => void;
  renderButton: (
    parent: HTMLElement,
    options: { theme: "outline"; size: "large"; text: "continue_with" },
  ) => void;
}

interface GoogleIdentityServices {
  accounts: { id: GoogleAccountsId };
}

declare global {
  interface Window {
    google?: GoogleIdentityServices;
  }
}

const SCRIPT_ID = "google-identity-services";
let scriptPromise: Promise<GoogleIdentityServices> | null = null;
let initializedClientId: string | null = null;
let credentialHandler: ((credential: string) => void) | null = null;

function loadGoogleIdentityServices(): Promise<GoogleIdentityServices> {
  if (window.google !== undefined) {
    return Promise.resolve(window.google);
  }
  if (scriptPromise !== null) {
    return scriptPromise;
  }

  scriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = SCRIPT_ID;
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => {
      if (window.google === undefined) {
        reject(new Error("Google Identity Services did not initialize."));
        return;
      }
      resolve(window.google);
    };
    script.onerror = () => reject(new Error("Google Sign-In could not be loaded."));
    document.head.append(script);
  });
  return scriptPromise;
}

export async function renderGoogleButton(
  parent: HTMLElement,
  clientId: string,
  onCredential: (credential: string) => void,
): Promise<void> {
  credentialHandler = onCredential;
  const google = await loadGoogleIdentityServices();

  if (initializedClientId === null) {
    google.accounts.id.initialize({
      client_id: clientId,
      callback: (response) => credentialHandler?.(response.credential),
    });
    initializedClientId = clientId;
  } else if (initializedClientId !== clientId) {
    throw new Error("Google Sign-In was initialized with a different client ID.");
  }

  parent.replaceChildren();
  google.accounts.id.renderButton(parent, {
    theme: "outline",
    size: "large",
    text: "continue_with",
  });
}
