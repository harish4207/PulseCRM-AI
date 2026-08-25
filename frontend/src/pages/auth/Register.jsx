import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import {
  VisibilityOutlined as VisibilityIcon,
  VisibilityOffOutlined as VisibilityOffIcon,
  CheckCircle as CheckIcon,
  AutoAwesome as AiSparkleIcon,
} from "@mui/icons-material";

import authService from "../../services/authService";
import { setError, setLoading } from "../../store/slices/authSlice";
import AppLogo from "../../components/common/AppLogo";

const initialForm = {
  full_name: "",
  email: "",
  password: "",
};

export function Register() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { isAuthenticated, loading, error } = useSelector((state) => state.auth ?? {});
  const [form, setForm] = useState(initialForm);
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

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
    setSuccessMessage("");
    dispatch(setError(null));
  };

  const validateForm = () => {
    if (!form.full_name.trim() || !form.email.trim() || !form.password.trim()) {
      setFormError("All fields are required.");
      return false;
    }

    if (form.password.length < 6) {
      setFormError("Password must be at least 6 characters long.");
      return false;
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(form.email.trim())) {
      setFormError("Please enter a valid email address.");
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
      await authService.register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
      });

      setSuccessMessage("Registration successful! Redirecting to sign in...");
      setTimeout(() => {
        navigate("/login");
      }, 1200);
    } catch (err) {
      const message =
        err?.userMessage ||
        err?.response?.data?.detail ||
        err?.message ||
        "Registration failed. Please try again.";
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
      {/* Left hero pane */}
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
        <div
          style={{
            position: "absolute",
            top: "-10%",
            right: "-10%",
            width: "500px",
            height: "500px",
            background: "radial-gradient(circle, rgba(13, 148, 136, 0.18) 0%, rgba(15, 23, 42, 0) 70%)",
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
              color: "#2dd4bf",
              marginBottom: "2rem",
            }}
          >
            <AiSparkleIcon style={{ fontSize: "1rem" }} />
            <span>Join PulseCRM</span>
          </div>

          <h1
            style={{
              fontSize: "2.4rem",
              fontWeight: 800,
              letterSpacing: "-0.03em",
              lineHeight: 1.2,
              maxWidth: "480px",
              color: "#ffffff",
            }}
          >
            Empower your clinical sales relationships.
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
            Create an account to start logging field visits, automating doctor commitments, and gaining territory intelligence.
          </p>
        </div>

        {/* Benefits list */}
        <div style={{ display: "flex", flexDirection: "column", gap: "1rem", maxWidth: "420px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <CheckIcon style={{ color: "#2dd4bf", fontSize: "1.25rem" }} />
            <span style={{ fontSize: "0.875rem", color: "#e2e8f0" }}>
              Fast voice/text meeting extraction
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <CheckIcon style={{ color: "#2dd4bf", fontSize: "1.25rem" }} />
            <span style={{ fontSize: "0.875rem", color: "#e2e8f0" }}>
              Automated HCP directory and hospital tracking
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
            <CheckIcon style={{ color: "#2dd4bf", fontSize: "1.25rem" }} />
            <span style={{ fontSize: "0.875rem", color: "#e2e8f0" }}>
              Smart follow-up timeline reminders
            </span>
          </div>
        </div>

        <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
          © 2026 PulseCRM AI. Enterprise-grade medical CRM.
        </div>
      </div>

      {/* Right form pane */}
      <div
        className="p-4 sm:p-8"
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          width: "100%",
        }}
      >
        <div style={{ width: "100%", maxWidth: "400px" }}>
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
              Create representative account
            </h2>
            <p style={{ fontSize: "0.875rem", color: "#64748b", marginTop: "0.35rem" }}>
              Enter your details to get started with PulseCRM.
            </p>
          </div>

          {successMessage && (
            <div
              style={{
                padding: "0.75rem 1rem",
                borderRadius: "10px",
                backgroundColor: "#ecfdf5",
                border: "1px solid #a7f3d0",
                color: "#059669",
                fontSize: "0.8125rem",
                marginBottom: "1.25rem",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
              }}
            >
              <CheckIcon style={{ fontSize: "1rem" }} />
              <span>{successMessage}</span>
            </div>
          )}

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
              }}
            >
              {submitError || error}
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
            {/* Full Name */}
            <div>
              <label
                htmlFor="full_name"
                style={{
                  display: "block",
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  color: "#334155",
                  marginBottom: "0.35rem",
                }}
              >
                Full name
              </label>
              <input
                id="full_name"
                name="full_name"
                type="text"
                placeholder="Dr. / Rep John Doe"
                value={form.full_name}
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

            {/* Email */}
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
                Work email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                placeholder="name@pharma.com"
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

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                style={{
                  display: "block",
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  color: "#334155",
                  marginBottom: "0.35rem",
                }}
              >
                Password (min. 6 characters)
              </label>
              <div style={{ position: "relative" }}>
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
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
                <span>Creating account...</span>
              ) : (
                <span>Create account</span>
              )}
            </button>
          </form>

          <div
            style={{
              marginTop: "1.5rem",
              textAlign: "center",
              fontSize: "0.8125rem",
              color: "#64748b",
            }}
          >
            Already have an account?{" "}
            <Link
              to="/login"
              style={{
                color: "#0284c7",
                fontWeight: 600,
                textDecoration: "none",
              }}
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Register;
