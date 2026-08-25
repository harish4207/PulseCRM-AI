import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  EventNote as InteractionIcon,
  AutoAwesome as AiIcon,
  Schedule as ScheduleIcon,
  Search as SearchIcon,
  Medication as MedicineIcon,
  Close as CloseIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import EmptyState from "../../components/common/EmptyState";
import LoadingState from "../../components/common/LoadingState";
import interactionService from "../../services/interactionService";

export function Interactions() {
  const [interactions, setInteractions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterMode, setFilterMode] = useState("all"); // 'all' | 'followup' | 'ai'
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
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date(dateStr));
    } catch {
      return dateStr;
    }
  };

  const filteredInteractions = interactions.filter((item) => {
    const matchesSearch =
      (item.products_discussed || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.meeting_notes || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      String(item.hcp_id).includes(searchQuery);

    if (filterMode === "followup") {
      return matchesSearch && Boolean(item.follow_up_date);
    }
    if (filterMode === "ai") {
      return matchesSearch && Boolean(item.ai_summary);
    }
    return matchesSearch;
  });

  return (
    <AppShell title="Interactions History">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <PageHeader
          tag="Field Intelligence Log"
          title="Interaction History"
          description="Detailed timeline of all healthcare professional meetings, product presentations, and commitments."
          actions={
            <Link
              to="/ai-meeting"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.4rem",
                padding: "0.65rem 1.15rem",
                borderRadius: "8px",
                backgroundColor: "#0284c7",
                color: "#ffffff",
                fontSize: "0.875rem",
                fontWeight: 600,
                textDecoration: "none",
                boxShadow: "0 2px 6px rgba(2, 132, 199, 0.2)",
              }}
            >
              <AiIcon style={{ fontSize: "1.1rem" }} />
              <span>Log Meeting with AI</span>
            </Link>
          }
        />

        {/* Filter bar */}
        <div
          className="pulse-card"
          style={{
            padding: "1rem 1.25rem",
            display: "flex",
            flexDirection: "column",
            gap: "0.85rem",
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
              placeholder="Search by products, keywords, or HCP ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: "100%",
                padding: "0.6rem 0.85rem 0.6rem 2.4rem",
                borderRadius: "10px",
                border: "1px solid #cbd5e1",
                backgroundColor: "#f8fafc",
                fontSize: "0.875rem",
                color: "#0f172a",
              }}
            />
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>
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
                  padding: "0.35rem 0.75rem",
                  borderRadius: "9999px",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  backgroundColor: filterMode === tab.value ? "#0284c7" : "#f1f5f9",
                  color: filterMode === tab.value ? "#ffffff" : "#475569",
                  border: filterMode === tab.value ? "1px solid #0284c7" : "1px solid #e2e8f0",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* List of Interactions */}
        {loading ? (
          <LoadingState label="Loading interaction timeline..." />
        ) : filteredInteractions.length === 0 ? (
          <EmptyState
            title="No interaction records found"
            description="Use the AI Meeting Logger to convert your notes into structured CRM records."
            action={
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
                }}
              >
                <AiIcon style={{ fontSize: "1.1rem" }} />
                <span>Log Meeting with AI</span>
              </Link>
            }
          />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {filteredInteractions.map((item) => (
              <div
                key={item.id}
                className="pulse-card pulse-card-interactive"
                style={{
                  padding: "1rem 1.25rem",
                  display: "flex",
                  flexDirection: "column",
                  gap: "0.75rem",
                  cursor: "pointer",
                }}
                onClick={() => setSelectedInteraction(item)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.65rem", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a" }}>
                      Healthcare Professional #{item.hcp_id}
                    </span>
                    {item.ai_summary && (
                      <StatusBadge variant="teal" size="sm">
                        AI Logged
                      </StatusBadge>
                    )}
                  </div>

                  <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                    Recorded on {formatDate(item.created_at)}
                  </span>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                  <MedicineIcon style={{ fontSize: "1.05rem", color: "#2563eb" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#475569" }}>
                    Products:
                  </span>
                  <StatusBadge variant="product" size="sm" withDot={false}>
                    {item.products_discussed || "General Detailing"}
                  </StatusBadge>
                </div>

                <p style={{ fontSize: "0.875rem", color: "#334155", lineHeight: 1.5, margin: 0, wordBreak: "break-word" }}>
                  {item.meeting_notes}
                </p>

                {item.follow_up_date && (
                  <div
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.4rem",
                      padding: "0.4rem 0.75rem",
                      borderRadius: "8px",
                      backgroundColor: "#fffbeb",
                      border: "1px solid #fde68a",
                      color: "#92400e",
                      fontSize: "0.75rem",
                      fontWeight: 600,
                      alignSelf: "flex-start",
                    }}
                  >
                    <ScheduleIcon style={{ fontSize: "0.95rem" }} />
                    <span>Follow-up: {formatDate(item.follow_up_date)}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Modal / Detail Drawer for selected interaction */}
        {selectedInteraction && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Interaction details"
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
              overflowY: "auto",
            }}
            onClick={() => setSelectedInteraction(null)}
          >
            <div
              className="pulse-card"
              style={{
                width: "95vw",
                maxWidth: "600px",
                padding: "1.25rem sm:padding-1.75rem",
                backgroundColor: "#ffffff",
                maxHeight: "90vh",
                overflowY: "auto",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
                <div>
                  <div style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", color: "#0284c7" }}>
                    Interaction #{selectedInteraction.id} Details
                  </div>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0f172a" }}>
                    Doctor #{selectedInteraction.hcp_id}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setSelectedInteraction(null)}
                  style={{ color: "#64748b", padding: "0.4rem", minWidth: "36px", minHeight: "36px" }}
                  aria-label="Close dialog"
                >
                  <CloseIcon fontSize="small" />
                </button>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <div>
                  <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: "0.25rem" }}>
                    Products Discussed
                  </div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#0f172a" }}>
                    {selectedInteraction.products_discussed || "General Detailing"}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#64748b", textTransform: "uppercase", marginBottom: "0.25rem" }}>
                    Field Notes & Discussion
                  </div>
                  <div
                    style={{
                      padding: "0.85rem",
                      borderRadius: "10px",
                      backgroundColor: "#f8fafc",
                      border: "1px solid #e2e8f0",
                      fontSize: "0.875rem",
                      color: "#334155",
                      lineHeight: 1.6,
                      wordBreak: "break-word",
                    }}
                  >
                    {selectedInteraction.meeting_notes}
                  </div>
                </div>

                {selectedInteraction.ai_summary && (
                  <div>
                    <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#0d9488", textTransform: "uppercase", marginBottom: "0.25rem" }}>
                      AI Intelligence Summary
                    </div>
                    <div
                      style={{
                        padding: "0.85rem",
                        borderRadius: "10px",
                        backgroundColor: "#f0fdf4",
                        border: "1px solid #bbf7d0",
                        fontSize: "0.875rem",
                        color: "#166534",
                        lineHeight: 1.6,
                        wordBreak: "break-word",
                      }}
                    >
                      {selectedInteraction.ai_summary}
                    </div>
                  </div>
                )}

                {selectedInteraction.follow_up_date && (
                  <div>
                    <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#d97706", textTransform: "uppercase", marginBottom: "0.25rem" }}>
                      Follow-up Commitment
                    </div>
                    <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#92400e" }}>
                      {formatDate(selectedInteraction.follow_up_date)}
                    </div>
                  </div>
                )}
              </div>

              <div style={{ marginTop: "1.5rem", display: "flex", justifyContent: "flex-end" }}>
                <button
                  type="button"
                  onClick={() => setSelectedInteraction(null)}
                  style={{
                    padding: "0.55rem 1.25rem",
                    minHeight: "40px",
                    borderRadius: "8px",
                    backgroundColor: "#f1f5f9",
                    color: "#334155",
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                  }}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default Interactions;
