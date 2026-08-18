import { GoogleIdentityButton } from "./GoogleIdentityButton";
import { useAuth } from "./useAuth";

export function GoogleSignInButton() {
  const { loginWithGoogle } = useAuth();

  return (
    <div>
      <p>Or</p>
      <GoogleIdentityButton
        ariaLabel="Google Sign-In"
        pendingMessage="Signing in with Google…"
        onCredential={loginWithGoogle}
      />
    </div>
  );
}
