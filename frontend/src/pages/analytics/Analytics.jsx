import React, { useEffect, useState } from "react";
import {
  TrendingUp as TrendingIcon,
  PeopleAlt as HcpIcon,
  EventAvailable as ComplianceIcon,
  AutoAwesome as AiIcon,
  LocalHospital as HospitalIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import PageHeader from "../../components/common/PageHeader";
import StatCard from "../../components/dashboard/StatCard";
import LoadingState from "../../components/common/LoadingState";
import doctorService from "../../services/doctorService";
import interactionService from "../../services/interactionService";

export function Analytics() {
  const [hcps, setHcps] = useState([]);
  const [interactions, setInteractions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [hcpRes, intRes] = await Promise.allSettled([
          doctorService.getAll(),
          interactionService.getAll(),
        ]);
        if (hcpRes.status === "fulfilled" && Array.isArray(hcpRes.value)) {
          setHcps(hcpRes.value);
        }
        if (intRes.status === "fulfilled" && Array.isArray(intRes.value)) {
          setInteractions(intRes.value);
        }
      } catch (err) {
        console.error("Error fetching analytics data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  // Compute metrics
  const totalHcps = hcps.length;
  const totalInteractions = interactions.length;
  const withFollowups = interactions.filter((i) => i.follow_up_date).length;
  const aiLogged = interactions.filter((i) => i.ai_summary).length;
  const aiAdoptionRate = totalInteractions > 0 ? Math.round((aiLogged / totalInteractions) * 100) : 0;
  const followUpRate = totalInteractions > 0 ? Math.round((withFollowups / totalInteractions) * 100) : 0;

  // Specialty Breakdown
  const specialtyCounts = hcps.reduce((acc, hcp) => {
    const spec = hcp.specialization || "Other";
    acc[spec] = (acc[spec] || 0) + 1;
    return acc;
  }, {});

  const specialtyEntries = Object.entries(specialtyCounts);

  return (
    <AppShell title="Relationship Analytics">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <PageHeader
          tag="Intelligence Insights"
          title="Territory Relationship Analytics"
          description="High-level visibility into doctor relationship coverage, meeting volume, and follow-up commitments."
        />

        {loading ? (
          <LoadingState label="Calculating territory analytics..." />
        ) : (
          <>
            {/* KPI Cards */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
                gap: "1rem",
              }}
            >
              <StatCard
                label="Physician Reach"
                value={totalHcps}
                accent="#0284c7"
                hint="Total doctors in CRM"
                icon={HcpIcon}
              />
              <StatCard
                label="Total Field Logs"
                value={totalInteractions}
                accent="#0d9488"
                hint="Meetings recorded"
                icon={TrendingIcon}
              />
              <StatCard
                label="Follow-up Rate"
                value={`${followUpRate}%`}
                accent="#d97706"
                hint={`${withFollowups} follow-ups scheduled`}
                icon={ComplianceIcon}
              />
              <StatCard
                label="AI Automation"
                value={`${aiAdoptionRate}%`}
                accent="#059669"
                hint={`${aiLogged} AI-extracted logs`}
                icon={AiIcon}
              />
            </div>

            {/* Specialty Coverage Breakdown */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
                gap: "1.5rem",
              }}
            >
              {/* Specialty Distribution */}
              <div className="pulse-card" style={{ padding: "1.5rem" }}>
                <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a", marginBottom: "0.25rem" }}>
                  Specialization Coverage
                </h3>
                <p style={{ fontSize: "0.8125rem", color: "#64748b", marginBottom: "1.25rem" }}>
                  Distribution of HCPs across clinical therapy areas
                </p>

                {specialtyEntries.length === 0 ? (
                  <div style={{ padding: "2rem 0", textAlign: "center", color: "#94a3b8", fontSize: "0.875rem" }}>
                    No HCP data recorded yet.
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                    {specialtyEntries.map(([spec, count]) => {
                      const percentage = totalHcps > 0 ? Math.round((count / totalHcps) * 100) : 0;
                      return (
                        <div key={spec} style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8125rem" }}>
                            <span style={{ fontWeight: 600, color: "#334155" }}>{spec}</span>
                            <span style={{ color: "#64748b" }}>
                              {count} HCPs ({percentage}%)
                            </span>
                          </div>
                          <div
                            style={{
                              width: "100%",
                              height: "8px",
                              borderRadius: "9999px",
                              backgroundColor: "#f1f5f9",
                              overflow: "hidden",
                            }}
                          >
                            <div
                              style={{
                                width: `${percentage}%`,
                                height: "100%",
                                backgroundColor: "#0284c7",
                                borderRadius: "9999px",
                              }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Relationship Health & Efficiency */}
              <div className="pulse-card" style={{ padding: "1.5rem" }}>
                <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a", marginBottom: "0.25rem" }}>
                  Field Productivity & AI Impact
                </h3>
                <p style={{ fontSize: "0.8125rem", color: "#64748b", marginBottom: "1.25rem" }}>
                  Automation efficiency gained using PulseCRM AI
                </p>

                <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                  <div
                    style={{
                      padding: "1rem",
                      borderRadius: "12px",
                      backgroundColor: "#f0fdf4",
                      border: "1px solid #bbf7d0",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.75rem",
                    }}
                  >
                    <AiIcon style={{ color: "#059669", fontSize: "1.5rem" }} />
                    <div>
                      <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#166534" }}>
                        ~75% Time Saved on Call Reports
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#15803d", marginTop: "2px" }}>
                        Meeting notes automatically parsed into ISO follow-up dates and products.
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      padding: "1rem",
                      borderRadius: "12px",
                      backgroundColor: "#f0f9ff",
                      border: "1px solid #bae6fd",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.75rem",
                    }}
                  >
                    <HospitalIcon style={{ color: "#0284c7", fontSize: "1.5rem" }} />
                    <div>
                      <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0369a1" }}>
                        Automatic Entity Match
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#0284c7", marginTop: "2px" }}>
                        HCP hospital and physician identifiers linked via LangGraph workflows.
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

export default Analytics;
