import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  SpaceDashboardOutlined as DashboardIcon,
  PeopleAltOutlined as HcpIcon,
  EventNoteOutlined as InteractionIcon,
  AutoAwesomeOutlined as AiIcon,
  BarChartOutlined as AnalyticsIcon,
  SettingsOutlined as SettingsIcon,
  LogoutOutlined as LogoutIcon,
  Close as CloseIcon,
  RecordVoiceOver as CopilotIcon,
} from "@mui/icons-material";

import AppLogo from "../common/AppLogo";
import { logout } from "../../store/slices/authSlice";

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: DashboardIcon },
  { label: "HCPs", path: "/hcps", icon: HcpIcon },
  { label: "Interactions", path: "/interactions", icon: InteractionIcon },
  { label: "AI Meeting", path: "/ai-meeting", icon: AiIcon, highlight: true },
  { label: "Voice Copilot", path: "/voice-copilot", icon: CopilotIcon, badge: "NEW" },
  { label: "Analytics", path: "/analytics", icon: AnalyticsIcon },
  { label: "Settings", path: "/settings", icon: SettingsIcon },
];

export function Sidebar({ onClose = null, isMobile = false }) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { user } = useSelector((state) => state.auth ?? {});

  const handleLogout = () => {
    if (isMobile && onClose) onClose();
    dispatch(logout());
    navigate("/login", { replace: true });
  };

  const userInitial = (user?.full_name || "U").charAt(0).toUpperCase();

  return (
    <aside
      style={{
        width: isMobile ? "280px" : "240px",
        maxWidth: isMobile ? "85vw" : "240px",
        height: "100vh",
        backgroundColor: "#ffffff",
        borderRight: "1px solid #e2e8f0",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "1.25rem 0.85rem",
        position: isMobile ? "relative" : "sticky",
        top: 0,
        flexShrink: 0,
        zIndex: 40,
        overflowY: "auto",
      }}
    >
      <div>
        {/* Brand and close button for mobile */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "0.25rem 0.6rem 1.25rem",
            borderBottom: "1px solid #f1f5f9",
            marginBottom: "0.85rem",
          }}
        >
          <AppLogo size="md" />
          {isMobile && onClose && (
            <button
              type="button"
              onClick={onClose}
              style={{
                color: "#64748b",
                padding: "0.5rem",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                minWidth: "44px",
                minHeight: "44px",
              }}
              aria-label="Close menu"
            >
              <CloseIcon fontSize="small" />
            </button>
          )}
        </div>

        {/* Navigation links */}
        <nav style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={isMobile && onClose ? onClose : undefined}
                style={({ isActive }) => ({
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0.7rem 0.85rem",
                  minHeight: "44px",
                  borderRadius: "10px",
                  textDecoration: "none",
                  fontSize: "0.875rem",
                  fontWeight: isActive ? 600 : 500,
                  color: isActive ? "#0284c7" : "#475569",
                  backgroundColor: isActive ? "#f0f9ff" : "transparent",
                  transition: "all 0.15s ease",
                  border: isActive ? "1px solid #bae6fd" : "1px solid transparent",
                })}
              >
                {({ isActive }) => (
                  <>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                      <Icon
                        style={{
                          fontSize: "1.25rem",
                          color: "inherit",
                        }}
                      />
                      <span>{item.label}</span>
                    </div>

                    {item.highlight && (
                      <span
                        style={{
                          fontSize: "0.65rem",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          letterSpacing: "0.06em",
                          backgroundColor: "#0284c7",
                          color: "#ffffff",
                          padding: "0.15rem 0.45rem",
                          borderRadius: "9999px",
                        }}
                      >
                        AI
                      </span>
                    )}

                    {item.badge && (
                      <span
                        style={{
                          fontSize: "0.65rem",
                          fontWeight: 700,
                          textTransform: "uppercase",
                          letterSpacing: "0.06em",
                          backgroundColor: "#059669",
                          color: "#ffffff",
                          padding: "0.15rem 0.45rem",
                          borderRadius: "9999px",
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Footer user profile & Logout */}
      <div
        style={{
          borderTop: "1px solid #f1f5f9",
          paddingTop: "0.85rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.6rem",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.7rem",
            padding: "0.4rem 0.6rem",
            borderRadius: "10px",
            backgroundColor: "#f8fafc",
            border: "1px solid #e2e8f0",
          }}
        >
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: "50%",
              backgroundColor: "#0284c7",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.875rem",
              fontWeight: 700,
              flexShrink: 0,
            }}
          >
            {userInitial}
          </div>

          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                fontSize: "0.8125rem",
                fontWeight: 600,
                color: "#0f172a",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {user?.full_name || "Medical Rep"}
            </div>
            <div
              style={{
                fontSize: "0.72rem",
                color: "#64748b",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {user?.email || "rep@pulsecrm.ai"}
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={handleLogout}
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "0.5rem",
            width: "100%",
            padding: "0.55rem",
            borderRadius: "8px",
            border: "1px solid #e2e8f0",
            backgroundColor: "#ffffff",
            color: "#475569",
            fontSize: "0.8125rem",
            fontWeight: 600,
            transition: "all 0.15s ease",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = "#fee2e2";
            e.currentTarget.style.borderColor = "#fecaca";
            e.currentTarget.style.color = "#dc2626";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = "#ffffff";
            e.currentTarget.style.borderColor = "#e2e8f0";
            e.currentTarget.style.color = "#475569";
          }}
        >
          <LogoutIcon style={{ fontSize: "1.1rem" }} />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}

export default Sidebar;
