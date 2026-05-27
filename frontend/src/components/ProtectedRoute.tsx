import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

type Props = {
  role?: "admin" | "user";
};

export default function ProtectedRoute({ role }: Props) {
  const { user, ready } = useAuth();

  if (!ready) {
    return <div className="screen center">Loading secure session...</div>;
  }

  if (!user) {
    return <Navigate to="/auth" replace />;
  }

  if (role && user.role !== role) {
    return <Navigate to={user.role === "admin" ? "/admin" : "/user"} replace />;
  }

  return <Outlet />;
}
