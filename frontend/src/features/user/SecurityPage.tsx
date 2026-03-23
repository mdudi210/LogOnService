import { FormEvent, useState } from 'react';
import { MessageBanner } from '@/components/MessageBanner';
import { ApiError, api } from '@/lib/api';

export function SecurityPage() {
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [mfaUri, setMfaUri] = useState<string | null>(null);
  const [mfaSecret, setMfaSecret] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const changePassword = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      await api.changePassword({ old_password: oldPassword, new_password: newPassword });
      setSuccess('Password changed and session rotated.');
      setOldPassword('');
      setNewPassword('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to change password');
    }
  };

  const setupMfa = async () => {
    setError(null);
    setSuccess(null);
    try {
      const data = await api.mfaSetup();
      setMfaUri(data.provisioning_uri);
      setMfaSecret(data.secret);
      setSuccess('MFA secret generated. Add it in authenticator and verify code.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to setup MFA');
    }
  };

  const verifyMfa = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    try {
      await api.mfaVerify(mfaCode);
      setSuccess('MFA enabled successfully.');
      setMfaCode('');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to verify MFA');
    }
  };

  return (
    <div className="grid-two">
      <article className="panel">
        <h2>Change Password</h2>
        <MessageBanner type="error" message={error} />
        <MessageBanner type="success" message={success} />
        <form className="form-grid" onSubmit={changePassword}>
          <label>
            Old Password
            <input
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
            />
          </label>
          <label>
            New Password
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </label>
          <button className="btn" type="submit">
            Update Password
          </button>
        </form>
      </article>

      <article className="panel">
        <h2>MFA Setup</h2>
        <p>Generate TOTP secret and verify once to enforce MFA login.</p>
        <div className="inline-actions">
          <button className="btn btn-outline" onClick={() => void setupMfa()}>
            Generate Secret
          </button>
        </div>

        {mfaSecret ? (
          <div className="note-box">
            <p className="mono">Secret: {mfaSecret}</p>
            <p className="mono">URI: {mfaUri}</p>
          </div>
        ) : null}

        <form className="form-grid" onSubmit={verifyMfa}>
          <label>
            MFA Code
            <input value={mfaCode} onChange={(e) => setMfaCode(e.target.value)} placeholder="123456" />
          </label>
          <button className="btn" type="submit">
            Verify MFA
          </button>
        </form>
      </article>
    </div>
  );
}

