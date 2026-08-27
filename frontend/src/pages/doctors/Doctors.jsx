import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Add as AddIcon,
  Search as SearchIcon,
  LocalHospital as HospitalIcon,
  LocationOn as LocationIcon,
  Phone as PhoneIcon,
  Email as EmailIcon,
  Close as CloseIcon,
  DeleteOutlined as DeleteIcon,
  AutoAwesome as SparkleIcon,
  EventAvailable as MeetingIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import EmptyState from "../../components/common/EmptyState";
import LoadingState from "../../components/common/LoadingState";
import doctorService from "../../services/doctorService";
import { useCopilot } from "../../context/CopilotContext";

const SPECIALIZATIONS = [
  "All",
  "Cardiology",
  "Oncology",
  "Endocrinology",
  "Neurology",
  "Pediatrics",
  "General Medicine",
];

export function Doctors() {
  const navigate = useNavigate();
  const { setSelectedHcp } = useCopilot();
  const [hcps, setHcps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSpecialty, setSelectedSpecialty] = useState("All");

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalForm, setModalForm] = useState({
    doctor_name: "",
    specialization: "Cardiology",
    hospital: "",
    city: "",
    phone: "",
    email: "",
  });
  const [modalError, setModalError] = useState("");
  const [modalSaving, setModalSaving] = useState(false);

  const fetchHcps = async () => {
    try {
      setLoading(true);
      const data = await doctorService.getAll();
      if (Array.isArray(data)) {
        setHcps(data);
      }
    } catch (err) {
      console.error("Error fetching doctors:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHcps();
  }, []);

  const handleModalSubmit = async (e) => {
    e.preventDefault();
    if (!modalForm.doctor_name || !modalForm.hospital || !modalForm.city || !modalForm.phone || !modalForm.email) {
      setModalError("All fields are required to register a doctor.");
      return;
    }

    setModalSaving(true);
    setModalError("");

    try {
      await doctorService.create(modalForm);
      setIsModalOpen(false);
      setModalForm({
        doctor_name: "",
        specialization: "Cardiology",
        hospital: "",
        city: "",
        phone: "",
        email: "",
      });
      fetchHcps();
    } catch (err) {
      setModalError(
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to create doctor record. Please verify fields are unique."
      );
    } finally {
      setModalSaving(false);
    }
  };

  const handleDeleteHcp = async (id, name) => {
    if (!window.confirm(`Are you sure you want to remove ${name} from your territory?`)) {
      return;
    }
    try {
      await doctorService.delete(id);
      fetchHcps();
    } catch (err) {
      alert(err?.response?.data?.detail || "Could not delete doctor.");
    }
  };

  const handleChatWithDoctor = (hcp) => {
    if (setSelectedHcp) {
      setSelectedHcp(hcp.id, hcp.doctor_name, hcp.hospital, hcp.city);
    }
    navigate("/voice-copilot");
  };

  // Filtering
  const filteredHcps = hcps.filter((hcp) => {
    const matchesSearch =
      (hcp.doctor_name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (hcp.hospital || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (hcp.city || "").toLowerCase().includes(searchQuery.toLowerCase());

    const matchesSpecialty =
      selectedSpecialty === "All" ||
      (hcp.specialization || "").toLowerCase() === selectedSpecialty.toLowerCase();

    return matchesSearch && matchesSpecialty;
  });

  return (
    <AppShell title="Doctors">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
        <PageHeader
          tag="DOCTORS DIRECTORY"
          title="Doctors"
          description="Manage your healthcare professional relationships."
          actions={
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
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
              <span>Add Doctor</span>
            </button>
          }
        />

        {/* Search & Specialization filter chips */}
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
              placeholder="Search doctors..."
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

          {/* Specialty chips */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.72rem", fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>
              Specialty:
            </span>
            {SPECIALIZATIONS.map((spec) => {
              const active = selectedSpecialty === spec;
              return (
                <button
                  key={spec}
                  type="button"
                  onClick={() => setSelectedSpecialty(spec)}
                  style={{
                    padding: "0.25rem 0.65rem",
                    borderRadius: "9999px",
                    fontSize: "0.72rem",
                    fontWeight: 600,
                    backgroundColor: active ? "#0284c7" : "#f1f5f9",
                    color: active ? "#ffffff" : "#475569",
                    border: active ? "1px solid #0284c7" : "1px solid #e2e8f0",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                  }}
                >
                  {spec}
                </button>
              );
            })}
          </div>
        </div>

        {/* Doctor Cards Grid */}
        {loading ? (
          <LoadingState label="Loading doctors directory..." />
        ) : filteredHcps.length === 0 ? (
          <EmptyState
            iconType="user"
            title={searchQuery || selectedSpecialty !== "All" ? "No matching doctors found" : "No doctors yet"}
            description={
              searchQuery || selectedSpecialty !== "All"
                ? "Try adjusting your search query or specialty filter."
                : "Add your first doctor or tell Ask PulseCRM about someone you met."
            }
            action={
              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", justifyContent: "center" }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(true)}
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
                  <AddIcon style={{ fontSize: "1.1rem" }} />
                  <span>Add Doctor</span>
                </button>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredHcps.map((hcp) => (
              <div
                key={hcp.id}
                style={{
                  padding: "1.15rem",
                  borderRadius: "12px",
                  backgroundColor: "#ffffff",
                  border: "1px solid #e2e8f0",
                  boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  minHeight: "190px",
                }}
              >
                <div>
                  {/* Top: Name & Specialty */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                    <div style={{ minWidth: 0 }}>
                      <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "#0f172a", margin: 0, wordBreak: "break-word" }}>
                        {hcp.doctor_name}
                      </h3>
                      <div style={{ marginTop: "0.3rem" }}>
                        <StatusBadge variant="specialty" size="sm">
                          {hcp.specialization}
                        </StatusBadge>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleDeleteHcp(hcp.id, hcp.doctor_name)}
                      style={{
                        padding: "0.3rem",
                        color: "#94a3b8",
                        border: "none",
                        background: "none",
                        borderRadius: "6px",
                        minWidth: "36px",
                        minHeight: "36px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        cursor: "pointer",
                      }}
                      title="Remove Doctor"
                      aria-label={`Remove ${hcp.doctor_name}`}
                    >
                      <DeleteIcon style={{ fontSize: "1.1rem" }} />
                    </button>
                  </div>

                  {/* Hospital & Location */}
                  <div style={{ marginTop: "0.75rem", display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", fontSize: "0.8rem", color: "#475569" }}>
                      <HospitalIcon style={{ fontSize: "0.95rem", color: "#0284c7", flexShrink: 0 }} />
                      <span style={{ wordBreak: "break-word" }}>{hcp.hospital}</span>
                    </div>
                    {hcp.city && (
                      <div style={{ display: "flex", alignItems: "center", gap: "0.45rem", fontSize: "0.8rem", color: "#64748b" }}>
                        <LocationIcon style={{ fontSize: "0.95rem", color: "#0d9488", flexShrink: 0 }} />
                        <span style={{ wordBreak: "break-word" }}>{hcp.city}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Contact info & Action Buttons */}
                <div style={{ borderTop: "1px solid #f1f5f9", paddingTop: "0.75rem", marginTop: "0.75rem" }}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem", fontSize: "0.72rem", color: "#64748b", marginBottom: "0.6rem" }}>
                    {hcp.phone && (
                      <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                        <PhoneIcon style={{ fontSize: "0.8rem" }} />
                        <span>{hcp.phone}</span>
                      </div>
                    )}
                    {hcp.email && (
                      <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", overflow: "hidden" }}>
                        <EmailIcon style={{ fontSize: "0.8rem" }} />
                        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{hcp.email}</span>
                      </div>
                    )}
                  </div>

                  <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      onClick={() => handleChatWithDoctor(hcp)}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.3rem",
                        padding: "0.35rem 0.65rem",
                        borderRadius: "6px",
                        backgroundColor: "#f0f9ff",
                        color: "#0369a1",
                        border: "1px solid #bae6fd",
                        fontSize: "0.72rem",
                        fontWeight: 600,
                        cursor: "pointer",
                        minHeight: "36px",
                      }}
                    >
                      <SparkleIcon style={{ fontSize: "0.85rem" }} />
                      <span>Ask PulseCRM</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => navigate("/ai-meeting")}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.3rem",
                        padding: "0.35rem 0.65rem",
                        borderRadius: "6px",
                        backgroundColor: "#f8fafc",
                        color: "#475569",
                        border: "1px solid #e2e8f0",
                        fontSize: "0.72rem",
                        fontWeight: 600,
                        cursor: "pointer",
                        minHeight: "36px",
                      }}
                    >
                      <MeetingIcon style={{ fontSize: "0.85rem" }} />
                      <span>Schedule</span>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Modal: Add New Doctor */}
        {isModalOpen && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Add Doctor"
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
            onClick={() => setIsModalOpen(false)}
          >
            <div
              style={{
                width: "95vw",
                maxWidth: "480px",
                padding: "1.5rem",
                backgroundColor: "#ffffff",
                borderRadius: "14px",
                maxHeight: "90vh",
                overflowY: "auto",
                boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1)",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0f172a", margin: 0 }}>
                  Add Doctor
                </h3>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  style={{ color: "#64748b", background: "none", border: "none", padding: "0.4rem", cursor: "pointer", minWidth: "36px", minHeight: "36px" }}
                  aria-label="Close dialog"
                >
                  <CloseIcon fontSize="small" />
                </button>
              </div>

              {modalError && (
                <div
                  style={{
                    padding: "0.65rem 0.85rem",
                    borderRadius: "8px",
                    backgroundColor: "#fef2f2",
                    border: "1px solid #fecaca",
                    color: "#dc2626",
                    fontSize: "0.8125rem",
                    marginBottom: "1rem",
                  }}
                >
                  {modalError}
                </div>
              )}

              <form onSubmit={handleModalSubmit} style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#334155", marginBottom: "0.25rem" }}>
                    Doctor Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Dr. Rajesh Kumar"
                    value={modalForm.doctor_name}
                    onChange={(e) => setModalForm({ ...modalForm, doctor_name: e.target.value })}
                    style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem", boxSizing: "border-box", minHeight: "44px" }}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#334155", marginBottom: "0.25rem" }}>
                      Specialization
                    </label>
                    <select
                      value={modalForm.specialization}
                      onChange={(e) => setModalForm({ ...modalForm, specialization: e.target.value })}
                      style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem", backgroundColor: "#ffffff", boxSizing: "border-box", minHeight: "44px" }}
                    >
                      {SPECIALIZATIONS.filter((s) => s !== "All").map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#334155", marginBottom: "0.25rem" }}>
                      City
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Hyderabad"
                      value={modalForm.city}
                      onChange={(e) => setModalForm({ ...modalForm, city: e.target.value })}
                      style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem", boxSizing: "border-box", minHeight: "44px" }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#334155", marginBottom: "0.25rem" }}>
                    Hospital / Clinic
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Apollo Hospital"
                    value={modalForm.hospital}
                    onChange={(e) => setModalForm({ ...modalForm, hospital: e.target.value })}
                    style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem", boxSizing: "border-box", minHeight: "44px" }}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#334155", marginBottom: "0.25rem" }}>
                      Phone
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. 9876543210"
                      value={modalForm.phone}
                      onChange={(e) => setModalForm({ ...modalForm, phone: e.target.value })}
                      style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem", boxSizing: "border-box", minHeight: "44px" }}
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#334155", marginBottom: "0.25rem" }}>
                      Email
                    </label>
                    <input
                      type="email"
                      placeholder="e.g. doctor@hospital.com"
                      value={modalForm.email}
                      onChange={(e) => setModalForm({ ...modalForm, email: e.target.value })}
                      style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem", boxSizing: "border-box", minHeight: "44px" }}
                    />
                  </div>
                </div>

                <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end", marginTop: "0.5rem" }}>
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    style={{ padding: "0.55rem 1rem", borderRadius: "8px", border: "1px solid #cbd5e1", backgroundColor: "#ffffff", color: "#64748b", fontSize: "0.8125rem", fontWeight: 600, cursor: "pointer", minHeight: "44px" }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={modalSaving}
                    style={{ padding: "0.55rem 1.25rem", borderRadius: "8px", border: "none", backgroundColor: "#0284c7", color: "#ffffff", fontSize: "0.8125rem", fontWeight: 600, cursor: modalSaving ? "not-allowed" : "pointer", minHeight: "44px" }}
                  >
                    {modalSaving ? "Saving..." : "Save Doctor"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default Doctors;
