import type { LoginResponse, OAuthAuthorizeResponse, UserSummary } from "../types/api";
import { apiRequest } from "./client";

export function login(payload: { email_or_username: string; password: string }) {
  return apiRequest<LoginResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function register(payload: { email: string; username: string; password: string }) {
  return apiRequest<{ message: string }>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function loginMfa(payload: { mfa_token: string; method: "totp" | "email"; code: string }) {
  return apiRequest<{ message: string }>("/auth/login/mfa", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function me() {
  return apiRequest<UserSummary>("/users/me", { method: "GET" });
}

export function refresh() {
  return apiRequest<{ message: string }>("/auth/refresh", { method: "POST" }, true);
}

export function logout() {
  return apiRequest<{ message: string }>("/auth/logout", { method: "POST" }, true);
}

export function logoutAll() {
  return apiRequest<{ message: string }>("/auth/logout-all", { method: "POST" }, true);
}

export function oauthAuthorize(provider: "google" | "github") {
  return apiRequest<OAuthAuthorizeResponse>(`/auth/oauth/${provider}/authorize`, { method: "GET" });
}

export function oauthCallback(provider: "google" | "github", code: string, state: string) {
  return apiRequest<LoginResponse>(
    `/auth/oauth/${provider}/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`,
    {
      method: "GET",
    }
  );
}
