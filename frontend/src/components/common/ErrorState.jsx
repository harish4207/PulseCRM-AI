import React from "react";
import { ErrorOutline as ErrorIcon, Refresh as RefreshIcon } from "@mui/icons-material";

export function ErrorState({
  title = "Something went wrong",
  message = "We couldn't load this information. Please try again.",
  onRetry = null,
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        padding: "2.5rem 1.5rem",
        borderRadius: "14px",
        border: "1px solid #fee2e2",
        backgroundColor: "#fffafa",
        minHeight: "180px",
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: "50%",
          backgroundColor: "#fee2e2",
          color: "#dc2626",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "0.85rem",
        }}
      >
        <ErrorIcon style={{ fontSize: "1.6rem" }} />
      </div>

      <h3
        style={{
          fontSize: "1rem",
          fontWeight: 700,
          color: "#991b1b",
          marginBottom: "0.25rem",
        }}
      >
        {title}
      </h3>

      <p
        style={{
          fontSize: "0.825rem",
          color: "#7f1d1d",
          maxWidth: "400px",
          lineHeight: 1.5,
          marginBottom: onRetry ? "1rem" : 0,
        }}
      >
        {message}
      </p>

      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "0.35rem",
            padding: "0.5rem 1rem",
            borderRadius: "8px",
            backgroundColor: "#ffffff",
            color: "#b91c1c",
            border: "1px solid #fca5a5",
            fontSize: "0.8rem",
            fontWeight: 600,
            cursor: "pointer",
            boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
            minHeight: "44px",
          }}
        >
          <RefreshIcon style={{ fontSize: "1rem" }} />
          <span>Try again</span>
        </button>
      )}
    </div>
  );
}

export default ErrorState;
