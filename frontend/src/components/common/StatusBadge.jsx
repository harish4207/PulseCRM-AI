import React from "react";

const variants = {
  success: {
    bg: "#ecfdf5",
    text: "#059669",
    border: "#a7f3d0",
    dot: "#10b981",
  },
  scheduled: {
    bg: "#fffbeb",
    text: "#d97706",
    border: "#fde68a",
    dot: "#f59e0b",
  },
  pending: {
    bg: "#fef2f2",
    text: "#dc2626",
    border: "#fecaca",
    dot: "#ef4444",
  },
  specialty: {
    bg: "#f0fdf4",
    text: "#166534",
    border: "#bbf7d0",
    dot: "#22c55e",
  },
  product: {
    bg: "#eff6ff",
    text: "#1d4ed8",
    border: "#bfdbfe",
    dot: "#3b82f6",
  },
  neutral: {
    bg: "#f1f5f9",
    text: "#475569",
    border: "#e2e8f0",
    dot: "#94a3b8",
  },
  teal: {
    bg: "#ccfbf1",
    text: "#0f766e",
    border: "#99f6e4",
    dot: "#0d9488",
  },
};

export function StatusBadge({
  children,
  variant = "neutral",
  size = "sm",
  withDot = true,
}) {
  const style = variants[variant] || variants.neutral;
  const isSmall = size === "sm";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: isSmall ? "0.35rem" : "0.5rem",
        padding: isSmall ? "0.2rem 0.55rem" : "0.3rem 0.75rem",
        borderRadius: "9999px",
        fontSize: isSmall ? "0.75rem" : "0.8125rem",
        fontWeight: 600,
        lineHeight: 1,
        backgroundColor: style.bg,
        color: style.text,
        border: `1px solid ${style.border}`,
        whiteSpace: "nowrap",
        letterSpacing: "0.01em",
      }}
    >
      {withDot && (
        <span
          style={{
            width: isSmall ? 6 : 8,
            height: isSmall ? 6 : 8,
            borderRadius: "50%",
            backgroundColor: style.dot,
            flexShrink: 0,
          }}
        />
      )}
      {children}
    </span>
  );
}

export default StatusBadge;
