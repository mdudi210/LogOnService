import { FormEvent, useEffect, useState } from 'react';
import { MessageBanner } from '@/components/MessageBanner';
import { ApiError, api } from '@/lib/api';
import type { AuditEventSummary } from '@/types/auth';

export function AdminEventsPage() {
  const [events, setEvents] = useState<AuditEventSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [eventType, setEventType] = useState('');
  const [limit, setLimit] = useState(50);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.adminSecurityEvents(limit, eventType);
      setEvents(data.events);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load security events');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const onFilter = async (e: FormEvent) => {
    e.preventDefault();
    await load();
  };

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Security Events</h2>
      </div>

      <form className="inline-filter" onSubmit={onFilter}>
        <label>
          Event Type
          <input value={eventType} onChange={(e) => setEventType(e.target.value)} placeholder="TOKEN_REUSE_DETECTED" />
        </label>
        <label>
          Limit
          <input
            type="number"
            min={1}
            max={200}
            value={limit}
            onChange={(e) => setLimit(Math.min(200, Math.max(1, Number(e.target.value) || 50)))}
          />
        </label>
        <button className="btn" type="submit">
          Apply
        </button>
      </form>

      <MessageBanner type="error" message={error} />

      {loading ? (
        <p>Loading events...</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Created</th>
                <th>Type</th>
                <th>User</th>
                <th>IP</th>
                <th>Metadata</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.id}>
                  <td>{new Date(event.created_at).toLocaleString()}</td>
                  <td>{event.event_type}</td>
                  <td className="mono">{event.user_id ?? '-'}</td>
                  <td>{event.ip_address ?? '-'}</td>
                  <td className="mono">{JSON.stringify(event.metadata)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

