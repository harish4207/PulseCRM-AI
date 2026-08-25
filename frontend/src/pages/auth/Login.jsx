import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import {
  VisibilityOutlined as VisibilityIcon,
  VisibilityOffOutlined as VisibilityOffIcon,
  AutoAwesome as AiSparkleIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
} from "@mui/icons-material";

import authService from "../../services/authService";
import { loginSuccess, setError, setLoading } from "../../store/slices/authSlice";
import AppLogo from "../../components/common/AppLogo";

const initialForm = {
  email: "",
  password: "",
};

export function Login() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { isAuthenticated, loading, error } = useSelector((state) => state.auth ?? {});
  const [form, setForm] = useState(initialForm);
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState("");
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/dashboard", { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    setFormError("");
    setSubmitError("");
    dispatch(setError(null));
  };

  const validateForm = () => {
    if (!form.email.trim() || !form.password.trim()) {
      setFormError("Email and password are required.");
      return false;
    }
    return true;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    if (!validateForm()) {
      return;
    }

    dispatch(setLoading(true));

    try {
      const response = await authService.login({
        email: form.email.trim(),
        password: form.password,
      });

      const token = response?.access_token;
      if (!token) {
        throw new Error("No access token returned from server.");
      }

      const currentUser = await authService.getCurrentUser();
      dispatch(loginSuccess({ token, user: currentUser }));
      navigate("/dashboard", { replace: true });
    } catch (err) {
      const message =
        err?.userMessage ||
        err?.response?.data?.detail ||
        err?.message ||
        "Unable to sign in. Please verify your credentials.";
      setSubmitError(message);
      dispatch(setError(message));
    } finally {
      dispatch(setLoading(false));
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        backgroundColor: "#f8fafc",
      }}
    >
      {/* Left hero pane (visible on large screens) */}
      <div
        className="hidden lg:flex"
        style={{
          flex: 1,
          backgroundColor: "#0f172a",
          color: "#ffffff",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "3.5rem",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Subtle background glow */}
        <div
          style={{
            position: "absolute",
            top: "-10%",
            right: "-10%",
            width: "500px",
            height: "500px",
            background: "radial-gradient(circle, rgba(2, 132, 199, 0.18) 0%, rgba(15, 23, 42, 0) 70%)",
            borderRadius: "50%",
            pointerEvents: "none",
          }}
        />

        <div>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              padding: "0.4rem 0.8rem",
              borderRadius: "9999px",
              backgroundColor: "rgba(255, 255, 255, 0.08)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "#38bdf8",
              marginBottom: "2rem",
            }}
          >
            <AiSparkleIcon style={{ fontSize: "1rem" }} />
            <span>Healthcare Relationship Intelligence</span>
          </div>

          <h1
            style={{
              fontSize: "2.5rem",
              fontWeight: 800,
              letterSpacing: "-0.03em",
              lineHeight: 1.2,
              maxWidth: "480px",
              color: "#ffffff",
            }}
          >
            Smarter doctor relationships, powered by AI.
          </h1>

          <p
            style={{
              fontSize: "1.05rem",
              color: "#94a3b8",
              marginTop: "1.25rem",
              maxWidth: "440px",
              lineHeight: 1.6,
            }}
          >
            Log meetings in natural language, automatically extract HCP commitments, and never miss a clinical follow-up.
          </p>
        </div>

        {/* Feature Highlights */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", maxWidth: "420px" }}>
          <div style={{ display: "flex", alignItems: "flex-start", gap: "1rem" }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                backgroundColor: "rgba(2, 132, 199, 0.15)",
                color: "#38bdf8",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <AiSparkleIcon style={{ fontSize: "1.2rem" }} />
            </div>
            <div>
              <div style={{ fontSize: "0.9rem", fontWeight: 600, color: "#ffffff" }}>
                Agentic Meeting Parsing
              </div>
              <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "2px" }}>
                Converts voice memos and unstructured notes into structured CRM records.
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "flex-start", gap: "1rem" }}>
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: 10,
                backgroundColor: "rgba(13, 148, 136, 0.15)",
                color: "#2dd4bf",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <SecurityIcon style={{ fontSize: "1.2rem" }} />
            </div>
            <div>
              <div style={{ fontSize: "0.9rem", fontWeight: 600, color: "#ffffff" }}>
                Enterprise Compliant & Secure
              </div>
              <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "2px" }}>
                Built with strict healthcare relationship governance and JWT security.
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Trust info */}
        <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
          © 2026 PulseCRM AI. Designed for pharmaceutical & medical field teams.
        </div>
      </div>

      {/* Right form pane */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: "2rem",
        }}
      >
        <div style={{ width: "100%", maxWidth: "400px" }}>
          {/* Logo */}
          <div style={{ marginBottom: "2rem" }}>
            <AppLogo size="md" />
          </div>

          <div style={{ marginBottom: "1.75rem" }}>
            <h2
              style={{
                fontSize: "1.5rem",
                fontWeight: 700,
                color: "#0f172a",
                letterSpacing: "-0.02em",
                margin: 0,
              }}
            >
              Sign in to your account
            </h2>
            <p style={{ fontSize: "0.875rem", color: "#64748b", marginTop: "0.35rem" }}>
              Enter your credentials to access your territory dashboard.
            </p>
          </div>

          {(submitError || error) && (
            <div
              style={{
                padding: "0.75rem 1rem",
                borderRadius: "10px",
                backgroundColor: "#fef2f2",
                border: "1px solid #fecaca",
                color: "#dc2626",
                fontSize: "0.8125rem",
                marginBottom: "1.25rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <span>{submitError || error}</span>
            </div>
          )}

          {formError && (
            <div
              style={{
                padding: "0.75rem 1rem",
                borderRadius: "10px",
                backgroundColor: "#fffbeb",
                border: "1px solid #fde68a",
                color: "#d97706",
                fontSize: "0.8125rem",
                marginBottom: "1.25rem",
              }}
            >
              {formError}
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.1rem" }}>
            {/* Email input */}
            <div>
              <label
                htmlFor="email"
                style={{
                  display: "block",
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  color: "#334155",
                  marginBottom: "0.35rem",
                }}
              >
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                placeholder="name@company.com"
                value={form.email}
                onChange={handleChange}
                disabled={loading}
                style={{
                  width: "100%",
                  padding: "0.65rem 0.85rem",
                  borderRadius: "10px",
                  border: "1px solid #cbd5e1",
                  backgroundColor: "#ffffff",
                  fontSize: "0.875rem",
                  color: "#0f172a",
                }}
              />
            </div>

            {/* Password input */}
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.35rem" }}>
                <label
                  htmlFor="password"
                  style={{
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    color: "#334155",
                  }}
                >
                  Password
                </label>
              </div>

              <div style={{ position: "relative" }}>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={form.password}
                  onChange={handleChange}
                  disabled={loading}
                  style={{
                    width: "100%",
                    padding: "0.65rem 2.5rem 0.65rem 0.85rem",
                    borderRadius: "10px",
                    border: "1px solid #cbd5e1",
                    backgroundColor: "#ffffff",
                    fontSize: "0.875rem",
                    color: "#0f172a",
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: "absolute",
                    right: "10px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "#94a3b8",
                    display: "flex",
                    alignItems: "center",
                    padding: "0.2rem",
                  }}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <VisibilityOffIcon style={{ fontSize: "1.15rem" }} />
                  ) : (
                    <VisibilityIcon style={{ fontSize: "1.15rem" }} />
                  )}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: "0.5rem",
                width: "100%",
                padding: "0.75rem 1rem",
                borderRadius: "10px",
                backgroundColor: loading ? "#94a3b8" : "#0284c7",
                color: "#ffffff",
                fontSize: "0.875rem",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "0.5rem",
                boxShadow: "0 2px 6px rgba(2, 132, 199, 0.25)",
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? (
                <span>Signing in...</span>
              ) : (
                <span>Sign in to PulseCRM</span>
              )}
            </button>
          </form>

          {/* Registration link */}
          <div
            style={{
              marginTop: "1.5rem",
              textAlign: "center",
              fontSize: "0.8125rem",
              color: "#64748b",
            }}
          >
            Don't have an account?{" "}
            <Link
              to="/register"
              style={{
                color: "#0284c7",
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              Create representative account
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Login;
