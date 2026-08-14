import { useState, type FormEvent } from "react";

import { useAuth } from "./useAuth";
import { GoogleSignInButton } from "./GoogleSignInButton";

type AuthMode = "login" | "register";

export function AuthForm() {
  const { error, login, register } = useAuth();
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isRegistration = mode === "register";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);

    try {
      if (isRegistration) {
        await register(email, password);
      } else {
        await login(email, password);
      }
    } catch {
      // AuthProvider exposes the safe API error for this form to render.
    } finally {
      setPassword("");
      setSubmitting(false);
    }
  }

  function switchMode() {
    setMode(isRegistration ? "login" : "register");
    setPassword("");
  }

  return (
    <section aria-labelledby="auth-heading">
      <h2 id="auth-heading">{isRegistration ? "Create an account" : "Log in"}</h2>
      <form onSubmit={(event) => void handleSubmit(event)}>
        <p>
          <label htmlFor="email">Email</label>
          <br />
          <input
            id="email"
            name="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </p>
        <p>
          <label htmlFor="password">Password</label>
          <br />
          <input
            id="password"
            name="password"
            type="password"
            autoComplete={isRegistration ? "new-password" : "current-password"}
            minLength={isRegistration ? 8 : undefined}
            maxLength={128}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </p>
        {error === null ? null : <p role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Please wait…" : isRegistration ? "Register" : "Log in"}
        </button>
      </form>
      <p>
        {isRegistration ? "Already have an account?" : "Need an account?"}{" "}
        <button type="button" onClick={switchMode} disabled={submitting}>
          {isRegistration ? "Log in" : "Register"}
        </button>
      </p>
      <GoogleSignInButton />
    </section>
  );
}
