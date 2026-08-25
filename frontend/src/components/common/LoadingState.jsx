import React from "react";

export function LoadingState({ label = "Loading intelligence data..." }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "240px",
        gap: "1rem",
        color: "#64748b",
      }}
    >
      <div
        style={{
          width: 36,
          height: 36,
          border: "3px solid #e2e8f0",
          borderTopColor: "#0284c7",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }}
      />
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
      <span style={{ fontSize: "0.875rem", fontWeight: 500 }}>{label}</span>
    </div>
  );
}

export default LoadingState;
