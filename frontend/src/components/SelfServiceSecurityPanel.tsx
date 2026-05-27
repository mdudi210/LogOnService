import { useEffect, useMemo, useState } from "react";
import {
  getMfaOptions,
  setupEmailMfa,
  setupTotpMfa,
  verifyEmailMfa,
  verifyTotpMfa,
} from "../api/mfaApi";
import { ApiError } from "../api/client";
import { listMySessions, revokeOtherSessions, revokeSession } from "../api/usersApi";
import type { MFAOptionsResponse, MFASetupResponse, SessionSummary } from "../types/api";

type Props = {
  title?: string;
};

export default function SelfServiceSecurityPanel({ title = "My Security Controls" }: Props) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [mfaOptions, setMfaOptions] = useState<MFAOptionsResponse | null>(null);
  const [totpSetup, setTotpSetup] = useState<MFASetupResponse | null>(null);

  const [totpCode, setTotpCode] = useState("");
  const [emailCode, setEmailCode] = useState("");

  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const enabledMfa = useMemo(() => new Set(mfaOptions?.enabled_methods || []), [mfaOptions]);

  const loadAll = async () => {
    const [sessionRes, mfaRes] = await Promise.all([listMySessions(), getMfaOptions()]);
    setSessions(sessionRes.sessions);
    setMfaOptions(mfaRes);
  };

  useEffect(() => {
    loadAll().catch((err) => {
      setError(err instanceof ApiError ? err.message : "Failed to load self-service security controls");
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

  return (
    <article className="card">
      <h3>{title}</h3>
      <div className="grid two">
        <section>
          <h4>MFA Settings</h4>
          <p>Enabled methods: {[...enabledMfa].join(", ") || "none"}</p>

          <div className="stack">
            <button
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  const setup = await setupTotpMfa();
                  setTotpSetup(setup);
                  setMessage("TOTP secret generated. Add to your authenticator, then verify code.");
                  await loadAll();
                })
              }
            >
              Setup TOTP MFA
            </button>

            {totpSetup ? (
              <div className="subcard">
                <p>
                  <strong>Secret:</strong> {totpSetup.secret}
                </p>
                <p className="tiny">
                  <strong>Provisioning URI:</strong> {totpSetup.provisioning_uri}
                </p>
                <input
                  placeholder="Enter TOTP code"
                  value={totpCode}
                  onChange={(e) => setTotpCode(e.target.value)}
                />
                <button
                  disabled={busy || !totpCode}
                  onClick={() =>
                    void run(async () => {
                      await verifyTotpMfa(totpCode.trim());
                      setTotpCode("");
                      setTotpSetup(null);
                      setMessage("TOTP MFA enabled successfully.");
                      await loadAll();
                    })
                  }
                >
                  Verify TOTP
                </button>
              </div>
            ) : null}

            <button
              disabled={busy}
              onClick={() =>
                void run(async () => {
                  await setupEmailMfa();
                  setMessage("Email MFA code sent. Check your inbox/Mailpit.");
                  await loadAll();
                })
              }
            >
              Setup Email MFA
            </button>
            <input
              placeholder="Enter email MFA code"
              value={emailCode}
              onChange={(e) => setEmailCode(e.target.value)}
            />
            <button
              disabled={busy || !emailCode}
              onClick={() =>
                void run(async () => {
                  await verifyEmailMfa(emailCode.trim());
                  setEmailCode("");
                  setMessage("Email MFA enabled successfully.");
                  await loadAll();
                })
              }
            >
              Verify Email MFA
            </button>
          </div>
        </section>

        <section>
          <h4>Active Sessions</h4>
          <p>Revoke any old session or revoke all except current one.</p>
          <button
            disabled={busy}
            onClick={() =>
              void run(async () => {
                await revokeOtherSessions();
                setMessage("Other sessions revoked.");
                await loadAll();
              })
            }
          >
            Revoke All Other Sessions
          </button>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Current</th>
                  <th>Started</th>
                  <th>Expires</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((item) => (
                  <tr key={item.jti}>
                    <td>{item.is_current ? "Yes" : "No"}</td>
                    <td>{new Date(item.session_started_at).toLocaleString()}</td>
                    <td>{new Date(item.session_expires_at).toLocaleString()}</td>
                    <td>
                      <button
                        disabled={busy || item.is_current}
                        onClick={() =>
                          void run(async () => {
                            await revokeSession(item.jti);
                            setMessage("Session revoked.");
                            await loadAll();
                          })
                        }
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {message ? <p className="feedback ok">{message}</p> : null}
      {error ? <p className="feedback error">{error}</p> : null}
    </article>
  );
}
