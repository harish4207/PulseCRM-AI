import React from "react";
import { useSelector } from "react-redux";

export function WelcomeCard({ name }) {
  const { user } = useSelector((state) => state.auth ?? {});
  const displayName = name || user?.full_name || "Clinical Representative";

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  const todayFormatted = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date());

  return (
    <div
      className="pulse-card"
      style={{
        background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
        borderRadius: "16px",
        padding: "1.5rem 1.75rem",
        color: "#ffffff",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "1rem",
        boxShadow: "0 4px 20px rgba(15, 23, 42, 0.15)",
        position: "relative",
        overflow: "hidden",
        border: "1px solid #334155",
      }}
    >
      {/* Background subtle healthcare wave accent */}
      <div
        style={{
          position: "absolute",
          right: "-15px",
          top: "-15px",
          width: "240px",
          height: "160px",
          opacity: 0.08,
          pointerEvents: "none",
        }}
      >
        <svg viewBox="0 0 200 200" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M0 100C40 60 80 140 120 100C160 60 200 140 240 100"
            stroke="#ffffff"
            strokeWidth="16"
            strokeLinecap="round"
          />
        </svg>
      </div>

      <div>
        <div
          style={{
            fontSize: "0.72rem",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
            color: "#38bdf8",
            marginBottom: "0.25rem",
          }}
        >
          {todayFormatted}
        </div>
        <h2
          style={{
            fontSize: "1.45rem",
            fontWeight: 700,
            color: "#ffffff",
            letterSpacing: "-0.02em",
            lineHeight: 1.25,
            margin: 0,
          }}
        >
          {getGreeting()}, {displayName}
        </h2>
        <p
          style={{
            fontSize: "0.875rem",
            color: "#94a3b8",
            marginTop: "0.35rem",
            margin: "0.35rem 0 0",
          }}
        >
          Here's your territory relationship intelligence summary.
        </p>
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.55rem",
          backgroundColor: "rgba(255, 255, 255, 0.08)",
          padding: "0.45rem 0.85rem",
          borderRadius: "9999px",
          border: "1px solid rgba(255, 255, 255, 0.12)",
        }}
      >
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            backgroundColor: "#10b981",
            boxShadow: "0 0 0 3px rgba(16, 185, 129, 0.2)",
          }}
        />
        <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#f1f5f9" }}>
          AI Relationship Copilot Active
        </span>
      </div>
    </div>
  );
}

export default WelcomeCard;
