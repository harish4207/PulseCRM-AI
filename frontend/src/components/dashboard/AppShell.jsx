import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { useCopilot } from "../../context/CopilotContext";
import { AutoAwesome as SparkleIcon } from "@mui/icons-material";

export function AppShell({ title = "Dashboard", children }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { selectedHcpName, chatHistory } = useCopilot();

  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [mobileOpen]);

  return (
    <div style={{ display: "flex", minHeight: "100vh", backgroundColor: "#f8fafc" }}>
      {/* Desktop Sidebar (hidden on small screens) */}
      <div className="hidden md:block">
        <Sidebar />
      </div>

      {/* Mobile Drawer Overlay */}
      {mobileOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Mobile navigation menu"
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.45)",
            backdropFilter: "blur(3px)",
            zIndex: 50,
            display: "flex",
          }}
          onClick={() => setMobileOpen(false)}
        >
          <div
            style={{ height: "100%", backgroundColor: "#ffffff", maxWidth: "85vw" }}
            onClick={(e) => e.stopPropagation()}
          >
            <Sidebar isMobile onClose={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
          overflowX: "hidden",
        }}
      >
        <Topbar title={title} onMenuClick={() => setMobileOpen(true)} />

        <main
          className="px-4 sm:px-6 md:px-10 py-6 sm:py-8"
          style={{
            flex: 1,
            maxWidth: "1120px",
            width: "100%",
            margin: "0 auto",
            boxSizing: "border-box",
          }}
        >
          {children}
        </main>
      </div>

      {/* Floating Global Copilot Dock (when away from /voice-copilot) */}
      {location.pathname !== "/voice-copilot" && chatHistory.length > 0 && (
        <button
          type="button"
          onClick={() => navigate("/voice-copilot")}
          style={{
            position: "fixed",
            bottom: "20px",
            right: "20px",
            display: "flex",
            alignItems: "center",
            gap: "0.45rem",
            padding: "0.55rem 0.95rem",
            backgroundColor: "#0284c7",
            color: "#ffffff",
            borderRadius: "9999px",
            boxShadow: "0 10px 15px -3px rgba(2, 132, 199, 0.35), 0 4px 6px -4px rgba(2, 132, 199, 0.2)",
            border: "none",
            cursor: "pointer",
            zIndex: 40,
            fontSize: "0.8rem",
            fontWeight: 600,
            transition: "all 0.2s ease",
            minHeight: "44px",
          }}
          aria-label="Return to Ask PulseCRM Copilot"
        >
          <SparkleIcon style={{ fontSize: "1rem" }} />
          <span>
            {selectedHcpName ? `Copilot · ${selectedHcpName}` : `Ask PulseCRM (${chatHistory.length})`}
          </span>
        </button>
      )}
    </div>
  );
}

export default AppShell;
