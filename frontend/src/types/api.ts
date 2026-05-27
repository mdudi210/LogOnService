export type Role = "admin" | "user" | string;

export interface LoginUser {
  id: string;
  email: string;
  username: string;
  role: Role;
  is_verified: boolean;
}

export interface LoginResponse {
  message: string;
  user?: LoginUser;
  mfa_required: boolean;
  mfa_token?: string;
  mfa_methods?: string[];
}

export interface UserSummary {
  id: string;
  email: string;
  username: string;
  role: Role;
  is_active: boolean;
}

export interface MFAOptionsResponse {
  available_methods: string[];
  enabled_methods: string[];
}

export interface MFASetupResponse {
  secret: string;
  provisioning_uri: string;
}

export interface SessionSummary {
  jti: string;
  session_started_at: string;
  session_expires_at: string;
  is_revoked: boolean;
  is_current: boolean;
}

export interface SessionListResponse {
  count: number;
  sessions: SessionSummary[];
}

export interface AdminUserAuthSummary {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  mfa_enabled: boolean;
  enabled_mfa_methods: string[];
  oauth_providers: string[];
  created_at: string;
  updated_at: string;
}

export interface AdminUserAuthListResponse {
  count: number;
  users: AdminUserAuthSummary[];
}

export interface SecurityEventSummary {
  id: string;
  created_at: string;
  event_type: string;
  user_id?: string | null;
  alert_type: string;
  severity: string;
  ip_address?: string | null;
  user_agent?: string | null;
  metadata: Record<string, unknown>;
}

export interface SecurityEventListResponse {
  count: number;
  events: SecurityEventSummary[];
}

export interface ActivityEventSummary {
  id: string;
  created_at: string;
  event_type: string;
  user_id?: string | null;
  ip_address?: string | null;
  user_agent?: string | null;
  metadata: Record<string, unknown>;
}

export interface ActivityEventListResponse {
  count: number;
  events: ActivityEventSummary[];
}

export interface OAuthAuthorizeResponse {
  authorization_url: string;
  state: string;
}
