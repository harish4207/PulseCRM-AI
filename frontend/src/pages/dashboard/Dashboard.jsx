import React, { useEffect, useState } from "react";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
  PeopleAltOutlined as DoctorIcon,
  EventNoteOutlined as InteractionIcon,
  EventAvailableOutlined as MeetingIcon,
  AssignmentTurnedInOutlined as FollowupIcon,
  AutoAwesome as SparkleIcon,
  Add as AddIcon,
  ArrowForward as ArrowForwardIcon,
  Schedule as ScheduleIcon,
  WarningAmber as WarningIcon,
  LocalHospitalOutlined as HospitalIcon,
  TaskAlt as TaskIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import StatCard from "../../components/dashboard/StatCard";
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

  const userName = user?.full_name || "Representative";

  // Calculate current greeting
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

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

  const todayStr = new Date().toISOString().slice(0, 10);

  // Filter follow-ups (interactions with follow_up_date)
  const followupsList = interactions.filter((item) => item.follow_up_date);

  const todayFollowups = followupsList.filter(
    (item) => item.follow_up_date && item.follow_up_date.slice(0, 10) === todayStr
  );

  const overdueFollowups = followupsList.filter(
    (item) => item.follow_up_date && item.follow_up_date.slice(0, 10) < todayStr
  );

  const upcomingFollowups = followupsList
    .filter((item) => item.follow_up_date && item.follow_up_date.slice(0, 10) >= todayStr)
    .sort((a, b) => new Date(a.follow_up_date) - new Date(b.follow_up_date))
    .slice(0, 4);

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

  const isFirstTime = hcps.length === 0 && interactions.length === 0 && !loading;

  return (
    <AppShell title="Dashboard">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", width: "100%" }}>
        {/* Top Welcome Header */}
        <div
          style={{
            padding: "1.25rem 1.5rem",
            borderRadius: "14px",
            backgroundColor: "#ffffff",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
            display: "flex",
            flexDirection: "column",
            gap: "0.85rem",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.75rem" }}>
            <div>
              <h1
                style={{
                  fontSize: "1.35rem",
                  fontWeight: 800,
                  color: "#0f172a",
                  letterSpacing: "-0.02em",
                  margin: 0,
                  lineHeight: 1.25,
                }}
              >
                {greeting}, {userName} 👋
              </h1>
              <p style={{ fontSize: "0.85rem", color: "#64748b", margin: "0.25rem 0 0 0" }}>
                Here's your territory at a glance.
              </p>
            </div>

            {/* Quick action buttons */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => navigate("/voice-copilot")}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.35rem",
                  padding: "0.5rem 0.85rem",
                  borderRadius: "8px",
                  backgroundColor: "#0284c7",
                  color: "#ffffff",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  border: "none",
                  cursor: "pointer",
                  boxShadow: "0 2px 4px rgba(2,132,199,0.2)",
                  minHeight: "44px",
                }}
              >
                <SparkleIcon style={{ fontSize: "0.95rem" }} />
                <span>Ask PulseCRM</span>
              </button>

              <button
                type="button"
                onClick={() => navigate("/ai-meeting")}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.35rem",
                  padding: "0.5rem 0.85rem",
                  borderRadius: "8px",
                  backgroundColor: "#ffffff",
                  color: "#334155",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  border: "1px solid #cbd5e1",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                <MeetingIcon style={{ fontSize: "0.95rem", color: "#0284c7" }} />
                <span>Schedule Meeting</span>
              </button>

              <button
                type="button"
                onClick={() => navigate("/interactions")}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.35rem",
                  padding: "0.5rem 0.85rem",
                  borderRadius: "8px",
                  backgroundColor: "#ffffff",
                  color: "#334155",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  border: "1px solid #cbd5e1",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                <InteractionIcon style={{ fontSize: "0.95rem", color: "#0d9488" }} />
                <span>Add Interaction</span>
              </button>

              <button
                type="button"
                onClick={() => navigate("/followups")}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.35rem",
                  padding: "0.5rem 0.85rem",
                  borderRadius: "8px",
                  backgroundColor: "#ffffff",
                  color: "#334155",
                  fontSize: "0.8rem",
                  fontWeight: 600,
                  border: "1px solid #cbd5e1",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                <FollowupIcon style={{ fontSize: "0.95rem", color: "#d97706" }} />
                <span>View Follow-ups</span>
              </button>
            </div>
          </div>
        </div>

        {/* First-time onboarding banner if territory is empty */}
        {isFirstTime && (
          <div
            style={{
              padding: "1.25rem 1.5rem",
              borderRadius: "14px",
              backgroundColor: "#f0f9ff",
              border: "1px solid #bae6fd",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <SparkleIcon style={{ color: "#0284c7", fontSize: "1.35rem" }} />
              <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0c4a6e", margin: 0 }}>
                Welcome to PulseCRM!
              </h2>
            </div>
            <p style={{ fontSize: "0.875rem", color: "#0369a1", margin: 0, lineHeight: 1.5 }}>
              Your AI assistant can help you manage doctors, interactions, meetings, and follow-ups. You can start by asking questions or telling Ask PulseCRM about someone you met.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "0.6rem", marginTop: "0.25rem" }}>
              <div style={{ backgroundColor: "#ffffff", padding: "0.75rem", borderRadius: "8px", border: "1px solid #e0f2fe" }}>
                <div style={{ fontWeight: 700, color: "#0f172a", fontSize: "0.8rem" }}>💬 Ask PulseCRM</div>
                <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "2px" }}>Talk naturally about your CRM</div>
              </div>
              <div style={{ backgroundColor: "#ffffff", padding: "0.75rem", borderRadius: "8px", border: "1px solid #e0f2fe" }}>
                <div style={{ fontWeight: 700, color: "#0f172a", fontSize: "0.8rem" }}>📅 Meeting Assistant</div>
                <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "2px" }}>Prepare and capture meetings</div>
              </div>
              <div style={{ backgroundColor: "#ffffff", padding: "0.75rem", borderRadius: "8px", border: "1px solid #e0f2fe" }}>
                <div style={{ fontWeight: 700, color: "#0f172a", fontSize: "0.8rem" }}>👨‍⚕️ Doctors</div>
                <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "2px" }}>Manage HCP relationships</div>
              </div>
              <div style={{ backgroundColor: "#ffffff", padding: "0.75rem", borderRadius: "8px", border: "1px solid #e0f2fe" }}>
                <div style={{ fontWeight: 700, color: "#0f172a", fontSize: "0.8rem" }}>📝 Interactions</div>
                <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: "2px" }}>Track what happened in the field</div>
              </div>
            </div>
          </div>
        )}

        {/* 4 Summary KPI Cards */}
        {loading ? (
          <LoadingState label="Loading territory intelligence..." />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <StatCard
              label="Today's Meetings"
              value={todayFollowups.length}
              accent="#0284c7"
              hint={todayFollowups.length > 0 ? `${todayFollowups.length} scheduled for today` : "Clear schedule today"}
              icon={MeetingIcon}
            />
            <StatCard
              label="Follow-ups"
              value={followupsList.length}
              accent="#d97706"
              hint={followupsList.length > 0 ? `${followupsList.length} active follow-ups` : "No follow-ups due"}
              icon={FollowupIcon}
            />
            <StatCard
              label="Doctors"
              value={hcps.length}
              accent="#0d9488"
              hint={hcps.length > 0 ? `${hcps.length} doctors in territory` : "No doctors added"}
              icon={DoctorIcon}
            />
            <StatCard
              label="Overdue"
              value={overdueFollowups.length}
              accent={overdueFollowups.length > 0 ? "#dc2626" : "#16a34a"}
              hint={overdueFollowups.length > 0 ? `${overdueFollowups.length} overdue follow-ups` : "All caught up"}
              icon={WarningIcon}
            />
          </div>
        )}

        {/* Next Recommended Action Card */}
        <div
          style={{
            padding: "1rem 1.25rem",
            borderRadius: "12px",
            backgroundColor: "#ffffff",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
            display: "flex",
            flexDirection: "column",
            gap: "0.5rem",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
              <SparkleIcon style={{ color: "#0284c7", fontSize: "1.1rem" }} />
              <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>
                Next Recommended Action
              </span>
            </div>
            <span
              style={{
                fontSize: "0.68rem",
                fontWeight: 700,
                padding: "0.15rem 0.5rem",
                borderRadius: "9999px",
                backgroundColor: overdueFollowups.length > 0 ? "#fee2e2" : "#e0f2fe",
                color: overdueFollowups.length > 0 ? "#b91c1c" : "#0369a1",
              }}
            >
              {overdueFollowups.length > 0 ? "🔴 Review Overdue" : "🟢 Territory Focus"}
            </span>
          </div>

          <div style={{ fontSize: "0.825rem", color: "#334155", lineHeight: 1.5 }}>
            {overdueFollowups.length > 0
              ? `You have ${overdueFollowups.length} overdue follow-up commitment(s). Review and follow up with your doctors to keep territory relationships active.`
              : todayFollowups.length > 0
              ? `You have ${todayFollowups.length} meeting(s) scheduled for today. Open Ask PulseCRM to prepare pre-meeting briefs.`
              : `Your territory schedule is up to date. You can review doctor interaction history, plan upcoming visits, or ask PulseCRM for talking points.`}
          </div>

          <div style={{ display: "flex", gap: "0.45rem", flexWrap: "wrap", marginTop: "0.25rem" }}>
            <button
              type="button"
              onClick={() => navigate("/voice-copilot")}
              style={{
                fontSize: "0.75rem",
                fontWeight: 600,
                padding: "0.35rem 0.65rem",
                borderRadius: "6px",
                backgroundColor: "#f0f9ff",
                color: "#0369a1",
                border: "1px solid #bae6fd",
                cursor: "pointer",
              }}
            >
              Plan Day in Ask PulseCRM →
            </button>
            <button
              type="button"
              onClick={() => navigate("/directory")}
              style={{
                fontSize: "0.75rem",
                fontWeight: 600,
                padding: "0.35rem 0.65rem",
                borderRadius: "6px",
                backgroundColor: "#f8fafc",
                color: "#475569",
                border: "1px solid #e2e8f0",
                cursor: "pointer",
              }}
            >
              Browse Doctors Directory →
            </button>
          </div>
        </div>

        {/* Two-Column Grid: Today's Schedule (Left) & Recent Interactions (Right) */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
          {/* Today's Schedule / Follow-ups */}
          <div
            style={{
              padding: "1.25rem",
              borderRadius: "12px",
              backgroundColor: "#ffffff",
              border: "1px solid #e2e8f0",
              boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a", margin: 0 }}>
                Today's Schedule & Commitments
              </h3>
              <button
                type="button"
                onClick={() => navigate("/followups")}
                style={{
                  background: "none",
                  border: "none",
                  color: "#0284c7",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                View all ({followupsList.length}) →
              </button>
            </div>

            {upcomingFollowups.length === 0 ? (
              <EmptyState
                title="No meetings scheduled for today"
                description="Use Ask PulseCRM to schedule visits and follow-ups with your doctors."
                iconType="medical"
              />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {upcomingFollowups.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "0.75rem",
                      borderRadius: "8px",
                      backgroundColor: "#f8fafc",
                      border: "1px solid #f1f5f9",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0f172a" }}>
                        {item.hcp?.doctor_name || `Doctor #${item.hcp_id}`}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                        {item.hcp?.hospital || "Hospital"} · {item.interaction_type || "Follow-up"}
                      </div>
                    </div>
                    <span
                      style={{
                        fontSize: "0.72rem",
                        fontWeight: 600,
                        padding: "0.2rem 0.5rem",
                        borderRadius: "6px",
                        backgroundColor: "#e0f2fe",
                        color: "#0369a1",
                      }}
                    >
                      {formatDate(item.follow_up_date)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Interactions */}
          <div
            style={{
              padding: "1.25rem",
              borderRadius: "12px",
              backgroundColor: "#ffffff",
              border: "1px solid #e2e8f0",
              boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
              display: "flex",
              flexDirection: "column",
              gap: "0.75rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a", margin: 0 }}>
                Recent Field Interactions
              </h3>
              <button
                type="button"
                onClick={() => navigate("/interactions")}
                style={{
                  background: "none",
                  border: "none",
                  color: "#0284c7",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                View all ({interactions.length}) →
              </button>
            </div>

            {recentInteractions.length === 0 ? (
              <EmptyState
                title="No interactions recorded yet"
                description="Log your first doctor visit or speak with Ask PulseCRM."
                iconType="medical"
              />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                {recentInteractions.map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: "0.75rem",
                      borderRadius: "8px",
                      backgroundColor: "#f8fafc",
                      border: "1px solid #f1f5f9",
                      display: "flex",
                      flexDirection: "column",
                      gap: "0.3rem",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0f172a" }}>
                        {item.hcp?.doctor_name || `Doctor #${item.hcp_id}`}
                      </span>
                      <span style={{ fontSize: "0.7rem", color: "#64748b" }}>
                        {formatDate(item.created_at)}
                      </span>
                    </div>
                    {item.products_discussed && (
                      <span style={{ fontSize: "0.7rem", color: "#0284c7", fontWeight: 600 }}>
                        Product: {item.products_discussed}
                      </span>
                    )}
                    <p style={{ fontSize: "0.775rem", color: "#475569", margin: 0, lineHeight: 1.45 }}>
                      {item.meeting_notes || item.ai_summary || "Routine relationship meeting."}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}

export default Dashboard;
