import React, { useEffect, useState } from "react";
import { useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import {
  PeopleAltOutlined as HcpIcon,
  EventNoteOutlined as InteractionIcon,
  EventAvailableOutlined as FollowupIcon,
  AutoAwesomeOutlined as AiIcon,
  Add as AddIcon,
  ArrowForward as ArrowForwardIcon,
  LocalHospitalOutlined as HospitalIcon,
  Schedule as ScheduleIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import WelcomeCard from "../../components/dashboard/WelcomeCard";
import StatCard from "../../components/dashboard/StatCard";
import StatusBadge from "../../components/common/StatusBadge";
import EmptyState from "../../components/common/EmptyState";
import LoadingState from "../../components/common/LoadingState";
import doctorService from "../../services/doctorService";
import interactionService from "../../services/interactionService";

export function Dashboard() {
  const navigate = useNavigate();
  const { user } = useSelector((state) => state.auth ?? {});

  const [hcps, setHcps] = useState([]);
  const [interactions, setInteractions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadDashboardData() {
      try {
        setLoading(true);
        const [hcpsData, interactionsData] = await Promise.allSettled([
          doctorService.getAll(),
          interactionService.getAll(),
        ]);

        if (isMounted) {
          if (hcpsData.status === "fulfilled" && Array.isArray(hcpsData.value)) {
            setHcps(hcpsData.value);
          }
          if (interactionsData.status === "fulfilled" && Array.isArray(interactionsData.value)) {
            setInteractions(interactionsData.value);
          }
        }
      } catch (err) {
        console.error("Error loading dashboard data:", err);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    loadDashboardData();

    return () => {
      isMounted = false;
    };
  }, []);

  // Filter follow-ups (interactions with follow_up_date)
  const upcomingFollowups = interactions
    .filter((item) => item.follow_up_date)
    .sort((a, b) => new Date(a.follow_up_date) - new Date(b.follow_up_date))
    .slice(0, 4);

  // Recent 5 interactions
  const recentInteractions = [...interactions]
    .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
    .slice(0, 5);

  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    try {
      return new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      }).format(new Date(dateStr));
    } catch {
      return dateStr;
    }
  };

  return (
    <AppShell title="Dashboard">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        {/* Welcome Header */}
        <WelcomeCard name={user?.full_name} />

        {/* 4 Summary KPI Cards */}
        {loading ? (
          <LoadingState label="Fetching territory intelligence..." />
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
              gap: "1rem",
            }}
          >
            <StatCard
              label="Total HCPs"
              value={hcps.length > 0 ? hcps.length : "0"}
              accent="#0284c7"
              hint={hcps.length > 0 ? `${hcps.length} active in territory` : "No HCPs recorded yet"}
              icon={HcpIcon}
            />
            <StatCard
              label="Total Interactions"
              value={interactions.length > 0 ? interactions.length : "0"}
              accent="#0d9488"
              hint={interactions.length > 0 ? "Logged field interactions" : "No interactions recorded"}
              icon={InteractionIcon}
            />
            <StatCard
              label="Upcoming Follow-ups"
              value={upcomingFollowups.length > 0 ? upcomingFollowups.length : "0"}
              accent="#d97706"
              hint={upcomingFollowups.length > 0 ? "Scheduled commitments" : "No follow-ups due"}
              icon={FollowupIcon}
            />
            <StatCard
              label="AI Logs Processed"
              value={interactions.filter((i) => i.ai_summary).length}
              accent="#059669"
              hint="Automated via AI workflow"
              icon={AiIcon}
            />
          </div>
        )}

        {/* Main Content Grid: Recent Interactions (65%) & Follow-ups / Quick Actions (35%) */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
            gap: "1.5rem",
            alignItems: "start",
          }}
        >
          {/* Left Column: Recent Interactions */}
          <div className="pulse-card" style={{ padding: "1.5rem", gridColumn: "span 2" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: "1.25rem",
              }}
            >
              <div>
                <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a" }}>
                  Recent Interactions
                </h3>
                <p style={{ fontSize: "0.8125rem", color: "#64748b", marginTop: "2px" }}>
                  Latest doctor visits and detailing notes
                </p>
              </div>

              <Link
                to="/interactions"
                style={{
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  color: "#0284c7",
                  textDecoration: "none",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.25rem",
                }}
              >
                <span>View all</span>
                <ArrowForwardIcon style={{ fontSize: "0.95rem" }} />
              </Link>
            </div>

            {recentInteractions.length === 0 ? (
              <EmptyState
                title="No recent interactions"
                description="Use the AI Meeting Logger to convert your doctor discussions into structured CRM logs."
                action={
                  <Link
                    to="/ai-meeting"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.4rem",
                      backgroundColor: "#0284c7",
                      color: "#ffffff",
                      padding: "0.55rem 1rem",
                      borderRadius: "8px",
                      fontSize: "0.8125rem",
                      fontWeight: 600,
                      textDecoration: "none",
                    }}
                  >
                    <AiIcon style={{ fontSize: "1.1rem" }} />
                    <span>Log Meeting with AI</span>
                  </Link>
                }
              />
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #e2e8f0" }}>
                      <th style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>
                        HCP ID
                      </th>
                      <th style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>
                        Products
                      </th>
                      <th style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>
                        Summary
                      </th>
                      <th style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>
                        Date
                      </th>
                      <th style={{ padding: "0.6rem 0.75rem", fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>
                        Follow-up
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {recentInteractions.map((item) => (
                      <tr
                        key={item.id}
                        style={{ borderBottom: "1px solid #f1f5f9", transition: "background-color 0.15s ease" }}
                        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#f8fafc")}
                        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                      >
                        <td style={{ padding: "0.85rem 0.75rem", fontSize: "0.875rem", fontWeight: 600, color: "#0f172a" }}>
                          HCP #{item.hcp_id}
                        </td>
                        <td style={{ padding: "0.85rem 0.75rem" }}>
                          <StatusBadge variant="product" size="sm" withDot={false}>
                            {item.products_discussed || "General"}
                          </StatusBadge>
                        </td>
                        <td style={{ padding: "0.85rem 0.75rem", fontSize: "0.8125rem", color: "#475569", maxWidth: "260px" }}>
                          <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                            {item.meeting_notes}
                          </div>
                        </td>
                        <td style={{ padding: "0.85rem 0.75rem", fontSize: "0.8125rem", color: "#64748b" }}>
                          {formatDate(item.created_at)}
                        </td>
                        <td style={{ padding: "0.85rem 0.75rem" }}>
                          {item.follow_up_date ? (
                            <StatusBadge variant="scheduled" size="sm">
                              {formatDate(item.follow_up_date)}
                            </StatusBadge>
                          ) : (
                            <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>None</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Right Column: Upcoming Follow-ups & Quick Actions */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {/* Quick Actions Panel */}
            <div className="pulse-card" style={{ padding: "1.25rem" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a", marginBottom: "0.85rem" }}>
                Quick Actions
              </h3>

              <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                <button
                  type="button"
                  onClick={() => navigate("/ai-meeting")}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    padding: "0.75rem 1rem",
                    borderRadius: "10px",
                    backgroundColor: "#f0f9ff",
                    border: "1px solid #bae6fd",
                    color: "#0284c7",
                    fontSize: "0.875rem",
                    fontWeight: 600,
                    textAlign: "left",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#e0f2fe")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#f0f9ff")}
                >
                  <AiIcon style={{ fontSize: "1.2rem" }} />
                  <span>Log Meeting with AI</span>
                </button>

                <button
                  type="button"
                  onClick={() => navigate("/hcps")}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    padding: "0.75rem 1rem",
                    borderRadius: "10px",
                    backgroundColor: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    color: "#334155",
                    fontSize: "0.875rem",
                    fontWeight: 600,
                    textAlign: "left",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#f1f5f9")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#f8fafc")}
                >
                  <HcpIcon style={{ fontSize: "1.2rem", color: "#64748b" }} />
                  <span>View HCP Directory</span>
                </button>

                <button
                  type="button"
                  onClick={() => navigate("/interactions")}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    padding: "0.75rem 1rem",
                    borderRadius: "10px",
                    backgroundColor: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    color: "#334155",
                    fontSize: "0.875rem",
                    fontWeight: 600,
                    textAlign: "left",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#f1f5f9")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#f8fafc")}
                >
                  <InteractionIcon style={{ fontSize: "1.2rem", color: "#64748b" }} />
                  <span>View Interactions</span>
                </button>
              </div>
            </div>

            {/* Upcoming Follow-ups Panel */}
            <div className="pulse-card" style={{ padding: "1.25rem" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.85rem" }}>
                <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a" }}>
                  Upcoming Follow-ups
                </h3>
                <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#d97706" }}>
                  {upcomingFollowups.length} scheduled
                </span>
              </div>

              {upcomingFollowups.length === 0 ? (
                <EmptyState
                  title="No scheduled follow-ups"
                  description="When doctor commitments with future dates are logged, they will appear here."
                />
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                  {upcomingFollowups.map((item) => (
                    <div
                      key={item.id}
                      style={{
                        padding: "0.75rem",
                        borderRadius: "10px",
                        backgroundColor: "#fffbeb",
                        border: "1px solid #fde68a",
                        display: "flex",
                        flexDirection: "column",
                        gap: "0.35rem",
                      }}
                    >
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#92400e" }}>
                          HCP #{item.hcp_id}
                        </span>
                        <span style={{ fontSize: "0.72rem", color: "#b45309", display: "flex", alignItems: "center", gap: "0.2rem" }}>
                          <ScheduleIcon style={{ fontSize: "0.85rem" }} />
                          {formatDate(item.follow_up_date)}
                        </span>
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#78350f" }}>
                        Product: <strong>{item.products_discussed || "Clinical Discussion"}</strong>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default Dashboard;
