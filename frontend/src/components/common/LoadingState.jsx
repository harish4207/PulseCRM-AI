import React from "react";

export function LoadingState({ label = "Loading intelligence data...", variant = "spinner" }) {
  if (variant === "skeleton") {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: "1rem" }}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="pulse-card" style={{ padding: "1.25rem", minHeight: "120px", display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            <div className="skeleton-box" style={{ width: "40%", height: "14px" }} />
            <div className="skeleton-box" style={{ width: "60%", height: "28px" }} />
            <div className="skeleton-box" style={{ width: "80%", height: "12px" }} />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "220px",
        gap: "0.85rem",
        color: "#64748b",
        padding: "2rem",
      }}
    >
      <div
        style={{
          width: 38,
          height: 38,
          border: "3px solid #e2e8f0",
          borderTopColor: "#0284c7",
          borderRadius: "50%",
          animation: "spin 0.75s linear infinite",
        }}
      />
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
      <span style={{ fontSize: "0.875rem", fontWeight: 600, color: "#475569" }}>{label}</span>
    </div>
  );
}

export default LoadingState;
