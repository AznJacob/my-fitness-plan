export interface AuthenticatedUser {
  id: string;
  email: string;
}

interface ErrorResponse {
  detail?: unknown;
}

const API_BASE_URL = `http://${window.location.hostname}:8000`;
const CSRF_COOKIE_NAME = "mfp_csrf";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
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

  try {
    const body = (await response.json()) as ErrorResponse;
    if (typeof body.detail === "string") {
      message = body.detail;
    }
  } catch {
    // Keep the generic message when the server does not return JSON.
  }

  return new ApiError(message, response.status);
}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
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
    await request("/auth/csrf");
    token = readCookie(CSRF_COOKIE_NAME);
  }

  if (token === null) {
    throw new Error("The browser did not accept the CSRF cookie.");
  }
  return token;
}

async function authMutation(path: string, body?: unknown): Promise<Response> {
  const token = await csrfToken();
  return request(path, {
    method: "POST",
    headers: {
      "X-CSRF-Token": token,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

export async function getCurrentUser(): Promise<AuthenticatedUser | null> {
  try {
    const response = await request("/auth/me");
    return (await response.json()) as AuthenticatedUser;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      return null;
    }
    throw error;
  }
}

export async function register(email: string, password: string): Promise<AuthenticatedUser> {
  const response = await authMutation("/auth/register", { email, password });
  return (await response.json()) as AuthenticatedUser;
}

export async function login(email: string, password: string): Promise<AuthenticatedUser> {
  const response = await authMutation("/auth/login", { email, password });
  return (await response.json()) as AuthenticatedUser;
}

export async function loginWithGoogle(idToken: string): Promise<AuthenticatedUser> {
  const response = await authMutation("/auth/google", { id_token: idToken });
  return (await response.json()) as AuthenticatedUser;
}

export async function logout(): Promise<void> {
  await authMutation("/auth/logout");
}
