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
      <div style={{ maxWidth: "700px" }}>
        {tag && (
          <div
            style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
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
          style={{
            fontSize: "1.6rem",
            fontWeight: 700,
            color: "#0f172a",
            letterSpacing: "-0.025em",
            lineHeight: 1.25,
            margin: 0,
          }}
        >
          {title}
        </h1>
        {description && (
          <p
            style={{
              fontSize: "0.875rem",
              color: "#64748b",
              marginTop: "0.35rem",
              lineHeight: 1.5,
              margin: "0.35rem 0 0",
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
