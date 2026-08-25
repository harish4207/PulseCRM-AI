import React from "react";
import { useSelector, useDispatch } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
  Person as UserIcon,
  Security as SecurityIcon,
  Notifications as NotificationIcon,
  Logout as LogoutIcon,
  CheckCircle as CheckIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import { logout } from "../../store/slices/authSlice";

export function Settings() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector((state) => state.auth ?? {});

  const handleLogout = () => {
    dispatch(logout());
    navigate("/login", { replace: true });
  };

  return (
    <AppShell title="Settings">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", maxWidth: "900px" }}>
        <PageHeader
          tag="Preferences"
          title="Account & Territory Settings"
          description="Manage your representative profile, notifications, and clinical territory configuration."
        />

        {/* Profile Card */}
        <div className="pulse-card" style={{ padding: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.25rem" }}>
            <UserIcon style={{ color: "#0284c7" }} />
            <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a" }}>
              Representative Profile
            </h3>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1.25rem" }}>
            <div>
              <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
                Full Name
              </div>
              <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "#0f172a", marginTop: "0.25rem" }}>
                {user?.full_name || "Clinical Representative"}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
                Work Email
              </div>
              <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "#0f172a", marginTop: "0.25rem" }}>
                {user?.email || "rep@pulsecrm.ai"}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
                Representative ID
              </div>
              <div style={{ fontSize: "0.95rem", fontWeight: 600, color: "#0f172a", marginTop: "0.25rem" }}>
                REP-00{user?.id || 1}
              </div>
            </div>

            <div>
              <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>
                Status
              </div>
              <div style={{ marginTop: "0.25rem" }}>
                <StatusBadge variant="success" size="sm">
                  Active in Field
                </StatusBadge>
              </div>
            </div>
          </div>
        </div>

        {/* Security & System Info */}
        <div className="pulse-card" style={{ padding: "1.5rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.25rem" }}>
            <SecurityIcon style={{ color: "#0d9488" }} />
            <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a" }}>
              Security & Environment
            </h3>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "0.75rem", borderBottom: "1px solid #f1f5f9" }}>
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#334155" }}>
                  Authentication Protocol
                </div>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                  JSON Web Tokens (JWT) with HTTP Bearer Authorization
                </div>
              </div>
              <StatusBadge variant="teal" size="sm">
                HS256 Secure
              </StatusBadge>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: "0.75rem", borderBottom: "1px solid #f1f5f9" }}>
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#334155" }}>
                  AI Extraction Engine
                </div>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                  LangGraph Agentic Workflow with entity extraction
                </div>
              </div>
              <StatusBadge variant="product" size="sm">
                LangGraph v0.2
              </StatusBadge>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#334155" }}>
                  PulseCRM Platform Version
                </div>
                <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                  PulseCRM AI Enterprise Edition
                </div>
              </div>
              <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "#64748b" }}>
                v1.0.0
              </span>
            </div>
          </div>
        </div>

        {/* Sign Out Card */}
        <div
          className="pulse-card"
          style={{
            padding: "1.5rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "1rem",
          }}
        >
          <div>
            <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a" }}>
              Sign Out
            </div>
            <div style={{ fontSize: "0.8125rem", color: "#64748b" }}>
              End your active session on this device.
            </div>
          </div>

          <button
            type="button"
            onClick={handleLogout}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              padding: "0.6rem 1.2rem",
              borderRadius: "8px",
              border: "1px solid #fecaca",
              backgroundColor: "#fef2f2",
              color: "#dc2626",
              fontSize: "0.8125rem",
              fontWeight: 600,
            }}
          >
            <LogoutIcon style={{ fontSize: "1rem" }} />
            <span>Sign out</span>
          </button>
        </div>
      </div>
    </AppShell>
  );
}

export default Settings;
