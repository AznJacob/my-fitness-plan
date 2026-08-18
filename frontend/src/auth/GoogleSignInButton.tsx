import { GoogleIdentityButton } from "./GoogleIdentityButton";
import { useAuth } from "./useAuth";

export function GoogleSignInButton() {
  const { loginWithGoogle } = useAuth();

  return (
    <div>
      <p className="mt-5 text-sm text-slate-500">Or continue with Google</p>
      <GoogleIdentityButton
        ariaLabel="Google Sign-In"
        pendingMessage="Signing in with Google…"
        onCredential={loginWithGoogle}
      />
    </div>
  );
}
