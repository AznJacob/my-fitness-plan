import { ApiError, apiRequest, csrfProtectedMutation } from "../auth/api";

export interface AccountDetails {
  username: string | null;
  height_cm: string | null;
  weight_kg: string | null;
}

export async function getAccountDetails(): Promise<AccountDetails | null> {
  try {
    const response = await apiRequest("/account/details");
    return (await response.json()) as AccountDetails;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export async function saveAccountDetails(details: AccountDetails): Promise<AccountDetails> {
  const response = await csrfProtectedMutation("/account/details", "PUT", details);
  return (await response.json()) as AccountDetails;
}
