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
import VoiceCopilot from "../pages/copilot/VoiceCopilot";
import FollowUps from "../pages/followups/FollowUps";
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
          color: "#0369a1",
          fontSize: "0.95rem",
          fontWeight: 600,
        }}
      >
        PulseCRM: Preparing your workspace...
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
          <Route path="/voice-copilot" element={<VoiceCopilot />} />
          <Route path="/ai-meeting" element={<LogMeeting />} />
          <Route path="/hcps" element={<Doctors />} />
          <Route path="/directory" element={<Doctors />} />
          <Route path="/interactions" element={<Interactions />} />
          <Route path="/followups" element={<FollowUps />} />
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