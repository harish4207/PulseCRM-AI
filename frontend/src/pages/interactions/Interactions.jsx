import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  EventNote as InteractionIcon,
  AutoAwesome as SparkleIcon,
  Schedule as ScheduleIcon,
  Search as SearchIcon,
  Medication as MedicineIcon,
  Close as CloseIcon,
  LocalHospital as HospitalIcon,
  Add as AddIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import EmptyState from "../../components/common/EmptyState";
import LoadingState from "../../components/common/LoadingState";
import interactionService from "../../services/interactionService";

export function Interactions() {
  const navigate = useNavigate();
  const [interactions, setInteractions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterMode, setFilterMode] = useState("all");
  const [selectedInteraction, setSelectedInteraction] = useState(null);

  const fetchInteractions = async () => {
    try {
      setLoading(true);
      const data = await interactionService.getAll();
      if (Array.isArray(data)) {
        setInteractions(data);
      }
    } catch (err) {
      console.error("Error fetching interactions:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInteractions();
  }, []);

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

  const filteredInteractions = interactions.filter((item) => {
    const docName = item.hcp?.doctor_name || "";
    const matchesSearch =
      docName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.products_discussed || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.meeting_notes || "").toLowerCase().includes(searchQuery.toLowerCase());

    if (filterMode === "followup") {
      return matchesSearch && Boolean(item.follow_up_date);
    }
    if (filterMode === "ai") {
      return matchesSearch && Boolean(item.ai_summary);
    }
    return matchesSearch;
  });

  return (
    <AppShell title="Interactions">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <PageHeader
          tag="FIELD ACTIVITY"
          title="Interactions"
          description="Review what happened during your doctor visits."
          actions={
            <Link
              to="/ai-meeting"
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
                textDecoration: "none",
                boxShadow: "0 2px 4px rgba(2,132,199,0.2)",
              }}
            >
              <AddIcon style={{ fontSize: "1.1rem" }} />
              <span>Log Interaction</span>
            </Link>
          }
        />

        {/* Filter bar */}
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
              placeholder="Search interactions by doctor, product, notes..."
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
            <span style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>
              Filter:
            </span>
            {[
              { label: `All (${interactions.length})`, value: "all" },
              { label: `With Follow-ups (${interactions.filter((i) => i.follow_up_date).length})`, value: "followup" },
              { label: `AI Structured (${interactions.filter((i) => i.ai_summary).length})`, value: "ai" },
            ].map((tab) => (
              <button
                key={tab.value}
                type="button"
                onClick={() => setFilterMode(tab.value)}
                style={{
                  padding: "0.25rem 0.65rem",
                  borderRadius: "9999px",
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  backgroundColor: filterMode === tab.value ? "#0284c7" : "#f1f5f9",
                  color: filterMode === tab.value ? "#ffffff" : "#475569",
                  border: filterMode === tab.value ? "1px solid #0284c7" : "1px solid #e2e8f0",
                  cursor: "pointer",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Timeline / Cards */}
        {loading ? (
          <LoadingState label="Loading interaction history..." />
        ) : filteredInteractions.length === 0 ? (
          <EmptyState
            iconType="medical"
            title={searchQuery || filterMode !== "all" ? "No matching interactions found" : "No interactions recorded yet"}
            description={
              searchQuery || filterMode !== "all"
                ? "Try adjusting your search query or filter."
                : "Log your first doctor visit or tell Ask PulseCRM about what happened."
            }
            action={
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", justifyContent: "center" }}>
                <Link
                  to="/ai-meeting"
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
                    textDecoration: "none",
                    minHeight: "44px",
                  }}
                >
                  <AddIcon style={{ fontSize: "1.1rem" }} />
                  <span>Log Interaction</span>
                </Link>
                <button
                  type="button"
                  onClick={() => navigate("/voice-copilot")}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.4rem",
                    padding: "0.55rem 1rem",
                    borderRadius: "8px",
                    backgroundColor: "#f0f9ff",
                    color: "#0369a1",
                    border: "1px solid #bae6fd",
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    minHeight: "44px",
                  }}
                >
                  <SparkleIcon style={{ fontSize: "1rem" }} />
                  <span>Ask PulseCRM</span>
                </button>
              </div>
            }
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {filteredInteractions.map((item) => (
              <div
                key={item.id}
                onClick={() => setSelectedInteraction(item)}
                style={{
                  padding: "1rem 1.25rem",
                  borderRadius: "12px",
                  backgroundColor: "#ffffff",
                  border: "1px solid #e2e8f0",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                  cursor: "pointer",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.45rem",
                  transition: "all 0.15s ease",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a" }}>
                      {item.hcp?.doctor_name || `Doctor #${item.hcp_id}`}
                    </span>
                    {item.hcp?.hospital && (
                      <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                        · {item.hcp.hospital} {item.hcp.city ? `(${item.hcp.city})` : ""}
                      </span>
                    )}
                  </div>
                  <span style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: 600 }}>
                    {formatDate(item.created_at)}
                  </span>
                </div>

                {item.products_discussed && (
                  <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                    <span style={{ fontSize: "0.68rem", fontWeight: 600, padding: "0.15rem 0.45rem", borderRadius: "4px", backgroundColor: "#e0f2fe", color: "#0284c7" }}>
                      {item.products_discussed}
                    </span>
                    {item.interaction_type && (
                      <span style={{ fontSize: "0.68rem", fontWeight: 600, padding: "0.15rem 0.45rem", borderRadius: "4px", backgroundColor: "#f1f5f9", color: "#475569" }}>
                        {item.interaction_type}
                      </span>
                    )}
                  </div>
                )}

                <p style={{ fontSize: "0.8rem", color: "#334155", margin: 0, lineHeight: 1.5, wordBreak: "break-word" }}>
                  {item.meeting_notes || item.ai_summary || "Routine relationship meeting."}
                </p>

                {item.follow_up_date && (
                  <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.72rem", color: "#d97706", fontWeight: 600, marginTop: "0.2rem" }}>
                    <ScheduleIcon style={{ fontSize: "0.85rem" }} />
                    <span>Follow-up: {formatDate(item.follow_up_date)}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Modal: Interaction Details */}
        {selectedInteraction && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Interaction Details"
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "rgba(15, 23, 42, 0.45)",
              backdropFilter: "blur(3px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 50,
              padding: "0.75rem",
            }}
            onClick={() => setSelectedInteraction(null)}
          >
            <div
              style={{
                width: "95vw",
                maxWidth: "520px",
                padding: "1.5rem",
                backgroundColor: "#ffffff",
                borderRadius: "14px",
                maxHeight: "90vh",
                overflowY: "auto",
                boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)",
                display: "flex",
                flexDirection: "column",
                gap: "1rem",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <h3 style={{ fontSize: "1.15rem", fontWeight: 700, color: "#0f172a", margin: 0 }}>
                    {selectedInteraction.hcp?.doctor_name || `Doctor #${selectedInteraction.hcp_id}`}
                  </h3>
                  <div style={{ fontSize: "0.8rem", color: "#64748b", marginTop: "2px" }}>
                    {selectedInteraction.hcp?.hospital} · {formatDate(selectedInteraction.created_at)}
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedInteraction(null)}
                  style={{ color: "#64748b", background: "none", border: "none", padding: "0.4rem", cursor: "pointer", minWidth: "36px", minHeight: "36px" }}
                  aria-label="Close dialog"
                >
                  <CloseIcon fontSize="small" />
                </button>
              </div>

              <div>
                <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>Notes</div>
                <p style={{ fontSize: "0.875rem", color: "#0f172a", lineHeight: 1.6, marginTop: "0.25rem" }}>
                  {selectedInteraction.meeting_notes || "No notes recorded."}
                </p>
              </div>

              {selectedInteraction.ai_summary && (
                <div style={{ padding: "0.75rem", borderRadius: "8px", backgroundColor: "#f0f9ff", border: "1px solid #bae6fd" }}>
                  <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#0369a1", display: "flex", alignItems: "center", gap: "0.3rem" }}>
                    <SparkleIcon style={{ fontSize: "0.9rem" }} /> AI Summary
                  </div>
                  <p style={{ fontSize: "0.8rem", color: "#0c4a6e", marginTop: "0.25rem", margin: 0, lineHeight: 1.5 }}>
                    {selectedInteraction.ai_summary}
                  </p>
                </div>
              )}

              {selectedInteraction.follow_up_date && (
                <div style={{ padding: "0.75rem", borderRadius: "8px", backgroundColor: "#fffbeb", border: "1px solid #fde68a" }}>
                  <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#92400e" }}>Follow-up Commitment</div>
                  <div style={{ fontSize: "0.8rem", color: "#78350f", marginTop: "0.25rem" }}>
                    Scheduled for: <strong>{formatDate(selectedInteraction.follow_up_date)}</strong>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default Interactions;
