import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '@/app/AuthContext';

const navClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'nav-link active' : 'nav-link';

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const onLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="shell-root">
      <aside className="sidebar">
        <Link to="/" className="brand">
          <span className="brand-dot" />
          LogOnService
        </Link>

        <nav className="nav-list">
          <NavLink to="/" end className={navClass}>
            Overview
          </NavLink>
          <NavLink to="/sessions" className={navClass}>
            Sessions
          </NavLink>
          <NavLink to="/security" className={navClass}>
            Security
          </NavLink>
          {user?.role === 'admin' ? (
            <>
              <NavLink to="/admin/events" className={navClass}>
                Admin Events
              </NavLink>
              <NavLink to="/admin/config" className={navClass}>
                Admin Config
              </NavLink>
            </>
          ) : null}
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <h1 className="topbar-title">Identity Console</h1>
            <p className="topbar-subtitle">Role: {user?.role ?? 'guest'}</p>
          </div>
          <button className="btn btn-outline" onClick={onLogout}>
            Logout
          </button>
        </header>

        <section className="content-area">
          <Outlet />
        </section>
      </main>
    </div>
  );
}
