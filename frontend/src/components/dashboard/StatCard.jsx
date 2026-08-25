import React from "react";

export function StatCard({
  label,
  value,
  accent = "#0284c7",
  hint = "Records in territory",
  icon: Icon,
}) {
  return (
    <div
      className="pulse-card pulse-card-interactive"
      style={{
        padding: "1.25rem",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        minHeight: "130px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Top row: Label & Icon/Accent */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            color: "#64748b",
          }}
        >
          {label}
        </span>
        {Icon ? (
          <div
            style={{
              width: 32,
              height: 32,
              borderRadius: 8,
              backgroundColor: `${accent}15`,
              color: accent,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon style={{ fontSize: "1.15rem" }} />
          </div>
        ) : (
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: accent,
            }}
          />
        )}
      </div>

      {/* Main Value */}
      <div
        style={{
          fontSize: "1.85rem",
          fontWeight: 700,
          color: "#0f172a",
          letterSpacing: "-0.025em",
          lineHeight: 1.1,
          marginTop: "0.5rem",
          marginBottom: "0.25rem",
        }}
      >
        {value}
      </div>

      {/* Hint / Subtitle */}
      <div
        style={{
          fontSize: "0.75rem",
          color: "#64748b",
          display: "flex",
          alignItems: "center",
          gap: "0.35rem",
        }}
      >
        {hint}
      </div>
    </div>
  );
}

export default StatCard;
