export interface AuthenticatedUser {
  id: string;
  email: string;
}

interface ErrorResponse {
  detail?: unknown;
}

interface StructuredErrorDetail {
  code?: unknown;
  message?: unknown;
  issues?: unknown;
}

const API_BASE_URL = `http://${window.location.hostname}:8000`;
const CSRF_COOKIE_NAME = "mfp_csrf";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code: string | null = null,
    readonly issues: string[] = [],
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function readCookie(name: string): string | null {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie.split("; ").find((candidate) => candidate.startsWith(prefix));

  return cookie === undefined ? null : decodeURIComponent(cookie.slice(prefix.length));
}

async function errorFromResponse(response: Response): Promise<ApiError> {
  let message = "The request could not be completed.";
  let code: string | null = null;
  let issues: string[] = [];

  try {
    const body = (await response.json()) as ErrorResponse;
    if (typeof body.detail === "string") {
      message = body.detail;
    } else if (isStructuredErrorDetail(body.detail)) {
      if (typeof body.detail.message === "string") {
        message = body.detail.message;
      }
      if (typeof body.detail.code === "string") {
        code = body.detail.code;
      }
      if (
        Array.isArray(body.detail.issues) &&
        body.detail.issues.every((issue) => typeof issue === "string")
      ) {
        issues = body.detail.issues;
      }
    }
  } catch {
    // Keep the generic message when the server does not return JSON.
  }

  return new ApiError(message, response.status, code, issues);
}

function isStructuredErrorDetail(value: unknown): value is StructuredErrorDetail {
  return typeof value === "object" && value !== null;
}

export async function apiRequest(path: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: "include",
  });

  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  return response;
}

async function csrfToken(): Promise<string> {
  let token = readCookie(CSRF_COOKIE_NAME);
  if (token === null) {
    await apiRequest("/auth/csrf");
    token = readCookie(CSRF_COOKIE_NAME);
  }

  if (token === null) {
    throw new Error("The browser did not accept the CSRF cookie.");
  }
  return token;
}

export async function csrfProtectedMutation(
  path: string,
  method: "POST" | "PUT",
  body?: unknown,
): Promise<Response> {
  const token = await csrfToken();
  return apiRequest(path, {
    method,
    headers: {
      "X-CSRF-Token": token,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export async function getCurrentUser(): Promise<AuthenticatedUser | null> {
  try {
    const response = await apiRequest("/auth/me");
    return (await response.json()) as AuthenticatedUser;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export async function register(email: string, password: string): Promise<AuthenticatedUser> {
  const response = await csrfProtectedMutation("/auth/register", "POST", { email, password });
  return (await response.json()) as AuthenticatedUser;
}

export async function login(email: string, password: string): Promise<AuthenticatedUser> {
  const response = await csrfProtectedMutation("/auth/login", "POST", { email, password });
  return (await response.json()) as AuthenticatedUser;
}

export async function loginWithGoogle(idToken: string): Promise<AuthenticatedUser> {
  const response = await csrfProtectedMutation("/auth/google", "POST", {
    id_token: idToken,
  });
  return (await response.json()) as AuthenticatedUser;
}

export async function logout(): Promise<void> {
  await csrfProtectedMutation("/auth/logout", "POST");
}
