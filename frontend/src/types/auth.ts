export type UserRole = 'user' | 'admin' | string;

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  role: UserRole;
  is_active: boolean;
}

export interface LoginResponse {
  message: string;
  mfa_required: boolean;
  mfa_token?: string | null;
  user?: {
    id: string;
    email: string;
    username: string;
    role: string;
    is_verified: boolean;
  } | null;
}

export interface SessionSummary {
  jti: string;
  session_started_at: string;
  session_expires_at: string;
  is_revoked: boolean;
  is_current: boolean;
}

export interface AuditEventSummary {
  id: string;
  user_id: string | null;
  event_type: string;
  ip_address: string | null;
  user_agent: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}
