import React from "react";
import { useSelector } from "react-redux";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Menu as MenuIcon,
  Search as SearchIcon,
  NotificationsNoneOutlined as NotificationIcon,
  AutoAwesome as SparkleIcon,
} from "@mui/icons-material";
import { useCopilot } from "../../context/CopilotContext";

export function Topbar({ title = "Dashboard", onMenuClick }) {
  const { user } = useSelector((state) => state.auth ?? {});
  const userInitial = (user?.full_name || "U").charAt(0).toUpperCase();
  const navigate = useNavigate();
  const location = useLocation();
  const { selectedHcpName, chatHistory, pendingConfirmation } = useCopilot();

  return (
    <header
      className="px-3 md:px-6"
      style={{
        height: "64px",
        backgroundColor: "#ffffff",
        borderBottom: "1px solid #e2e8f0",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        position: "sticky",
        top: 0,
        zIndex: 30,
      }}
    >
      {/* Left title & mobile trigger */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", minWidth: 0 }}>
        {onMenuClick && (
          <button
            type="button"
            onClick={onMenuClick}
            className="md:hidden"
            style={{
              padding: "0.5rem",
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
              color: "#475569",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "#f8fafc",
              minWidth: "44px",
              minHeight: "44px",
              flexShrink: 0,
            }}
            aria-label="Open navigation"
          >
            <MenuIcon fontSize="small" />
          </button>
        )}

        <div style={{ minWidth: 0 }}>
          <div
            style={{
              fontSize: "0.65rem",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              color: "#64748b",
              lineHeight: 1,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            PulseCRM Platform
          </div>
          <h2
            style={{
              fontSize: "1.05rem",
              fontWeight: 700,
              color: "#0f172a",
              lineHeight: 1.25,
              marginTop: "2px",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {title}
          </h2>
        </div>
      </div>

      {/* Right actions: Search, Notifications, Avatar */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexShrink: 0 }}>
        {/* Search bar (Desktop only - never crowd mobile header) */}
        <div
          style={{
            position: "relative",
            display: "flex",
            alignItems: "center",
          }}
          className="hidden md:flex"
        >
          <SearchIcon
            style={{
              position: "absolute",
              left: "10px",
              fontSize: "1.1rem",
              color: "#94a3b8",
            }}
          />
          <input
            type="text"
            placeholder="Search HCPs, records..."
            style={{
              padding: "0.45rem 0.75rem 0.45rem 2rem",
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
              backgroundColor: "#f8fafc",
              fontSize: "0.8125rem",
              color: "#0f172a",
              width: "190px",
            }}
          />
        </div>

        {/* Global Copilot Access Pill - Responsive compact on mobile */}
        {location.pathname !== "/voice-copilot" && (
          <button
            type="button"
            onClick={() => navigate("/voice-copilot")}
            title="Open Ask PulseCRM AI Assistant"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.3rem",
              padding: "0.35rem 0.6rem",
              borderRadius: "20px",
              border: "1px solid #bae6fd",
              backgroundColor: "#f0f9ff",
              color: "#0369a1",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.15s ease",
              minHeight: "36px",
              flexShrink: 0,
            }}
            aria-label="Navigate to Ask PulseCRM"
          >
            <SparkleIcon style={{ fontSize: "0.95rem", color: "#0284c7", flexShrink: 0 }} />
            <span className="hidden sm:inline" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "160px" }}>
              {selectedHcpName
                ? `Context: ${selectedHcpName}`
                : pendingConfirmation
                ? `Pending Action`
                : chatHistory.length > 0
                ? `Copilot (${chatHistory.length})`
                : `Ask PulseCRM`}
            </span>
          </button>
        )}

        {/* Notifications */}
        <button
          type="button"
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "8px",
            border: "1px solid #e2e8f0",
            backgroundColor: "#ffffff",
            color: "#64748b",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
          }}
          aria-label="Notifications"
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#f8fafc")}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#ffffff")}
        >
          <NotificationIcon style={{ fontSize: "1.2rem" }} />
          <span
            style={{
              position: "absolute",
              top: "8px",
              right: "8px",
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              backgroundColor: "#0284c7",
            }}
          />
        </button>

        {/* User avatar chip */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.6rem",
            padding: "0.3rem 0.6rem",
            borderRadius: "8px",
            border: "1px solid #e2e8f0",
            backgroundColor: "#ffffff",
          }}
        >
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              backgroundColor: "#0284c7",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.8125rem",
              fontWeight: 700,
            }}
          >
            {userInitial}
          </div>
          <span
            style={{
              fontSize: "0.8125rem",
              fontWeight: 600,
              color: "#0f172a",
            }}
            className="hidden sm:inline"
          >
            {user?.full_name?.split(" ")[0] || "User"}
          </span>
        </div>
      </div>
    </header>
  );
}

export default Topbar;
