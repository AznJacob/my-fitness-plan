import { createContext } from "react";

import type { AuthenticatedUser } from "./api";

export type AuthenticationStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  status: AuthenticationStatus;
  user: AuthenticatedUser | null;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  loginWithGoogle: (idToken: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
