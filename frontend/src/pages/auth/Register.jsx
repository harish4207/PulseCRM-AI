import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import {
  VisibilityOutlined as VisibilityIcon,
  VisibilityOffOutlined as VisibilityOffIcon,
  CheckCircle as CheckIcon,
  AutoAwesome as SparkleIcon,
  Email as MailIcon,
} from "@mui/icons-material";

import authService from "../../services/authService";
import { setError, setLoading } from "../../store/slices/authSlice";
import AppLogo from "../../components/common/AppLogo";

const initialForm = {
  full_name: "",
  email: "",
  password: "",
  confirm_password: "",
};

export function Register() {
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { isAuthenticated, loading, error } = useSelector((state) => state.auth ?? {});
  const [form, setForm] = useState(initialForm);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [formError, setFormError] = useState("");
  const [submitError, setSubmitError] = useState("");
  const [registeredEmail, setRegisteredEmail] = useState(null);

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
    if (!form.full_name.trim() || !form.email.trim() || !form.password.trim() || !form.confirm_password.trim()) {
      setFormError("All fields are required.");
      return false;
    }

    if (form.password.length < 8) {
      setFormError("Password must be at least 8 characters long.");
      return false;
    }

    if (form.password !== form.confirm_password) {
      setFormError("Passwords do not match.");
      return false;
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailPattern.test(form.email.trim())) {
      setFormError("Please enter a valid work email address.");
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

      setRegisteredEmail(form.email.trim());
    } catch (err) {
      const message =
        err?.userMessage ||
        err?.response?.data?.detail ||
        err?.message ||
        "Registration failed. Please check your details and try again.";
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
        flexDirection: "row",
        backgroundColor: "#f8fafc",
        width: "100%",
        boxSizing: "border-box",
        overflowX: "hidden",
      }}
    >
      {/* Left branding pane (desktop) */}
      <div
        className="hidden lg:flex"
        style={{
          flex: "1 1 50%",
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
            width: "450px",
            height: "450px",
            background: "radial-gradient(circle, rgba(2, 132, 199, 0.22) 0%, rgba(15, 23, 42, 0) 70%)",
            borderRadius: "50%",
            pointerEvents: "none",
          }}
        />

        <div>
          <div style={{ marginBottom: "2.5rem" }}>
            <AppLogo size="md" />
          </div>

          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.4rem",
              padding: "0.3rem 0.75rem",
              borderRadius: "9999px",
              backgroundColor: "rgba(2, 132, 199, 0.15)",
              border: "1px solid rgba(56, 189, 248, 0.25)",
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "#38bdf8",
              marginBottom: "1.5rem",
            }}
          >
            <SparkleIcon style={{ fontSize: "0.95rem" }} />
            <span>AI-First CRM for Field Sales</span>
          </div>

          <h1
            style={{
              fontSize: "2.25rem",
              fontWeight: 800,
              letterSpacing: "-0.03em",
              lineHeight: 1.25,
              color: "#ffffff",
              marginBottom: "1rem",
              maxWidth: "480px",
            }}
          >
            Start managing doctor relationships with AI
          </h1>

          <p
            style={{
              fontSize: "1rem",
              color: "#94a3b8",
              maxWidth: "440px",
              lineHeight: 1.6,
              marginBottom: "2.5rem",
            }}
          >
            Equip your pharmaceutical and healthcare field teams with conversational logging, automatic scheduling, and relationship intelligence.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: "1rem", maxWidth: "420px" }}>
            {[
              "Real-time voice and text conversation",
              "Structured doctor interaction history",
              "Automated meeting follow-up reminders",
              "Zero manual data entry overhead",
            ].map((benefit, idx) => (
              <div key={idx} style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <CheckIcon style={{ fontSize: "1.2rem", color: "#38bdf8", flexShrink: 0 }} />
                <span style={{ fontSize: "0.9rem", color: "#e2e8f0", fontWeight: 500 }}>{benefit}</span>
              </div>
            ))}
          </div>
        </div>

        <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "2rem" }}>
          © 2026 PulseCRM. Enterprise Grade Healthcare Intelligence.
        </div>
      </div>

      {/* Right form pane */}
      <div
        className="p-4 sm:p-8 md:p-12"
        style={{
          flex: "1 1 50%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          minWidth: 0,
          boxSizing: "border-box",
        }}
      >
        <div style={{ width: "100%", maxWidth: "400px", boxSizing: "border-box" }}>
          {/* Mobile branding header */}
          <div className="lg:hidden" style={{ marginBottom: "1.5rem", textAlign: "center" }}>
            <div style={{ display: "flex", justifyContent: "center", marginBottom: "0.75rem" }}>
              <AppLogo size="md" />
            </div>
            <p style={{ fontSize: "0.8rem", color: "#64748b", margin: 0 }}>
              AI-Powered Doctor Relationship CRM
            </p>
          </div>

          {registeredEmail ? (
            /* Post-registration Verification State (Section 5) */
            <div
              style={{
                textAlign: "center",
                padding: "2rem 1rem",
                borderRadius: "14px",
                backgroundColor: "#ffffff",
                border: "1px solid #e2e8f0",
                boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
              }}
            >
              <div
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: "50%",
                  backgroundColor: "#e0f2fe",
                  color: "#0284c7",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 1.25rem",
                }}
              >
                <MailIcon style={{ fontSize: "1.8rem" }} />
              </div>

              <h2 style={{ fontSize: "1.35rem", fontWeight: 700, color: "#0f172a", marginBottom: "0.5rem" }}>
                Check your inbox
              </h2>

              <p style={{ fontSize: "0.875rem", color: "#64748b", lineHeight: 1.55, marginBottom: "1.5rem" }}>
                We've sent a verification link to <strong>{registeredEmail}</strong>. You can now sign in to your PulseCRM account.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                <Link
                  to="/login"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "0.75rem 1rem",
                    borderRadius: "10px",
                    backgroundColor: "#0284c7",
                    color: "#ffffff",
                    fontWeight: 600,
                    fontSize: "0.875rem",
                    textDecoration: "none",
                    minHeight: "44px",
                  }}
                >
                  Back to sign in
                </Link>
              </div>
            </div>
          ) : (
            <>
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
                  Create your PulseCRM account
                </h2>
                <p style={{ fontSize: "0.875rem", color: "#64748b", marginTop: "0.35rem" }}>
                  Start managing your doctor relationships with an AI-powered CRM.
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
                    lineHeight: 1.45,
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
                    lineHeight: 1.45,
                  }}
                >
                  {formError}
                </div>
              )}

              <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
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
                    autoComplete="name"
                    placeholder="Dr. / Rep Full Name"
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
                      boxSizing: "border-box",
                      minHeight: "44px",
                    }}
                  />
                </div>

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
                    Work email
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="email"
                    placeholder="rep@pharmaco.com"
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
                      boxSizing: "border-box",
                      minHeight: "44px",
                    }}
                  />
                </div>

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
                    Password (min. 8 characters)
                  </label>
                  <div style={{ position: "relative" }}>
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="new-password"
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
                        boxSizing: "border-box",
                        minHeight: "44px",
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      style={{
                        position: "absolute",
                        right: "8px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        color: "#94a3b8",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        cursor: "pointer",
                        padding: "0.3rem",
                        minWidth: "36px",
                        minHeight: "36px",
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

                <div>
                  <label
                    htmlFor="confirm_password"
                    style={{
                      display: "block",
                      fontSize: "0.8125rem",
                      fontWeight: 600,
                      color: "#334155",
                      marginBottom: "0.35rem",
                    }}
                  >
                    Confirm password
                  </label>
                  <div style={{ position: "relative" }}>
                    <input
                      id="confirm_password"
                      name="confirm_password"
                      type={showConfirmPassword ? "text" : "password"}
                      autoComplete="new-password"
                      placeholder="••••••••"
                      value={form.confirm_password}
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
                        boxSizing: "border-box",
                        minHeight: "44px",
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      style={{
                        position: "absolute",
                        right: "8px",
                        top: "50%",
                        transform: "translateY(-50%)",
                        background: "none",
                        border: "none",
                        color: "#94a3b8",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        cursor: "pointer",
                        padding: "0.3rem",
                        minWidth: "36px",
                        minHeight: "36px",
                      }}
                      aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                    >
                      {showConfirmPassword ? (
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
                    border: "none",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "0.5rem",
                    boxShadow: "0 2px 6px rgba(2, 132, 199, 0.25)",
                    cursor: loading ? "not-allowed" : "pointer",
                    minHeight: "44px",
                  }}
                >
                  {loading ? (
                    <span>Creating your account...</span>
                  ) : (
                    <span>Create account</span>
                  )}
                </button>
              </form>

              <div
                style={{
                  marginTop: "1.75rem",
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
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Register;
