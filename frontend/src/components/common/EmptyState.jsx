import React from "react";

export function EmptyState({
  title = "No records found",
  description = "Get started by adding your first record or connecting live data.",
  action = null,
  iconType = "medical",
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "3rem 1.5rem",
        borderRadius: "16px",
        border: "1px dashed #cbd5e1",
        backgroundColor: "#f8fafc",
        minHeight: "220px",
      }}
    >
      <div
        style={{
          width: 56,
          height: 56,
          borderRadius: 16,
          backgroundColor: "#e0f2fe",
          color: "#0284c7",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "1rem",
          boxShadow: "0 2px 8px rgba(2, 132, 199, 0.12)",
        }}
      >
        {iconType === "ai" ? (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
        ) : iconType === "user" ? (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        ) : (
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
            <line x1="10" y1="9" x2="8" y2="9" />
          </svg>
        )}
      </div>

      <h3
        style={{
          fontSize: "1.05rem",
          fontWeight: 600,
          color: "#0f172a",
          marginBottom: "0.35rem",
          letterSpacing: "-0.01em",
        }}
      >
        {title}
      </h3>

      <p
        style={{
          fontSize: "0.875rem",
          color: "#64748b",
          maxWidth: "420px",
          lineHeight: 1.5,
          marginBottom: action ? "1.25rem" : 0,
        }}
      >
        {description}
      </p>

      {action && <div>{action}</div>}
    </div>
  );
}

export default EmptyState;
