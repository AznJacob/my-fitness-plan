import { useEffect, useMemo, useState, type ReactNode } from "react";

import { AuthContext, type AuthenticationStatus, type AuthContextValue } from "./auth-context";
import {
  getCurrentUser,
  login as loginRequest,
  loginWithGoogle as googleLoginRequest,
  logout as logoutRequest,
  register as registerRequest,
  type AuthenticatedUser,
} from "./api";

function messageFromError(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [status, setStatus] = useState<AuthenticationStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    void getCurrentUser()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
          setStatus(currentUser === null ? "unauthenticated" : "authenticated");
        }
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(messageFromError(requestError));
          setStatus("unauthenticated");
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      error,
      login: async (email, password) => {
        setError(null);
        try {
          const authenticatedUser = await loginRequest(email, password);
          setUser(authenticatedUser);
          setStatus("authenticated");
        } catch (requestError) {
          setError(messageFromError(requestError));
          throw requestError;
        }
      },
      loginWithGoogle: async (idToken) => {
        setError(null);
        try {
          const authenticatedUser = await googleLoginRequest(idToken);
          setUser(authenticatedUser);
          setStatus("authenticated");
        } catch (requestError) {
          setError(messageFromError(requestError));
          throw requestError;
        }
      },
      register: async (email, password) => {
        setError(null);
        try {
          const authenticatedUser = await registerRequest(email, password);
          setUser(authenticatedUser);
          setStatus("authenticated");
        } catch (requestError) {
          setError(messageFromError(requestError));
          throw requestError;
        }
      },
      logout: async () => {
        setError(null);
        try {
          await logoutRequest();
          setUser(null);
          setStatus("unauthenticated");
        } catch (requestError) {
          setError(messageFromError(requestError));
          throw requestError;
        }
      },
    }),
    [error, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
