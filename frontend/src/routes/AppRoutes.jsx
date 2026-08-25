import React from "react";
import { BrowserRouter, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useSelector } from "react-redux";

import Login from "../pages/auth/Login";
import Register from "../pages/auth/Register";
import Dashboard from "../pages/dashboard/Dashboard";
import Doctors from "../pages/doctors/Doctors";
import Interactions from "../pages/interactions/Interactions";
import LogMeeting from "../pages/meetings/LogMeeting";
import Analytics from "../pages/analytics/Analytics";
import Settings from "../pages/settings/Settings";
import ProtectedRoute from "./ProtectedRoute";

function PublicRoute() {
  const { isAuthenticated, loading } = useSelector((state) => state.auth ?? {});

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          height: "100vh",
          alignItems: "center",
          justifyContent: "center",
          backgroundColor: "#f8fafc",
          color: "#64748b",
          fontSize: "0.95rem",
          fontWeight: 600,
        }}
      >
        Initializing PulseCRM session...
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}

export function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public unauthenticated routes */}
        <Route element={<PublicRoute />}>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
        </Route>

        {/* Authenticated CRM routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/hcps" element={<Doctors />} />
          <Route path="/interactions" element={<Interactions />} />
          <Route path="/ai-meeting" element={<LogMeeting />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/settings" element={<Settings />} />
        </Route>

        {/* Fallbacks */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default AppRoutes;