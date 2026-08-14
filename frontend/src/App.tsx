import { AuthForm } from "./auth/AuthForm";
import { useAuth } from "./auth/useAuth";

export function App() {
  const { error, logout, status, user } = useAuth();

  if (status === "loading") {
    return (
      <main>
        <h1>MyFitnessPlan</h1>
        <p>Checking your session…</p>
      </main>
    );
  }

  return (
    <main>
      <h1>MyFitnessPlan</h1>
      <p>A personalized workout and nutrition planning application.</p>
      {status === "authenticated" && user !== null ? (
        <section aria-labelledby="account-heading">
          <h2 id="account-heading">Your account</h2>
          <p>Signed in as {user.email}</p>
          {error === null ? null : <p role="alert">{error}</p>}
          <button type="button" onClick={() => void logout().catch(() => undefined)}>
            Log out
          </button>
        </section>
      ) : (
        <AuthForm />
      )}
    </main>
  );
}
