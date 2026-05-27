import { useEffect, useState } from "react";
import AppShell from "../components/AppShell";
import SelfServiceSecurityPanel from "../components/SelfServiceSecurityPanel";
import { ApiError } from "../api/client";
import {
  adminActivity,
  adminSecurityEvents,
  adminUsers,
  exportSecurityEventsCsv,
  triggerTestAlert,
} from "../api/usersApi";
import type {
  ActivityEventSummary,
  AdminUserAuthSummary,
  SecurityEventSummary,
} from "../types/api";

export default function AdminDashboardPage() {
  const [users, setUsers] = useState<AdminUserAuthSummary[]>([]);
  const [securityEvents, setSecurityEvents] = useState<SecurityEventSummary[]>([]);
  const [activityEvents, setActivityEvents] = useState<ActivityEventSummary[]>([]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const loadAll = async () => {
    const [usersRes, secRes, actRes] = await Promise.all([
      adminUsers(200, 0),
      adminSecurityEvents(100),
      adminActivity(100),
    ]);
    setUsers(usersRes.users);
    setSecurityEvents(secRes.events);
    setActivityEvents(actRes.events);
  };

  useEffect(() => {
    loadAll().catch((err) => {
      setError(err instanceof ApiError ? err.message : "Failed to load admin dashboard");
    });
  }, []);

  const run = async (task: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await task();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Operation failed");
    } finally {
      setBusy(false);
    }
  };

  const downloadCsv = async () => {
    await run(async () => {
      const blob = await exportSecurityEventsCsv(500);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `security-events-${Date.now()}.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setMessage("Security events CSV exported.");
    });
  };

  return (
    <AppShell role="admin" title="Admin Security Console">
      <SelfServiceSecurityPanel title="Admin Self-Service Security (All User Features)" />

      <div className="grid two">
        <article className="card">
          <div className="card-head">
            <h3>Organization Users</h3>
            <button disabled={busy} onClick={() => void run(loadAll)}>
              Refresh
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>MFA</th>
                  <th>Methods</th>
                  <th>OAuth</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.email}</td>
                    <td>{u.role}</td>
                    <td>{u.mfa_enabled ? "Enabled" : "Disabled"}</td>
                    <td>{u.enabled_mfa_methods.join(", ") || "-"}</td>
                    <td>{u.oauth_providers.join(", ") || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="card">
          <div className="card-head">
            <h3>Security Events</h3>
            <div className="actions-inline">
              <button disabled={busy} onClick={downloadCsv}>
                Export CSV
              </button>
              <button
                disabled={busy}
                onClick={() =>
                  void run(async () => {
                    await triggerTestAlert();
                    setMessage("Test alert emitted.");
                    await loadAll();
                  })
                }
              >
                Emit Test Alert
              </button>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Type</th>
                  <th>Severity</th>
                  <th>User</th>
                </tr>
              </thead>
              <tbody>
                {securityEvents.map((event) => (
                  <tr key={event.id}>
                    <td>{new Date(event.created_at).toLocaleString()}</td>
                    <td>{event.alert_type || event.event_type}</td>
                    <td>{event.severity}</td>
                    <td>{event.user_id || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </div>

      <article className="card">
        <h3>Activity Feed</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Event</th>
                <th>User ID</th>
                <th>IP</th>
              </tr>
            </thead>
            <tbody>
              {activityEvents.map((event) => (
                <tr key={event.id}>
                  <td>{new Date(event.created_at).toLocaleString()}</td>
                  <td>{event.event_type}</td>
                  <td>{event.user_id || "-"}</td>
                  <td>{event.ip_address || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>

      {message ? <p className="feedback ok">{message}</p> : null}
      {error ? <p className="feedback error">{error}</p> : null}
    </AppShell>
  );
}
