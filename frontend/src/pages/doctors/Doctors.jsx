import React, { useEffect, useState } from "react";
import {
  Add as AddIcon,
  Search as SearchIcon,
  LocalHospital as HospitalIcon,
  LocationOn as LocationIcon,
  Phone as PhoneIcon,
  Email as EmailIcon,
  MedicalServices as MedicalIcon,
  Close as CloseIcon,
  DeleteOutlined as DeleteIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import EmptyState from "../../components/common/EmptyState";
import LoadingState from "../../components/common/LoadingState";
import doctorService from "../../services/doctorService";

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
      console.error("Error fetching HCPs:", err);
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
      setModalError("All fields are required to register an HCP.");
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
        "Failed to create HCP record. Please verify fields are unique."
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
      alert(err?.response?.data?.detail || "Could not delete HCP.");
    }
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
    <AppShell title="Healthcare Professionals">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
        <PageHeader
          tag="Territory Directory"
          title="Healthcare Professionals (HCPs)"
          description="Manage doctors, hospitals, and clinical specialists across your assigned sales territory."
          actions={
            <button
              type="button"
              onClick={() => setIsModalOpen(true)}
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
                boxShadow: "0 2px 6px rgba(2, 132, 199, 0.2)",
              }}
            >
              <AddIcon style={{ fontSize: "1.1rem" }} />
              <span>Add Healthcare Professional</span>
            </button>
          }
        />

        {/* Search & Specialization filter chips */}
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
              placeholder="Search by doctor name, hospital, or city..."
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

          {/* Specialty chips */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", color: "#64748b" }}>
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
                    padding: "0.3rem 0.75rem",
                    borderRadius: "9999px",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    backgroundColor: active ? "#0284c7" : "#f1f5f9",
                    color: active ? "#ffffff" : "#475569",
                    border: active ? "1px solid #0284c7" : "1px solid #e2e8f0",
                    transition: "all 0.15s ease",
                  }}
                >
                  {spec}
                </button>
              );
            })}
          </div>
        </div>

        {/* HCP Grid / List */}
        {loading ? (
          <LoadingState label="Loading healthcare professionals..." />
        ) : filteredHcps.length === 0 ? (
          <EmptyState
            iconType="user"
            title={searchQuery || selectedSpecialty !== "All" ? "No matching HCPs found" : "No HCPs registered yet"}
            description={
              searchQuery || selectedSpecialty !== "All"
                ? "Try adjusting your search query or specialty filter."
                : "Add your first healthcare professional to start managing relationship intelligence."
            }
            action={
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
                }}
              >
                <AddIcon style={{ fontSize: "1.1rem" }} />
                <span>Add HCP</span>
              </button>
            }
          />
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(320px, 1fr))",
              gap: "1.25rem",
            }}
          >
            {filteredHcps.map((hcp) => (
              <div
                key={hcp.id}
                className="pulse-card pulse-card-interactive"
                style={{
                  padding: "1.25rem",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  minHeight: "200px",
                }}
              >
                <div>
                  {/* Top: Name & Specialty */}
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem" }}>
                    <div>
                      <h3 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a" }}>
                        {hcp.doctor_name}
                      </h3>
                      <div style={{ marginTop: "0.35rem" }}>
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
                        borderRadius: "6px",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = "#dc2626")}
                      onMouseLeave={(e) => (e.currentTarget.style.color = "#94a3b8")}
                      title="Remove HCP"
                    >
                      <DeleteIcon style={{ fontSize: "1.15rem" }} />
                    </button>
                  </div>

                  {/* Hospital & Location */}
                  <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8125rem", color: "#475569" }}>
                      <HospitalIcon style={{ fontSize: "1rem", color: "#0284c7" }} />
                      <span>{hcp.hospital}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.8125rem", color: "#64748b" }}>
                      <LocationIcon style={{ fontSize: "1rem", color: "#0d9488" }} />
                      <span>{hcp.city}</span>
                    </div>
                  </div>
                </div>

                {/* Contact info footer */}
                <div
                  style={{
                    borderTop: "1px solid #f1f5f9",
                    paddingTop: "0.85rem",
                    marginTop: "1rem",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.3rem",
                    fontSize: "0.75rem",
                    color: "#64748b",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    <PhoneIcon style={{ fontSize: "0.85rem" }} />
                    <span>{hcp.phone}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
                    <EmailIcon style={{ fontSize: "0.85rem" }} />
                    <span>{hcp.email}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Modal: Add New HCP */}
        {isModalOpen && (
          <div
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "rgba(15, 23, 42, 0.45)",
              backdropFilter: "blur(3px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 50,
              padding: "1rem",
            }}
            onClick={() => setIsModalOpen(false)}
          >
            <div
              className="pulse-card"
              style={{
                width: "100%",
                maxWidth: "500px",
                padding: "1.75rem",
                backgroundColor: "#ffffff",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "#0f172a" }}>
                  Register Healthcare Professional
                </h3>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  style={{ color: "#64748b", padding: "0.25rem" }}
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
                    placeholder="e.g. Dr. Rajesh Sharma"
                    value={modalForm.doctor_name}
                    onChange={(e) => setModalForm({ ...modalForm, doctor_name: e.target.value })}
                    style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem" }}
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#334155", marginBottom: "0.25rem" }}>
                      Specialization
                    </label>
                    <select
                      value={modalForm.specialization}
                      onChange={(e) => setModalForm({ ...modalForm, specialization: e.target.value })}
                      style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem", backgroundColor: "#ffffff" }}
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
                      placeholder="e.g. Mumbai"
                      value={modalForm.city}
                      onChange={(e) => setModalForm({ ...modalForm, city: e.target.value })}
                      style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem" }}
                    />
                  </div>
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#334155", marginBottom: "0.25rem" }}>
                    Hospital / Institution
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Apollo Hospital Mumbai"
                    value={modalForm.hospital}
                    onChange={(e) => setModalForm({ ...modalForm, hospital: e.target.value })}
                    style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem" }}
                  />
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem" }}>
                  <div>
                    <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#334155", marginBottom: "0.25rem" }}>
                      Phone
                    </label>
                    <input
                      type="tel"
                      placeholder="+91 98765 43210"
                      value={modalForm.phone}
                      onChange={(e) => setModalForm({ ...modalForm, phone: e.target.value })}
                      style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem" }}
                    />
                  </div>

                  <div>
                    <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "#334155", marginBottom: "0.25rem" }}>
                      Email
                    </label>
                    <input
                      type="email"
                      placeholder="dr.sharma@apollo.com"
                      value={modalForm.email}
                      onChange={(e) => setModalForm({ ...modalForm, email: e.target.value })}
                      style={{ width: "100%", padding: "0.55rem 0.75rem", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "0.875rem" }}
                    />
                  </div>
                </div>

                <div style={{ marginTop: "1rem", display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    style={{ padding: "0.55rem 1rem", borderRadius: "8px", border: "1px solid #e2e8f0", backgroundColor: "#ffffff", fontSize: "0.8125rem", fontWeight: 600, color: "#475569" }}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={modalSaving}
                    style={{ padding: "0.55rem 1.25rem", borderRadius: "8px", backgroundColor: "#0284c7", color: "#ffffff", fontSize: "0.8125rem", fontWeight: 600, cursor: modalSaving ? "not-allowed" : "pointer" }}
                  >
                    {modalSaving ? "Saving..." : "Save HCP Record"}
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
