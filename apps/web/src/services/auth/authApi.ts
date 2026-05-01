import { fetchJson } from "@/services/http/fetchJson";

export type AuthSessionUser = {
  email: string;
  display_name: string;
  group_name: string;
};

export type AuthSessionResponse = {
  enabled: boolean;
  authenticated: boolean;
  user: AuthSessionUser | null;
};

export type AuthLoginResponse = {
  authenticated: boolean;
  user: AuthSessionUser;
};

export async function getAuthSession(
  signal?: AbortSignal,
): Promise<AuthSessionResponse> {
  return fetchJson<AuthSessionResponse>("/api/auth/session", { signal });
}

export async function login(
  email: string,
  password: string,
): Promise<AuthLoginResponse> {
  return fetchJson<AuthLoginResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
    suppressUnauthorizedHandler: true,
  });
}

export async function logout(): Promise<void> {
  await fetchJson("/api/auth/logout", {
    method: "POST",
  });
}
