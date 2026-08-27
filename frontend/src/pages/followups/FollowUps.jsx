import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AssignmentTurnedIn as FollowupIcon,
  CheckCircle as CheckIcon,
  Schedule as ScheduleIcon,
  WarningAmber as WarningIcon,
  Search as SearchIcon,
  AutoAwesome as SparkleIcon,
  LocalHospital as HospitalIcon,
  Add as AddIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import PageHeader from "../../components/common/PageHeader";
import EmptyState from "../../components/common/EmptyState";
import LoadingState from "../../components/common/LoadingState";
import interactionService from "../../services/interactionService";

export function FollowUps() {
  const navigate = useNavigate();
  const [interactions, setInteractions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("all"); // 'all' | 'today' | 'upcoming' | 'overdue' | 'completed'
  const [searchQuery, setSearchQuery] = useState("");
  const [completedIds, setCompletedIds] = useState(new Set());

  const fetchFollowups = async () => {
    try {
      setLoading(true);
      const data = await interactionService.getAll();
      if (Array.isArray(data)) {
        setInteractions(data.filter((item) => item.follow_up_date));
      }
    } catch (err) {
      console.error("Error fetching follow-ups:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFollowups();
  }, []);

  const todayStr = new Date().toISOString().slice(0, 10);

  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    try {
      return new Intl.DateTimeFormat("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
        year: "numeric",
      }).format(new Date(dateStr));
    } catch {
      return dateStr;
    }
  };

  const getStatus = (item) => {
    if (completedIds.has(item.id)) return "completed";
    const dStr = item.follow_up_date ? item.follow_up_date.slice(0, 10) : "";
    if (dStr === todayStr) return "today";
    if (dStr < todayStr) return "overdue";
    return "upcoming";
  };

  const handleToggleComplete = (id) => {
    setCompletedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const filteredItems = interactions.filter((item) => {
    const docName = item.hcp?.doctor_name || "";
    const matchesSearch =
      docName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.meeting_notes || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.products_discussed || "").toLowerCase().includes(searchQuery.toLowerCase());

    const status = getStatus(item);

    if (activeTab === "all") return matchesSearch;
    if (activeTab === "today") return matchesSearch && status === "today";
    if (activeTab === "upcoming") return matchesSearch && status === "upcoming";
    if (activeTab === "overdue") return matchesSearch && status === "overdue";
    if (activeTab === "completed") return matchesSearch && status === "completed";
    return matchesSearch;
  });

  const todayCount = interactions.filter((i) => getStatus(i) === "today").length;
  const overdueCount = interactions.filter((i) => getStatus(i) === "overdue").length;
  const upcomingCount = interactions.filter((i) => getStatus(i) === "upcoming").length;
  const completedCount = completedIds.size;

  return (
    <AppShell title="Follow-ups">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <PageHeader
          tag="NEXT ACTIONS"
          title="Follow-ups"
          description="Stay on top of your next actions."
          actions={
            <button
              type="button"
              onClick={() => navigate("/ai-meeting")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.4rem",
                padding: "0.55rem 1rem",
                minHeight: "44px",
                fontSize: "0.8125rem",
                borderRadius: "8px",
                backgroundColor: "#0284c7",
                color: "#ffffff",
                fontWeight: 600,
                border: "none",
                cursor: "pointer",
                boxShadow: "0 2px 4px rgba(2,132,199,0.2)",
              }}
            >
              <AddIcon style={{ fontSize: "1.1rem" }} />
              <span>Schedule Follow-up</span>
            </button>
          }
        />

        {/* Tab Filter Bar */}
        <div
          style={{
            padding: "1rem 1.25rem",
            backgroundColor: "#ffffff",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
          }}
        >
          <div style={{ position: "relative", width: "100%" }}>
            <SearchIcon
              style={{
                position: "absolute",
                left: "12px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "#94a3b8",
                fontSize: "1.2rem",
              }}
            />
            <input
              type="text"
              placeholder="Search follow-ups by doctor or notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "0.6rem 0.85rem 0.6rem 2.4rem",
                borderRadius: "8px",
                border: "1px solid #cbd5e1",
                backgroundColor: "#f8fafc",
                fontSize: "0.875rem",
                color: "#0f172a",
                boxSizing: "border-box",
                minHeight: "44px",
              }}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexWrap: "wrap" }}>
            {[
              { label: `All (${interactions.length})`, value: "all" },
              { label: `Today (${todayCount})`, value: "today", badgeColor: "#0284c7" },
              { label: `Overdue (${overdueCount})`, value: "overdue", badgeColor: "#dc2626" },
              { label: `Upcoming (${upcomingCount})`, value: "upcoming" },
              { label: `Completed (${completedCount})`, value: "completed" },
            ].map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => setActiveTab(tab.value)}
                style={{
                  padding: "0.3rem 0.75rem",
                  borderRadius: "9999px",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  backgroundColor: activeTab === tab.value ? "#0284c7" : "#f1f5f9",
                  color: activeTab === tab.value ? "#ffffff" : "#475569",
                  border: activeTab === tab.value ? "1px solid #0284c7" : "1px solid #e2e8f0",
                  cursor: "pointer",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* List of Follow-up Cards */}
        {loading ? (
          <LoadingState label="Loading follow-ups..." />
        ) : filteredItems.length === 0 ? (
          <EmptyState
            iconType="medical"
            title="You're all caught up"
            description="No pending follow-ups found for this view. Use Ask PulseCRM to schedule new commitments."
            action={
              <button
                type="button"
                onClick={() => navigate("/voice-copilot")}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  padding: "0.55rem 1rem",
                  borderRadius: "8px",
                  backgroundColor: "#0284c7",
                  color: "#ffffff",
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  border: "none",
                  cursor: "pointer",
                  minHeight: "44px",
                }}
              >
                <SparkleIcon style={{ fontSize: "1rem" }} />
                <span>Ask PulseCRM</span>
              </button>
            }
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {filteredItems.map((item) => {
              const status = getStatus(item);
              const isDone = status === "completed";

              return (
                <div
                  key={item.id}
                  style={{
                    padding: "1rem 1.25rem",
                    borderRadius: "12px",
                    backgroundColor: isDone ? "#f8fafc" : "#ffffff",
                    border: isDone
                      ? "1px solid #e2e8f0"
                      : status === "overdue"
                      ? "1px solid #fecaca"
                      : status === "today"
                      ? "1px solid #bae6fd"
                      : "1px solid #e2e8f0",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.45rem",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <button
                        type="button"
                        onClick={() => handleToggleComplete(item.id)}
                        style={{
                          width: "24px",
                          height: "24px",
                          borderRadius: "50%",
                          border: isDone ? "2px solid #16a34a" : "2px solid #cbd5e1",
                          backgroundColor: isDone ? "#16a34a" : "#ffffff",
                          color: "#ffffff",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          cursor: "pointer",
                          padding: 0,
                          flexShrink: 0,
                        }}
                        aria-label={isDone ? "Mark incomplete" : "Mark complete"}
                      >
                        {isDone && <CheckIcon style={{ fontSize: "1rem" }} />}
                      </button>

                      <span
                        style={{
                          fontSize: "0.95rem",
                          fontWeight: 700,
                          color: isDone ? "#64748b" : "#0f172a",
                          textDecoration: isDone ? "line-through" : "none",
                        }}
                      >
                        {item.hcp?.doctor_name || `Doctor #${item.hcp_id}`}
                      </span>

                      {item.hcp?.hospital && (
                        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                          · {item.hcp.hospital}
                        </span>
                      )}
                    </div>

                    <span
                      style={{
                        fontSize: "0.7rem",
                        fontWeight: 700,
                        padding: "0.15rem 0.5rem",
                        borderRadius: "9999px",
                        backgroundColor: isDone
                          ? "#f1f5f9"
                          : status === "overdue"
                          ? "#fee2e2"
                          : status === "today"
                          ? "#e0f2fe"
                          : "#f8fafc",
                        color: isDone
                          ? "#64748b"
                          : status === "overdue"
                          ? "#b91c1c"
                          : status === "today"
                          ? "#0369a1"
                          : "#475569",
                        border: `1px solid ${
                          isDone
                            ? "#e2e8f0"
                            : status === "overdue"
                            ? "#fca5a5"
                            : status === "today"
                            ? "#bae6fd"
                            : "#e2e8f0"
                        }`,
                      }}
                    >
                      {isDone ? "✓ Completed" : status === "overdue" ? "🔴 Overdue" : status === "today" ? "🟡 Due Today" : "Upcoming"}
                    </span>
                  </div>

                  <p
                    style={{
                      fontSize: "0.8rem",
                      color: isDone ? "#94a3b8" : "#334155",
                      margin: "0.2rem 0",
                      lineHeight: 1.45,
                    }}
                  >
                    {item.meeting_notes || item.ai_summary || "Follow-up discussion commitment."}
                  </p>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.25rem", borderTop: "1px solid #f1f5f9", paddingTop: "0.5rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.75rem", color: "#64748b" }}>
                      <ScheduleIcon style={{ fontSize: "0.85rem" }} />
                      <span>Due: <strong>{formatDate(item.follow_up_date)}</strong></span>
                    </div>

                    <div style={{ display: "flex", gap: "0.4rem" }}>
                      <button
                        type="button"
                        onClick={() => navigate("/voice-copilot")}
                        style={{
                          fontSize: "0.72rem",
                          fontWeight: 600,
                          padding: "0.3rem 0.6rem",
                          borderRadius: "6px",
                          backgroundColor: "#f0f9ff",
                          color: "#0369a1",
                          border: "1px solid #bae6fd",
                          cursor: "pointer",
                          minHeight: "36px",
                        }}
                      >
                        Ask PulseCRM
                      </button>
                      <button
                        type="button"
                        onClick={() => handleToggleComplete(item.id)}
                        style={{
                          fontSize: "0.72rem",
                          fontWeight: 600,
                          padding: "0.3rem 0.6rem",
                          borderRadius: "6px",
                          backgroundColor: isDone ? "#ffffff" : "#dcfce7",
                          color: isDone ? "#64748b" : "#166534",
                          border: isDone ? "1px solid #cbd5e1" : "1px solid #bbf7d0",
                          cursor: "pointer",
                          minHeight: "36px",
                        }}
                      >
                        {isDone ? "Reopen" : "✓ Mark Done"}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default FollowUps;
