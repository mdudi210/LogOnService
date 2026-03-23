import { useEffect, useState } from 'react';

interface FeatureFlags {
  enforceMfaForAdmins: boolean;
  securityAlertsEnabled: boolean;
  maintenanceMode: boolean;
}

const STORAGE_KEY = 'logonservice_admin_feature_flags_v1';

export function AdminConfigPage() {
  const [flags, setFlags] = useState<FeatureFlags>({
    enforceMfaForAdmins: true,
    securityAlertsEnabled: true,
    maintenanceMode: false
  });
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return;
    }
    try {
      const parsed = JSON.parse(raw) as FeatureFlags;
      setFlags(parsed);
    } catch {
      // Ignore malformed local data.
    }
  }, []);

  const persist = (next: FeatureFlags) => {
    setFlags(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setSavedAt(new Date().toLocaleString());
  };

  const toggle = (key: keyof FeatureFlags) => {
    const next = { ...flags, [key]: !flags[key] };
    persist(next);
  };

  return (
    <div className="panel">
      <h2>Admin Feature Configuration</h2>
      <p>
        Frontend-ready control panel for feature governance. These toggles are currently local
        placeholders and can be connected to backend config APIs later.
      </p>

      <div className="feature-grid">
        <button className="flag-card" onClick={() => toggle('enforceMfaForAdmins')}>
          <h3>Enforce MFA for Admin</h3>
          <p>{flags.enforceMfaForAdmins ? 'Enabled' : 'Disabled'}</p>
        </button>

        <button className="flag-card" onClick={() => toggle('securityAlertsEnabled')}>
          <h3>Security Alerts</h3>
          <p>{flags.securityAlertsEnabled ? 'Enabled' : 'Disabled'}</p>
        </button>

        <button className="flag-card" onClick={() => toggle('maintenanceMode')}>
          <h3>Maintenance Mode</h3>
          <p>{flags.maintenanceMode ? 'Enabled' : 'Disabled'}</p>
        </button>
      </div>

      {savedAt ? <p className="muted">Last saved at: {savedAt}</p> : null}
    </div>
  );
}

