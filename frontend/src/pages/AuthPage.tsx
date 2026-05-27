import type { FormEvent } from "react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, loginMfa, oauthAuthorize, register } from "../api/authApi";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Mode = "signin" | "signup";

export default function AuthPage() {
  const navigate = useNavigate();
  const { reloadUser } = useAuth();

  const [mode, setMode] = useState<Mode>("signin");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [emailOrUsername, setEmailOrUsername] = useState("");
  const [password, setPassword] = useState("");

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");

  const [mfaToken, setMfaToken] = useState<string | null>(null);
  const [mfaMethods, setMfaMethods] = useState<string[]>([]);
  const [mfaMethod, setMfaMethod] = useState<"totp" | "email">("totp");
  const [mfaCode, setMfaCode] = useState("");

  const clearFeedback = () => {
    setError(null);
    setNotice(null);
  };

  const routeUser = async () => {
    const user = await reloadUser();
    if (!user) {
      throw new Error("Could not resolve authenticated user");
    }
    navigate(user.role === "admin" ? "/admin" : "/user", { replace: true });
  };

  const onSignIn = async (event: FormEvent) => {
    event.preventDefault();
    clearFeedback();
    setBusy(true);
    try {
      const response = await login({
        email_or_username: emailOrUsername.trim(),
        password,
      });

      if (response.mfa_required && response.mfa_token) {
        const methods = response.mfa_methods || ["totp"];
        setMfaToken(response.mfa_token);
        setMfaMethods(methods);
        setMfaMethod((methods.includes("email") ? "email" : "totp") as "totp" | "email");
        setNotice("MFA required. Complete verification to continue.");
      } else {
        await routeUser();
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  };

  const onMfa = async (event: FormEvent) => {
    event.preventDefault();
    if (!mfaToken) {
      return;
    }
    clearFeedback();
    setBusy(true);
    try {
      await loginMfa({ mfa_token: mfaToken, method: mfaMethod, code: mfaCode.trim() });
      await routeUser();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "MFA verification failed");
    } finally {
      setBusy(false);
    }
  };

  const onSignUp = async (event: FormEvent) => {
    event.preventDefault();
    clearFeedback();
    setBusy(true);
    try {
      await register({
        email: email.trim(),
        username: username.trim(),
        password: registerPassword,
      });
      setMode("signin");
      setEmailOrUsername(email.trim());
      setPassword("");
      setNotice("Account created. Sign in to continue.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign up failed");
    } finally {
      setBusy(false);
    }
  };

  const onOauth = async (provider: "google" | "github") => {
    clearFeedback();
    setBusy(true);
    try {
      const response = await oauthAuthorize(provider);
      window.location.href = response.authorization_url;
    } catch (err) {
      setBusy(false);
      setError(err instanceof ApiError ? err.message : `Unable to start ${provider} sign-in`);
    }
  };

  return (
    <div className="screen auth-layout">
      <section className="hero">
        <h1>Command Access Portal</h1>
        <p>
          One secure sign-in command for both users and admins with MFA, OAuth, and session-safe cookie auth.
        </p>
      </section>

      <section className="auth-card">
        <div className="auth-switch">
          <button className={mode === "signin" ? "active" : ""} onClick={() => setMode("signin")}>
            Sign In
          </button>
          <button className={mode === "signup" ? "active" : ""} onClick={() => setMode("signup")}>
            Sign Up
          </button>
        </div>

        {mfaToken ? (
          <form className="form" onSubmit={onMfa}>
            <label>
              MFA Method
              <select value={mfaMethod} onChange={(e) => setMfaMethod(e.target.value as "totp" | "email")}>
                {mfaMethods.map((item) => (
                  <option key={item} value={item}>
                    {item.toUpperCase()}
                  </option>
                ))}
              </select>
            </label>
            <label>
              MFA Code
              <input
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                placeholder="Enter 6-digit code"
                required
              />
            </label>
            <button type="submit" disabled={busy}>
              {busy ? "Verifying..." : "Complete Login"}
            </button>
            <button
              type="button"
              className="ghost"
              onClick={() => {
                setMfaToken(null);
                setMfaMethods([]);
                setMfaCode("");
                setNotice(null);
              }}
            >
              Back
            </button>
          </form>
        ) : mode === "signin" ? (
          <form className="form" onSubmit={onSignIn}>
            <label>
              Email or Username
              <input
                value={emailOrUsername}
                onChange={(e) => setEmailOrUsername(e.target.value)}
                placeholder="admin.qa@logonservices.local"
                required
              />
            </label>
            <label>
              Password
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </label>
            <button type="submit" disabled={busy}>
              {busy ? "Signing in..." : "Sign In"}
            </button>
          </form>
        ) : (
          <form className="form" onSubmit={onSignUp}>
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@logonservices.local"
                required
              />
            </label>
            <label>
              Username
              <input value={username} onChange={(e) => setUsername(e.target.value)} required />
            </label>
            <label>
              Password
              <input
                type="password"
                value={registerPassword}
                onChange={(e) => setRegisterPassword(e.target.value)}
                required
              />
            </label>
            <button type="submit" disabled={busy}>
              {busy ? "Creating account..." : "Create Account"}
            </button>
          </form>
        )}

        <div className="oauth-block">
          <span>or sign in with</span>
          <div>
            <button className="ghost" type="button" disabled={busy} onClick={() => void onOauth("google")}>
              Google
            </button>
            <button className="ghost" type="button" disabled={busy} onClick={() => void onOauth("github")}>
              GitHub
            </button>
          </div>
        </div>

        {error ? <p className="feedback error">{error}</p> : null}
        {notice ? <p className="feedback ok">{notice}</p> : null}
      </section>
    </div>
  );
}
