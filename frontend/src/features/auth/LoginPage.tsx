import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MessageBanner } from '@/components/MessageBanner';
import { useAuth } from '@/app/AuthContext';
import { ApiError, api } from '@/lib/api';

export function LoginPage() {
  const navigate = useNavigate();
  const { reload } = useAuth();

  const [identifier, setIdentifier] = useState('admin@test.local');
  const [password, setPassword] = useState('Admin@12345');
  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const onPrimaryLogin = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await api.login({ email_or_username: identifier, password });
      if (response.mfa_required && response.mfa_token) {
        setMfaToken(response.mfa_token);
        setSuccess('MFA required. Enter code to complete login.');
      } else {
        await reload();
        navigate('/');
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const onMfaLogin = async (e: FormEvent) => {
    e.preventDefault();
    if (!mfaToken) {
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      await api.loginMfa({ mfa_token: mfaToken, code: mfaCode });
      await reload();
      navigate('/');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'MFA login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-root">
      <div className="login-card">
        <h1>LogOnService Console</h1>
        <p>Secure entry for user and admin operations.</p>

        <MessageBanner type="error" message={error} />
        <MessageBanner type="success" message={success} />

        {!mfaToken ? (
          <form onSubmit={onPrimaryLogin} className="form-grid">
            <label>
              Email / Username
              <input
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="admin@test.local"
                required
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="********"
                required
              />
            </label>

            <button className="btn" disabled={loading} type="submit">
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        ) : (
          <form onSubmit={onMfaLogin} className="form-grid">
            <label>
              MFA Code
              <input
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                placeholder="123456"
                required
              />
            </label>

            <button className="btn" disabled={loading} type="submit">
              {loading ? 'Verifying...' : 'Verify MFA'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
