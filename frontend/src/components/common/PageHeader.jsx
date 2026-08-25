import React from "react";

export function PageHeader({
  title,
  description,
  tag,
  actions,
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "row",
        alignItems: "flex-start",
        justifyContent: "space-between",
        gap: "1.25rem",
        marginBottom: "1.5rem",
        flexWrap: "wrap",
      }}
    >
      <div style={{ maxWidth: "720px" }}>
        {tag && (
          <div
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#0284c7",
              marginBottom: "0.35rem",
            }}
          >
            {tag}
          </div>
        )}
        <h1
          className="text-2xl sm:text-3xl font-bold text-slate-900"
          style={{
            letterSpacing: "-0.025em",
            lineHeight: 1.2,
            margin: 0,
          }}
        >
          {title}
        </h1>
        {description && (
          <p
            style={{
              fontSize: "0.9375rem",
              color: "#64748b",
              lineHeight: 1.5,
              margin: "0.4rem 0 0",
            }}
          >
            {description}
          </p>
        )}
      </div>

      {actions && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            flexWrap: "wrap",
          }}
        >
          {actions}
        </div>
      )}
    </div>
  );
}

export default PageHeader;
