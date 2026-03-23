import type { AuditEventSummary, LoginResponse, SessionSummary, UserProfile } from '@/types/auth';
import { getCookie } from '@/lib/cookies';

const runtimeDefaultBaseUrl =
  typeof window !== 'undefined'
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : 'http://127.0.0.1:8000';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || runtimeDefaultBaseUrl;
const CSRF_COOKIE = 'csrf_token';
const CSRF_HEADER = 'X-CSRF-Token';

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown = null) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase();
  const headers = new Headers(init.headers ?? {});

  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json');
  }

  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrf = getCookie(CSRF_COOKIE);
    if (csrf) {
      headers.set(CSRF_HEADER, csrf);
    }
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    method,
    headers,
    credentials: 'include'
  });

  const isJson = (res.headers.get('content-type') ?? '').includes('application/json');
  const payload = isJson ? await res.json() : await res.text();

  if (!res.ok) {
    const detail = typeof payload === 'object' && payload && 'detail' in payload
      ? String((payload as { detail: unknown }).detail)
      : `Request failed with status ${res.status}`;
    throw new ApiError(detail, res.status, payload);
  }

  return payload as T;
}

export const api = {
  health: () => request<{ status: string; service?: string; module?: string }>('/health'),

  login: (input: { email_or_username: string; password: string }) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(input)
    }),

  loginMfa: (input: { mfa_token: string; code: string }) =>
    request<{ message: string }>('/auth/login/mfa', {
      method: 'POST',
      body: JSON.stringify(input)
    }),

  logout: () => request<{ message: string }>('/auth/logout', { method: 'POST' }),

  logoutAll: () => request<{ message: string }>('/auth/logout-all', { method: 'POST' }),

  refresh: () => request<{ message: string }>('/auth/refresh', { method: 'POST' }),

  me: () => request<UserProfile>('/users/me'),

  changePassword: (input: { old_password: string; new_password: string }) =>
    request<{ message: string }>('/users/me/change-password', {
      method: 'POST',
      body: JSON.stringify(input)
    }),

  listSessions: () => request<{ sessions: SessionSummary[] }>('/users/me/sessions'),

  revokeSession: (jti: string) =>
    request<{ message: string }>(`/users/me/sessions/${encodeURIComponent(jti)}`, {
      method: 'DELETE'
    }),

  revokeOtherSessions: () =>
    request<{ message: string }>('/users/me/sessions', {
      method: 'DELETE'
    }),

  mfaSetup: () => request<{ secret: string; provisioning_uri: string }>('/mfa/setup', { method: 'POST' }),

  mfaVerify: (code: string) =>
    request<{ message: string }>('/mfa/verify', {
      method: 'POST',
      body: JSON.stringify({ code })
    }),

  adminHealth: () => request<{ status: string; scope: string }>('/users/admin/health'),

  adminSecurityEvents: (limit = 50, eventType = '') => {
    const q = new URLSearchParams({ limit: String(limit) });
    if (eventType.trim()) {
      q.set('event_type', eventType.trim());
    }
    return request<{ events: AuditEventSummary[] }>(`/users/admin/security-events?${q.toString()}`);
  }
};
