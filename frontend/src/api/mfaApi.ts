import type { MFAOptionsResponse, MFASetupResponse } from "../types/api";
import { apiRequest } from "./client";

export function getMfaOptions() {
  return apiRequest<MFAOptionsResponse>("/mfa/options", { method: "GET" });
}

export function setupTotpMfa() {
  return apiRequest<MFASetupResponse>("/mfa/setup", { method: "POST" }, true);
}

export function verifyTotpMfa(code: string) {
  return apiRequest<{ message: string }>("/mfa/verify", {
    method: "POST",
    body: JSON.stringify({ code }),
  }, true);
}

export function setupEmailMfa() {
  return apiRequest<{ message: string; expires_in_seconds: number }>("/mfa/setup/email", {
    method: "POST",
  }, true);
}

export function verifyEmailMfa(code: string) {
  return apiRequest<{ message: string }>("/mfa/verify/email", {
    method: "POST",
    body: JSON.stringify({ code }),
  }, true);
}
