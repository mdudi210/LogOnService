import { useEffect, useState } from 'react';
import { MessageBanner } from '@/components/MessageBanner';
import { ApiError, api } from '@/lib/api';
import type { SessionSummary } from '@/types/auth';

export function SessionsPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.listSessions();
      setSessions(data.sessions);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to fetch sessions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const revokeOne = async (jti: string) => {
    setError(null);
    setSuccess(null);
    try {
      await api.revokeSession(jti);
      setSuccess('Session revoked successfully.');
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to revoke session');
    }
  };

  const revokeOthers = async () => {
    setError(null);
    setSuccess(null);
    try {
      await api.revokeOtherSessions();
      setSuccess('All other sessions revoked.');
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to revoke sessions');
    }
  };

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Active Sessions</h2>
        <button className="btn btn-outline" onClick={revokeOthers}>
          Revoke Others
        </button>
      </div>

      <MessageBanner type="error" message={error} />
      <MessageBanner type="success" message={success} />

      {loading ? (
        <p>Loading sessions...</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>JTI</th>
                <th>Started</th>
                <th>Expires</th>
                <th>Current</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.jti}>
                  <td className="mono">{session.jti.slice(0, 12)}...</td>
                  <td>{new Date(session.session_started_at).toLocaleString()}</td>
                  <td>{new Date(session.session_expires_at).toLocaleString()}</td>
                  <td>{session.is_current ? 'Yes' : 'No'}</td>
                  <td>
                    <button
                      className="btn btn-danger"
                      disabled={session.is_current}
                      onClick={() => void revokeOne(session.jti)}
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

