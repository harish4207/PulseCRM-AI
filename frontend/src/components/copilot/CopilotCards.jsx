import React, { useState } from "react";
import {
  LocalHospital as HospitalIcon,
  EventNote as EventIcon,
  CheckCircle as CheckIcon,
  Cancel as CancelIcon,
  Phone as PhoneIcon,
  Email as EmailIcon,
  MedicalServices as MedIcon,
  AssignmentTurnedIn as TaskIcon,
  Edit as EditIcon,
  InfoOutlined as InfoIcon,
  Save as SaveIcon,
  Close as CloseIcon,
} from "@mui/icons-material";

export function HcpCard({ data }) {
  if (!data) return null;
  const { doctor_name, specialization, hospital, city, phone, email } = data;

  return (
    <div
      style={{
        marginTop: "0.5rem",
        padding: "0.75rem 0.9rem",
        borderRadius: "10px",
        backgroundColor: "#f8fafc",
        border: "1px solid #e2e8f0",
        display: "flex",
        flexDirection: "column",
        gap: "0.4rem",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>
          {doctor_name}
        </span>
        {specialization && (
          <span
            style={{
              fontSize: "0.7rem",
              fontWeight: 600,
              padding: "0.15rem 0.45rem",
              borderRadius: "6px",
              backgroundColor: "#e0f2fe",
              color: "#0369a1",
            }}
          >
            {specialization}
          </span>
        )}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.775rem", color: "#475569" }}>
        <HospitalIcon style={{ fontSize: "0.9rem", color: "#0284c7" }} />
        <span>{hospital} {city ? `· ${city}` : ""}</span>
      </div>

      {(phone || email) && (
        <div style={{ display: "flex", gap: "0.8rem", fontSize: "0.72rem", color: "#64748b", marginTop: "0.2rem" }}>
          {phone && (
            <span style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
              <PhoneIcon style={{ fontSize: "0.8rem" }} /> {phone}
            </span>
          )}
          {email && (
            <span style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
              <EmailIcon style={{ fontSize: "0.8rem" }} /> {email}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export function FollowupsListCard({ data }) {
  if (!data || !data.followups || data.followups.length === 0) return null;
  const { followups } = data;

  return (
    <div
      style={{
        marginTop: "0.5rem",
        padding: "0.75rem 0.9rem",
        borderRadius: "10px",
        backgroundColor: "#f8fafc",
        border: "1px solid #e2e8f0",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
      }}
    >
      <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#0f172a", display: "flex", alignItems: "center", gap: "0.35rem" }}>
        <EventIcon style={{ fontSize: "0.95rem", color: "#0284c7" }} />
        <span>Scheduled Follow-ups ({followups.length})</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
        {followups.slice(0, 4).map((f, idx) => (
          <div
            key={idx}
            style={{
              padding: "0.45rem 0.65rem",
              borderRadius: "8px",
              backgroundColor: "#ffffff",
              border: "1px solid #e2e8f0",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: "0.775rem",
            }}
          >
            <div>
              <div style={{ fontWeight: 600, color: "#0f172a" }}>
                {f.hcp_name || f.doctor_name || "Doctor"}
              </div>
              <div style={{ fontSize: "0.7rem", color: "#64748b" }}>
                {f.hospital || "Hospital"}
              </div>
            </div>
            <span
              style={{
                fontSize: "0.7rem",
                fontWeight: 600,
                color: "#0369a1",
                backgroundColor: "#e0f2fe",
                padding: "0.15rem 0.4rem",
                borderRadius: "4px",
              }}
            >
              {(f.follow_up_date || "").slice(0, 10)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function InteractionCard({ data }) {
  if (!data || !data.interactions || data.interactions.length === 0) return null;
  const { interactions, doctor_name } = data;

  return (
    <div
      style={{
        marginTop: "0.5rem",
        padding: "0.75rem 0.9rem",
        borderRadius: "10px",
        backgroundColor: "#f8fafc",
        border: "1px solid #e2e8f0",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
      }}
    >
      <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "#0f172a" }}>
        Recent Interactions {doctor_name ? `with ${doctor_name}` : ""}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.4rem" }}>
        {interactions.slice(0, 3).map((inter, idx) => (
          <div
            key={idx}
            style={{
              padding: "0.5rem 0.65rem",
              borderRadius: "8px",
              backgroundColor: "#ffffff",
              border: "1px solid #e2e8f0",
              fontSize: "0.75rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.2rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", color: "#64748b", fontSize: "0.7rem" }}>
              <span>{(inter.created_at || "").slice(0, 10)}</span>
              {inter.products_discussed && (
                <span style={{ fontWeight: 600, color: "#0284c7" }}>
                  {inter.products_discussed}
                </span>
              )}
            </div>
            <p style={{ margin: 0, color: "#1e293b", lineHeight: 1.4 }}>
              {inter.meeting_notes || inter.ai_summary || "Routine meeting."}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ConfirmationActionCard({ data, onConfirm, onCancel }) {
  if (!data) return null;
  const { doctor_name, date, time, action_id, is_completed, status } = data;
  const isCompleted = is_completed || status === "completed";

  return (
    <div
      style={{
        marginTop: "0.5rem",
        padding: "0.85rem 1rem",
        borderRadius: "12px",
        backgroundColor: "#ffffff",
        border: isCompleted ? "1px solid #bbf7d0" : "1px solid #bae6fd",
        boxShadow: "0 2px 4px rgba(2,132,199,0.06)",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        maxWidth: "100%",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #f1f5f9", paddingBottom: "0.4rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <EventIcon style={{ fontSize: "1.1rem", color: isCompleted ? "#16a34a" : "#0284c7" }} />
          <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>
            {isCompleted ? "✓ FOLLOW-UP SCHEDULED" : "FOLLOW-UP REVIEW"}
          </span>
        </div>
        <span
          style={{
            fontSize: "0.68rem",
            fontWeight: 600,
            padding: "0.15rem 0.5rem",
            borderRadius: "6px",
            backgroundColor: isCompleted ? "#dcfce7" : "#fef3c7",
            color: isCompleted ? "#166534" : "#92400e",
          }}
        >
          {isCompleted ? "✓ Saved" : "Requires Confirmation"}
        </span>
      </div>

      <div style={{ fontSize: "0.8rem", color: "#334155", lineHeight: 1.5 }}>
        {isCompleted ? (
          <>
            Follow-up with <strong>{doctor_name}</strong> scheduled for <strong>{date} {time ? `at ${time}` : ""}</strong>.
          </>
        ) : (
          <>
            Schedule a follow-up with <strong>{doctor_name}</strong> on <strong>{date} {time ? `at ${time}` : ""}</strong>?
          </>
        )}
      </div>

      {isCompleted ? (
        <div style={{ padding: "0.4rem 0.6rem", borderRadius: "6px", backgroundColor: "#f0fdf4", border: "1px solid #bbf7d0", fontSize: "0.72rem", color: "#166534", fontWeight: 600 }}>
          ✓ Follow-up saved to your CRM
        </div>
      ) : (
        <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", marginTop: "0.2rem" }}>
          <button
            type="button"
            onClick={onConfirm}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.3rem",
              padding: "0.45rem 0.85rem",
              borderRadius: "6px",
              backgroundColor: "#16a34a",
              color: "#ffffff",
              border: "none",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <CheckIcon style={{ fontSize: "0.85rem" }} /> Confirm & Schedule (అవును)
          </button>
          <button
            type="button"
            onClick={onCancel}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.3rem",
              padding: "0.45rem 0.85rem",
              borderRadius: "6px",
              backgroundColor: "#ffffff",
              color: "#dc2626",
              border: "1px solid #fecaca",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            <CancelIcon style={{ fontSize: "0.85rem" }} /> Cancel (వద్దు)
          </button>
        </div>
      )}
    </div>
  );
}

export function MeetingCaptureCard({ data, onConfirm, onCancel, onUpdateMeeting }) {
  if (!data) return null;
  const {
    doctor_name,
    hospital,
    city,
    specialization,
    meeting_date_display,
    product,
    request,
    follow_up_display,
    phone,
    email,
    is_new_hcp,
    actions = [],
    evidence = {},
    changes_applied,
    is_completed,
    status,
  } = data;

  const isCompleted = is_completed || status === "completed";
  const [isEditing, setIsEditing] = useState(false);
  const [editProduct, setEditProduct] = useState(product && product !== "Not specified" && product !== "General discussion" ? product : "");
  const [editRequest, setEditRequest] = useState(request && request !== "Not specified" ? request : "");
  const [editFollowUp, setEditFollowUp] = useState(follow_up_display && follow_up_display !== "Not scheduled" ? follow_up_display : "");

  const handleSaveEdit = () => {
    setIsEditing(false);
    if (onUpdateMeeting) {
      onUpdateMeeting({
        ...data,
        product: editProduct || "Not specified",
        request: editRequest || "Not specified",
        follow_up_display: editFollowUp || "Not scheduled",
      });
    }
  };

  const cardTitle = isCompleted
    ? (is_new_hcp ? "✓ NEW HCP CREATED" : "✓ MEETING SAVED")
    : (is_new_hcp ? "NEW HCP REVIEW" : "MEETING CAPTURE REVIEW");

  const displayProduct = (product && product !== "General discussion" && product !== "None") ? product : "Not specified";
  const hospLoc = hospital ? (city && !hospital.includes(city) ? `${hospital} · ${city}` : hospital) : "Hospital Clinic";

  return (
    <div
      style={{
        marginTop: "0.5rem",
        padding: "0.85rem 1rem",
        borderRadius: "12px",
        backgroundColor: "#ffffff",
        border: isCompleted ? "1px solid #bbf7d0" : "1px solid #bae6fd",
        boxShadow: "0 2px 4px rgba(2,132,199,0.06)",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        maxWidth: "100%",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #f1f5f9", paddingBottom: "0.4rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <MedIcon style={{ fontSize: "1.1rem", color: isCompleted ? "#16a34a" : "#0284c7" }} />
          <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>
            {cardTitle}
          </span>
        </div>
        <span
          style={{
            fontSize: "0.68rem",
            fontWeight: 600,
            padding: "0.15rem 0.5rem",
            borderRadius: "6px",
            backgroundColor: isCompleted ? "#dcfce7" : "#fef3c7",
            color: isCompleted ? "#166534" : "#92400e",
          }}
        >
          {isCompleted ? "✓ Saved" : "Requires Confirmation"}
        </span>
      </div>

      {changes_applied && changes_applied.length > 0 && !isCompleted && (
        <div style={{ padding: "0.4rem 0.6rem", borderRadius: "6px", backgroundColor: "#f0fdf4", border: "1px solid #bbf7d0", fontSize: "0.72rem", color: "#166534" }}>
          ✓ {changes_applied.join(", ")}
        </div>
      )}

      {isEditing ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
          <div>
            <label style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 600 }}>Product</label>
            <input type="text" value={editProduct} onChange={(e) => setEditProduct(e.target.value)} placeholder="Leave blank if not specified" style={{ width: "100%", padding: "0.35rem 0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.8rem", boxSizing: "border-box" }} />
          </div>
          <div>
            <label style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 600 }}>Doctor Request</label>
            <input type="text" value={editRequest} onChange={(e) => setEditRequest(e.target.value)} placeholder="e.g. send clinical brochure" style={{ width: "100%", padding: "0.35rem 0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.8rem", boxSizing: "border-box" }} />
          </div>
          <div>
            <label style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 600 }}>Follow-up Date</label>
            <input type="text" value={editFollowUp} onChange={(e) => setEditFollowUp(e.target.value)} placeholder="e.g. September 29, 2026" style={{ width: "100%", padding: "0.35rem 0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.8rem", boxSizing: "border-box" }} />
          </div>
          <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.2rem" }}>
            <button type="button" onClick={handleSaveEdit} style={{ padding: "0.4rem 0.8rem", borderRadius: "6px", backgroundColor: "#0284c7", color: "#ffffff", border: "none", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>Save</button>
            <button type="button" onClick={() => setIsEditing(false)} style={{ padding: "0.4rem 0.7rem", borderRadius: "6px", backgroundColor: "#ffffff", color: "#64748b", border: "1px solid #cbd5e1", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>Cancel</button>
          </div>
        </div>
      ) : (
        <>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
            <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>
              {doctor_name} {is_new_hcp && <span style={{ fontSize: "0.68rem", backgroundColor: "#dcfce7", color: "#166534", padding: "0.1rem 0.35rem", borderRadius: "4px" }}>New HCP</span>}
            </div>
            {specialization && (
              <div style={{ fontSize: "0.72rem", color: "#0284c7", fontWeight: 600 }}>
                {specialization}
              </div>
            )}
            <div style={{ fontSize: "0.775rem", color: "#475569" }}>
              {hospLoc} {meeting_date_display ? `· ${meeting_date_display}` : ""}
            </div>
            {(phone || email) && (
              <div style={{ display: "flex", gap: "0.6rem", fontSize: "0.72rem", color: "#64748b" }}>
                {phone && phone !== "Not specified" && <span>📞 {phone}</span>}
                {email && email !== "Not specified" && <span>✉️ {email}</span>}
              </div>
            )}
            <div style={{ fontSize: "0.75rem", color: displayProduct !== "Not specified" ? "#0284c7" : "#64748b", fontWeight: displayProduct !== "Not specified" ? 600 : 400 }}>
              Product: <strong>{displayProduct}</strong>
            </div>
            {request && request !== "Not specified" && request !== "None" && (
              <div style={{ fontSize: "0.75rem", color: "#78350f", backgroundColor: "#fef3c7", padding: "0.25rem 0.5rem", borderRadius: "4px" }}>
                Request: {request}
              </div>
            )}
            {follow_up_display && follow_up_display !== "Not scheduled" && follow_up_display !== "None" && (
              <div style={{ fontSize: "0.75rem", color: "#0369a1", fontWeight: 600 }}>
                📅 Scheduled Follow-up: {follow_up_display}
              </div>
            )}
          </div>

          {isCompleted ? (
            <div style={{ padding: "0.4rem 0.6rem", borderRadius: "6px", backgroundColor: "#f0fdf4", border: "1px solid #bbf7d0", fontSize: "0.72rem", color: "#166534", fontWeight: 600 }}>
              ✓ Saved to your CRM database
            </div>
          ) : (
            <div style={{ display: "flex", gap: "0.45rem", flexWrap: "wrap", marginTop: "0.25rem" }}>
              <button type="button" onClick={onConfirm} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", padding: "0.45rem 0.85rem", borderRadius: "6px", backgroundColor: "#16a34a", color: "#ffffff", border: "none", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>
                <CheckIcon style={{ fontSize: "0.85rem" }} /> Confirm & Save (అవును)
              </button>
              <button type="button" onClick={() => setIsEditing(true)} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", padding: "0.45rem 0.8rem", borderRadius: "6px", backgroundColor: "#ffffff", color: "#0369a1", border: "1px solid #bae6fd", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>
                <EditIcon style={{ fontSize: "0.85rem" }} /> Edit
              </button>
              <button type="button" onClick={onCancel} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", padding: "0.45rem 0.8rem", borderRadius: "6px", backgroundColor: "#ffffff", color: "#dc2626", border: "1px solid #fecaca", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>
                <CancelIcon style={{ fontSize: "0.85rem" }} /> Cancel (వద్దు)
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function AmbiguityCard({ data, onSelectCandidate }) {
  if (!data || !data.candidates || data.candidates.length === 0) return null;
  const { candidates } = data;

  return (
    <div style={{ marginTop: "0.5rem", padding: "0.75rem 0.9rem", borderRadius: "10px", backgroundColor: "#fffbeb", border: "1px solid #fde68a", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
      <div style={{ fontSize: "0.775rem", fontWeight: 700, color: "#92400e" }}>
        Multiple Doctors Found — Select One:
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
        {candidates.map((c) => (
          <button key={c.id} type="button" onClick={() => onSelectCandidate && onSelectCandidate(c)} style={{ padding: "0.35rem 0.65rem", borderRadius: "6px", backgroundColor: "#ffffff", border: "1px solid #fcd34d", fontSize: "0.75rem", fontWeight: 600, color: "#78350f", cursor: "pointer" }}>
            {c.doctor_name} ({c.hospital})
          </button>
        ))}
      </div>
    </div>
  );
}

export function CrmBriefCard({ data, onQuickQuery }) {
  if (!data || !data.brief) return null;
  const { brief } = data;
  const {
    today_date,
    today_meetings_count = 0,
    today_meetings = [],
    today_followups_count = 0,
    today_followups = [],
    doctors_to_visit_count = 0,
    overdue_followups_count = 0,
    recent_interactions_this_week_count = 0,
  } = brief;

  return (
    <div style={{ marginTop: "0.5rem", padding: "0.85rem 1rem", borderRadius: "12px", backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: "0.4rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <TaskIcon style={{ fontSize: "1.1rem", color: "#0284c7" }} />
          <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>Daily CRM Briefing</span>
        </div>
        <span style={{ fontSize: "0.72rem", color: "#64748b", fontWeight: 500 }}>{today_date}</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(105px, 1fr))", gap: "0.45rem" }}>
        <div style={{ backgroundColor: "#ffffff", padding: "0.5rem 0.6rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "0.68rem", color: "#64748b" }}>Today's Meetings</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0284c7" }}>{today_meetings_count}</div>
        </div>
        <div style={{ backgroundColor: "#ffffff", padding: "0.5rem 0.6rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "0.68rem", color: "#64748b" }}>Follow-ups</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0f172a" }}>{today_followups_count}</div>
        </div>
        <div style={{ backgroundColor: "#ffffff", padding: "0.5rem 0.6rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "0.68rem", color: "#64748b" }}>Overdue Tasks</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: overdue_followups_count > 0 ? "#dc2626" : "#16a34a" }}>
            {overdue_followups_count}
          </div>
        </div>
        <div style={{ backgroundColor: "#ffffff", padding: "0.5rem 0.6rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "0.68rem", color: "#64748b" }}>Weekly Meetings</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#16a34a" }}>{recent_interactions_this_week_count}</div>
        </div>
      </div>

      {today_meetings.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem", marginTop: "0.1rem" }}>
          <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "#0369a1" }}>Calendar Meetings Today:</span>
          {today_meetings.slice(0, 3).map((m, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", backgroundColor: "#ffffff", padding: "0.35rem 0.6rem", borderRadius: "6px", border: "1px solid #bae6fd" }}>
              <span style={{ fontWeight: 700, color: "#0f172a" }}>{m.doctor_name || "Doctor"}</span>
              <span style={{ color: "#0284c7", fontWeight: 600 }}>{m.meeting_time_display || "Today"}</span>
            </div>
          ))}
        </div>
      )}

      {today_followups.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem", marginTop: "0.1rem" }}>
          <span style={{ fontSize: "0.72rem", fontWeight: 600, color: "#475569" }}>Scheduled Follow-ups Today:</span>
          {today_followups.slice(0, 3).map((f, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", backgroundColor: "#ffffff", padding: "0.35rem 0.6rem", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
              <span style={{ fontWeight: 600, color: "#0f172a" }}>{f.hcp_name || "Doctor"}</span>
              <span style={{ color: "#64748b" }}>{f.hospital || "Hospital"}</span>
            </div>
          ))}
        </div>
      )}

      {onQuickQuery && (
        <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginTop: "0.2rem" }}>
          <button type="button" onClick={() => onQuickQuery("What follow-ups do I have today?")} style={{ fontSize: "0.72rem", fontWeight: 600, padding: "0.3rem 0.6rem", borderRadius: "6px", backgroundColor: "#e0f2fe", color: "#0369a1", border: "1px solid #bae6fd", cursor: "pointer" }}>
            View Today's Follow-ups
          </button>
          <button type="button" onClick={() => onQuickQuery("How many follow-ups are overdue?")} style={{ fontSize: "0.72rem", fontWeight: 600, padding: "0.3rem 0.6rem", borderRadius: "6px", backgroundColor: "#fef2f2", color: "#b91c1c", border: "1px solid #fecaca", cursor: "pointer" }}>
            Review Overdue ({overdue_followups_count})
          </button>
        </div>
      )}
    </div>
  );
}

export function PreMeetingIntelligenceCard({ data }) {
  if (!data || !data.intelligence) return null;
  const { hcp, intelligence } = data;
  const doc = intelligence.doctor || hcp || {};
  const lastI = intelligence.last_interaction;
  const prods = intelligence.products_discussed_history || [];
  const openReqs = intelligence.open_requests || [];
  const nextFu = intelligence.next_followup;

  return (
    <div style={{ marginTop: "0.5rem", padding: "0.85rem 1rem", borderRadius: "12px", backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "0.55rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", borderBottom: "1px solid #e2e8f0", paddingBottom: "0.4rem" }}>
        <div>
          <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#0f172a" }}>{doc.doctor_name || "Doctor"}</div>
          <div style={{ fontSize: "0.75rem", color: "#475569" }}>{doc.hospital} {doc.city ? `· ${doc.city}` : ""} · {doc.specialization}</div>
        </div>
        <span style={{ fontSize: "0.68rem", fontWeight: 600, padding: "0.15rem 0.45rem", borderRadius: "6px", backgroundColor: "#e0f2fe", color: "#0284c7" }}>
          Pre-Meeting Brief
        </span>
      </div>

      {prods.length > 0 && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", flexWrap: "wrap", fontSize: "0.72rem" }}>
          <span style={{ color: "#64748b", fontWeight: 600 }}>Products History:</span>
          {prods.map((p, idx) => (
            <span key={idx} style={{ backgroundColor: "#f1f5f9", padding: "0.15rem 0.45rem", borderRadius: "4px", color: "#334155", fontWeight: 500 }}>
              {p}
            </span>
          ))}
        </div>
      )}

      {lastI && (
        <div style={{ backgroundColor: "#ffffff", padding: "0.5rem 0.65rem", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <div style={{ fontSize: "0.7rem", fontWeight: 600, color: "#64748b", marginBottom: "0.15rem" }}>
            Last Meeting ({(lastI.created_at || "").slice(0, 10)})
          </div>
          <div style={{ fontSize: "0.775rem", color: "#0f172a", lineHeight: 1.45 }}>
            {lastI.meeting_notes || lastI.ai_summary || "Routine relationship meeting."}
          </div>
        </div>
      )}

      {openReqs.length > 0 && (
        <div style={{ backgroundColor: "#fffbeb", padding: "0.5rem 0.65rem", borderRadius: "8px", border: "1px solid #fde68a" }}>
          <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "#92400e", marginBottom: "0.15rem" }}>
            Open Commitments & Requests:
          </div>
          {openReqs.map((req, idx) => (
            <div key={idx} style={{ fontSize: "0.75rem", color: "#78350f" }}>• {req}</div>
          ))}
        </div>
      )}

      {nextFu && (
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", fontSize: "0.72rem", color: "#0369a1" }}>
          <EventIcon style={{ fontSize: "0.85rem" }} />
          <span>Scheduled Follow-up: <strong>{(nextFu.follow_up_date || "").slice(0, 10)}</strong></span>
        </div>
      )}
    </div>
  );
}

export function AnalyticsCard({ data }) {
  if (!data || !data.analytics) return null;
  const { analytics, metric } = data;
  const { title, total_count = 0, items = [], period } = analytics;

  return (
    <div style={{ marginTop: "0.5rem", padding: "0.85rem 1rem", borderRadius: "12px", backgroundColor: "#f8fafc", border: "1px solid #e2e8f0", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #e2e8f0", paddingBottom: "0.4rem" }}>
        <div>
          <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0f172a" }}>{title}</span>
          <span style={{ fontSize: "0.7rem", color: "#64748b", marginLeft: "0.4rem" }}>({period})</span>
        </div>
        <span style={{ fontSize: "0.8rem", fontWeight: 700, padding: "0.15rem 0.55rem", borderRadius: "9999px", backgroundColor: "#e0f2fe", color: "#0284c7" }}>
          Total: {total_count}
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.35rem" }}>
        {items.length === 0 ? (
          <div style={{ fontSize: "0.75rem", color: "#64748b", fontStyle: "italic" }}>No records found for this timeframe.</div>
        ) : (
          items.slice(0, 5).map((item, idx) => (
            <div key={idx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", backgroundColor: "#ffffff", padding: "0.35rem 0.6rem", borderRadius: "6px", border: "1px solid #f1f5f9" }}>
              <span style={{ fontWeight: 600, color: "#0f172a" }}>{item.doctor_name || item.hcp_name || item.product || "Doctor"}</span>
              <span style={{ color: "#64748b" }}>{item.hospital || (item.follow_up_date || item.created_at || "").slice(0, 10)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export function MeetingScheduleCard({ data, onConfirm, onCancel, onUpdateMeeting }) {
  if (!data) return null;
  const {
    doctor_name,
    hospital,
    city,
    specialization,
    meeting_date_display,
    meeting_time_display,
    location,
    reminder_display,
    conflict_info,
    changes_applied,
    is_completed,
    status,
  } = data;

  const isCompleted = is_completed || status === "completed";
  const hasConflict = conflict_info && conflict_info.is_conflict && !isCompleted;

  const [isEditing, setIsEditing] = useState(false);
  const [editDate, setEditDate] = useState(meeting_date_display || "");
  const [editTime, setEditTime] = useState(meeting_time_display || "");
  const [editReminder, setEditReminder] = useState(reminder_display || "30 minutes before");
  const [editLocation, setEditLocation] = useState(location || hospital || "");

  const handleSaveEdit = () => {
    setIsEditing(false);
    if (onUpdateMeeting) {
      onUpdateMeeting({
        ...data,
        meeting_date_display: editDate,
        meeting_time_display: editTime,
        reminder_display: editReminder,
        location: editLocation,
      });
    }
  };

  const hospLoc = location || (hospital ? (city && !hospital.includes(city) ? `${hospital} · ${city}` : hospital) : "Apollo Hospital · Visakhapatnam");

  return (
    <div
      style={{
        marginTop: "0.5rem",
        padding: "0.85rem 1rem",
        borderRadius: "12px",
        backgroundColor: "#ffffff",
        border: isCompleted ? "1px solid #bbf7d0" : hasConflict ? "1px solid #fed7aa" : "1px solid #bae6fd",
        boxShadow: "0 2px 4px rgba(2,132,199,0.06)",
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        maxWidth: "100%",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #f1f5f9", paddingBottom: "0.4rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <EventIcon style={{ fontSize: "1.1rem", color: isCompleted ? "#16a34a" : hasConflict ? "#ea580c" : "#0284c7" }} />
          <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>
            {isCompleted ? "✓ MEETING SCHEDULED" : "MEETING REVIEW"}
          </span>
        </div>
        <span
          style={{
            fontSize: "0.68rem",
            fontWeight: 600,
            padding: "0.15rem 0.5rem",
            borderRadius: "6px",
            backgroundColor: isCompleted ? "#dcfce7" : hasConflict ? "#ffedd5" : "#fef3c7",
            color: isCompleted ? "#166534" : hasConflict ? "#c2410c" : "#92400e",
          }}
        >
          {isCompleted ? "✓ Scheduled" : hasConflict ? "⚠️ Scheduling Conflict" : "Requires Confirmation"}
        </span>
      </div>

      {hasConflict && (
        <div style={{ padding: "0.5rem 0.7rem", borderRadius: "8px", backgroundColor: "#fffbeb", border: "1px solid #fde68a", fontSize: "0.75rem", color: "#92400e", lineHeight: 1.4 }}>
          ⚠️ <strong>POSSIBLE SCHEDULING CONFLICT:</strong> You already have a meeting with{" "}
          <strong>{conflict_info.conflicting_meeting?.doctor_name || "another doctor"}</strong> on{" "}
          <strong>{conflict_info.conflicting_meeting?.meeting_time_display || "the same day"}</strong>.
        </div>
      )}

      {changes_applied && changes_applied.length > 0 && !isCompleted && (
        <div style={{ padding: "0.4rem 0.6rem", borderRadius: "6px", backgroundColor: "#f0fdf4", border: "1px solid #bbf7d0", fontSize: "0.72rem", color: "#166534" }}>
          ✓ {changes_applied.join(", ")}
        </div>
      )}

      {isEditing ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
          <div>
            <label style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 600 }}>Date</label>
            <input type="text" value={editDate} onChange={(e) => setEditDate(e.target.value)} style={{ width: "100%", padding: "0.35rem 0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.8rem", boxSizing: "border-box" }} />
          </div>
          <div>
            <label style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 600 }}>Time</label>
            <input type="text" value={editTime} onChange={(e) => setEditTime(e.target.value)} style={{ width: "100%", padding: "0.35rem 0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.8rem", boxSizing: "border-box" }} />
          </div>
          <div>
            <label style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 600 }}>Reminder</label>
            <input type="text" value={editReminder} onChange={(e) => setEditReminder(e.target.value)} style={{ width: "100%", padding: "0.35rem 0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.8rem", boxSizing: "border-box" }} />
          </div>
          <div>
            <label style={{ fontSize: "0.7rem", color: "#64748b", fontWeight: 600 }}>Location</label>
            <input type="text" value={editLocation} onChange={(e) => setEditLocation(e.target.value)} style={{ width: "100%", padding: "0.35rem 0.5rem", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "0.8rem", boxSizing: "border-box" }} />
          </div>
          <div style={{ display: "flex", gap: "0.4rem", marginTop: "0.2rem" }}>
            <button type="button" onClick={handleSaveEdit} style={{ padding: "0.35rem 0.75rem", borderRadius: "6px", backgroundColor: "#0284c7", color: "#ffffff", border: "none", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>Done Editing</button>
            <button type="button" onClick={() => setIsEditing(false)} style={{ padding: "0.35rem 0.65rem", borderRadius: "6px", backgroundColor: "#ffffff", color: "#64748b", border: "1px solid #cbd5e1", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>Cancel</button>
          </div>
        </div>
      ) : (
        <>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
            <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>
              {doctor_name}
            </div>
            {specialization && (
              <div style={{ fontSize: "0.72rem", color: "#0284c7", fontWeight: 600 }}>
                {specialization}
              </div>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.775rem", color: "#475569" }}>
              <HospitalIcon style={{ fontSize: "0.9rem", color: "#0284c7" }} />
              <span>{hospLoc}</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.775rem", color: "#0f172a", fontWeight: 600, marginTop: "0.1rem" }}>
              <EventIcon style={{ fontSize: "0.9rem", color: "#0284c7" }} />
              <span>{meeting_date_display} · {meeting_time_display}</span>
            </div>
            {reminder_display && reminder_display.toLowerCase() !== "no reminder" && (
              <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.75rem", color: "#64748b" }}>
                <span>🔔 Reminder: {reminder_display}</span>
              </div>
            )}
          </div>

          <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap", marginTop: "0.15rem" }}>
            <span style={{ fontSize: "0.68rem", fontWeight: 600, padding: "0.15rem 0.45rem", borderRadius: "4px", backgroundColor: "#e0f2fe", color: "#0369a1" }}>
              ✓ Schedule Meeting
            </span>
            {reminder_display && reminder_display.toLowerCase() !== "no reminder" && (
              <span style={{ fontSize: "0.68rem", fontWeight: 600, padding: "0.15rem 0.45rem", borderRadius: "4px", backgroundColor: "#f1f5f9", color: "#334155" }}>
                ✓ Create Reminder
              </span>
            )}
          </div>

          {isCompleted ? (
            <div style={{ padding: "0.4rem 0.6rem", borderRadius: "6px", backgroundColor: "#f0fdf4", border: "1px solid #bbf7d0", fontSize: "0.72rem", color: "#166534", fontWeight: 600 }}>
              ✓ Scheduled successfully in your CRM
            </div>
          ) : hasConflict ? (
            <div style={{ display: "flex", gap: "0.45rem", flexWrap: "wrap", marginTop: "0.35rem" }}>
              <button type="button" onClick={onConfirm} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", padding: "0.45rem 0.85rem", borderRadius: "6px", backgroundColor: "#ea580c", color: "#ffffff", border: "none", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer", boxShadow: "0 1px 2px rgba(234,88,12,0.2)" }}>
                <CheckIcon style={{ fontSize: "0.85rem" }} /> Schedule Anyway
              </button>
              <button type="button" onClick={() => setIsEditing(true)} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", padding: "0.45rem 0.8rem", borderRadius: "6px", backgroundColor: "#ffffff", color: "#0369a1", border: "1px solid #bae6fd", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>
                <EditIcon style={{ fontSize: "0.85rem" }} /> Edit Time
              </button>
              <button type="button" onClick={onCancel} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", padding: "0.45rem 0.8rem", borderRadius: "6px", backgroundColor: "#ffffff", color: "#dc2626", border: "1px solid #fecaca", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>
                <CancelIcon style={{ fontSize: "0.85rem" }} /> Cancel
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", gap: "0.45rem", flexWrap: "wrap", marginTop: "0.35rem" }}>
              <button type="button" onClick={onConfirm} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", padding: "0.45rem 0.85rem", borderRadius: "6px", backgroundColor: "#16a34a", color: "#ffffff", border: "none", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer", boxShadow: "0 1px 2px rgba(22,163,74,0.2)" }}>
                <CheckIcon style={{ fontSize: "0.85rem" }} /> Confirm & Schedule (అవును)
              </button>
              <button type="button" onClick={() => setIsEditing(true)} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", padding: "0.45rem 0.8rem", borderRadius: "6px", backgroundColor: "#ffffff", color: "#0369a1", border: "1px solid #bae6fd", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>
                <EditIcon style={{ fontSize: "0.85rem" }} /> Edit
              </button>
              <button type="button" onClick={onCancel} style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem", padding: "0.45rem 0.8rem", borderRadius: "6px", backgroundColor: "#ffffff", color: "#dc2626", border: "1px solid #fecaca", fontSize: "0.75rem", fontWeight: 600, cursor: "pointer" }}>
                <CancelIcon style={{ fontSize: "0.85rem" }} /> Cancel (వద్దు)
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function NextActionCard({ data, onActionClick }) {
  if (!data || !data.next_action) return null;
  const { next_action } = data;
  const {
    priority_level = "normal",
    headline,
    explanation,
    action_items = [],
  } = next_action;

  const isUrgent = priority_level === "urgent";
  const isHigh = priority_level === "high";

  return (
    <div
      style={{
        marginTop: "0.6rem",
        padding: "0.85rem 1rem",
        borderRadius: "12px",
        backgroundColor: isUrgent ? "#fff5f5" : "#f8fafc",
        border: `1px solid ${isUrgent ? "#fecaca" : isHigh ? "#fed7aa" : "#e2e8f0"}`,
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        maxWidth: "100%",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>
          Next Recommended Action
        </span>
        <span
          style={{
            fontSize: "0.68rem",
            fontWeight: 700,
            padding: "0.15rem 0.5rem",
            borderRadius: "9999px",
            backgroundColor: isUrgent ? "#fee2e2" : isHigh ? "#ffedd5" : "#e0f2fe",
            color: isUrgent ? "#b91c1c" : isHigh ? "#c2410c" : "#0369a1",
          }}
        >
          {isUrgent ? "🔴 Urgent" : isHigh ? "🟠 High Priority" : "🟢 Normal Priority"}
        </span>
      </div>

      <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "#0f172a", lineHeight: 1.4 }}>
        {headline}
      </div>

      <p style={{ fontSize: "0.775rem", color: "#475569", lineHeight: 1.5, margin: 0 }}>
        {explanation}
      </p>

      {action_items.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem", marginTop: "0.2rem" }}>
          <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "#334155" }}>Action Checklist:</span>
          {action_items.map((item, idx) => (
            <div
              key={idx}
              style={{
                fontSize: "0.75rem",
                color: "#1e293b",
                backgroundColor: "#ffffff",
                padding: "0.35rem 0.55rem",
                borderRadius: "6px",
                border: "1px solid #e2e8f0",
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
              }}
            >
              <TaskIcon style={{ fontSize: "0.85rem", color: isUrgent ? "#dc2626" : "#0284c7" }} />
              <span>{item}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
