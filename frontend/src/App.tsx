import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AuthPage from "./pages/AuthPage";
import OAuthCallbackPage from "./pages/OAuthCallbackPage";
import UserDashboardPage from "./pages/UserDashboardPage";

function RootPage() {
  const { user, ready } = useAuth();
  if (!ready) {
    return <div className="screen center">Preparing console...</div>;
  }
  if (!user) {
    return <Navigate to="/auth" replace />;
  }
  return <Navigate to={user.role === "admin" ? "/admin" : "/user"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootPage />} />
      <Route path="/auth" element={<AuthPage />} />
      <Route path="/oauth/callback/:provider" element={<OAuthCallbackPage />} />

      <Route element={<ProtectedRoute role="user" />}>
        <Route path="/user" element={<UserDashboardPage />} />
      </Route>

      <Route element={<ProtectedRoute role="admin" />}>
        <Route path="/admin" element={<AdminDashboardPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
