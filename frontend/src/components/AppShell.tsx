import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { logout, logoutAll } from "../api/authApi";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

type Props = {
  role: "admin" | "user";
  title: string;
  children: React.ReactNode;
};

export default function AppShell({ role, title, children }: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, setUser } = useAuth();
  const [error, setError] = useState<string | null>(null);

  const onLogout = async () => {
    setError(null);
    try {
      await logout();
      setUser(null);
      navigate("/auth", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Logout failed");
    }
  };

  const onLogoutAll = async () => {
    setError(null);
    try {
      await logoutAll();
      setUser(null);
      navigate("/auth", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Logout-all failed");
    }
  };

  return (
    <div className="shell">
      <aside className="sidebar">
        <h1>LogOnService</h1>
        <p>{role === "admin" ? "Admin Console" : "User Console"}</p>
        <nav>
          <Link className={location.pathname === `/${role}` ? "active" : ""} to={`/${role}`}>
            Dashboard
          </Link>
          <button className="link-btn" onClick={onLogout}>
            Logout
          </button>
          <button className="link-btn" onClick={onLogoutAll}>
            Logout All
          </button>
        </nav>
        {error ? <p className="feedback error">{error}</p> : null}
      </aside>
      <section className="main-panel">
        <header className="panel-header">
          <h2>{title}</h2>
          <div className="identity-pill">
            <strong>{user?.username}</strong>
            <span>{user?.email}</span>
          </div>
        </header>
        {children}
      </section>
    </div>
  );
}
