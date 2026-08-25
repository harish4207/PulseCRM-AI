import { Navigate, Outlet } from "react-router-dom";
import { useSelector } from "react-redux";

function ProtectedRoute() {
  const { isAuthenticated, loading } = useSelector((state) => state.auth ?? {});

  if (loading) {
    return <div style={{ padding: "2rem", fontSize: "1rem" }}>Loading your session...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
