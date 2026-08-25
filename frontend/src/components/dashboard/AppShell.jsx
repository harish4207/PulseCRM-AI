import React, { useState, useEffect } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";

export function AppShell({ title = "Dashboard", children }) {
  const [mobileOpen, setMobileOpen] = useState(false);

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
          className="p-3 sm:p-5 md:p-6"
          style={{
            flex: 1,
            maxWidth: "1200px",
            width: "100%",
            margin: "0 auto",
            boxSizing: "border-box",
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}

export default AppShell;
