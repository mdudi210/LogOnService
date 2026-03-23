import { useAuth } from '@/app/AuthContext';

export function OverviewPage() {
  const { user } = useAuth();

  return (
    <div className="grid-two">
      <article className="panel">
        <h2>Welcome</h2>
        <p>Identity and session controls for secure operations.</p>
        <ul className="meta-list">
          <li>
            <strong>User:</strong> {user?.username}
          </li>
          <li>
            <strong>Email:</strong> {user?.email}
          </li>
          <li>
            <strong>Role:</strong> {user?.role}
          </li>
          <li>
            <strong>Status:</strong> {user?.is_active ? 'Active' : 'Inactive'}
          </li>
        </ul>
      </article>

      <article className="panel highlight">
        <h2>Operational Guidance</h2>
        <p>Use this console to review sessions, rotate credentials, and monitor security events.</p>
        <div className="chip-row">
          <span className="chip">Cookie auth</span>
          <span className="chip">CSRF protected</span>
          <span className="chip">RBAC enforced</span>
        </div>
      </article>
    </div>
  );
}

