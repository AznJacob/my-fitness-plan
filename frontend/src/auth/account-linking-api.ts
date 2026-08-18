import { apiRequest, csrfProtectedMutation } from "./api";

export interface ConnectedMethods {
  password: boolean;
  google: boolean;
}

export async function getConnectedMethods(): Promise<ConnectedMethods> {
  const response = await apiRequest("/auth/methods");
  return (await response.json()) as ConnectedMethods;
}

export async function linkGoogle(password: string, idToken: string): Promise<ConnectedMethods> {
  const response = await csrfProtectedMutation("/auth/link/google", "POST", {
    password,
    id_token: idToken,
  });
  return (await response.json()) as ConnectedMethods;
}

export async function linkPassword(
  newPassword: string,
  googleIdToken: string,
): Promise<ConnectedMethods> {
  const response = await csrfProtectedMutation("/auth/link/password", "POST", {
    new_password: newPassword,
    google_id_token: googleIdToken,
  });
  return (await response.json()) as ConnectedMethods;
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await csrfProtectedMutation("/auth/password", "POST", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}
