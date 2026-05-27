import type {
  ActivityEventListResponse,
  AdminUserAuthListResponse,
  SecurityEventListResponse,
  SessionListResponse,
} from "../types/api";
import { apiRequest, downloadBlob } from "./client";

export function listMySessions() {
  return apiRequest<SessionListResponse>("/users/me/sessions", { method: "GET" });
}

export function revokeSession(jti: string) {
  return apiRequest<{ message: string }>(`/users/me/sessions/${encodeURIComponent(jti)}`, {
    method: "DELETE",
  }, true);
}

export function revokeOtherSessions() {
  return apiRequest<{ message: string }>("/users/me/sessions", { method: "DELETE" }, true);
}

export function adminUsers(limit = 200, offset = 0) {
  return apiRequest<AdminUserAuthListResponse>(`/users/admin/users?limit=${limit}&offset=${offset}`, {
    method: "GET",
  });
}

export function adminSecurityEvents(limit = 100) {
  return apiRequest<SecurityEventListResponse>(`/users/admin/security-events?limit=${limit}`, {
    method: "GET",
  });
}

export function adminActivity(limit = 100) {
  return apiRequest<ActivityEventListResponse>(`/users/admin/activity?limit=${limit}`, {
    method: "GET",
  });
}

export function triggerTestAlert() {
  return apiRequest<{ message: string }>("/users/admin/security-events/test-alert", {
    method: "POST",
  }, true);
}

export function exportSecurityEventsCsv(limit = 500) {
  return downloadBlob(`/users/admin/security-events/export?limit=${limit}`);
}
