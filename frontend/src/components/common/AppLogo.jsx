import React from "react";

export function AppLogo({ collapsed = false, size = "md" }) {
  const isSmall = size === "sm";

  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", userSelect: "none" }}>
      <div
        style={{
          width: isSmall ? 32 : 38,
          height: isSmall ? 32 : 38,
          borderRadius: 10,
          background: "linear-gradient(135deg, #0284c7 0%, #0d9488 100%)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: "0 2px 8px rgba(2, 132, 199, 0.25)",
          flexShrink: 0,
        }}
      >
        <svg
          width={isSmall ? 18 : 22}
          height={isSmall ? 18 : 22}
          viewBox="0 0 24 24"
          fill="none"
          stroke="#ffffff"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
      </div>

      {!collapsed && (
        <div style={{ display: "flex", flexDirection: "column" }}>
          <div
            style={{
              fontSize: isSmall ? "1.05rem" : "1.2rem",
              fontWeight: 700,
              letterSpacing: "-0.03em",
              color: "#0f172a",
              lineHeight: 1.2,
            }}
          >
            Pulse<span style={{ color: "#0284c7" }}>CRM</span>
          </div>
          <div
            style={{
              fontSize: "0.68rem",
              fontWeight: 600,
              letterSpacing: "0.06em",
              textTransform: "uppercase",
              color: "#64748b",
              lineHeight: 1,
              marginTop: "2px",
            }}
          >
            Healthcare Intelligence
          </div>
        </div>
      )}
    </div>
  );
}

export default AppLogo;
