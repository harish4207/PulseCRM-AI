import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  AutoAwesome as AiIcon,
  LocalHospital as HospitalIcon,
  Person as DoctorIcon,
  Event as CalendarIcon,
  Medication as MedicineIcon,
  Notes as NotesIcon,
  CheckCircle as CheckIcon,
  Schedule as ScheduleIcon,
  Refresh as RefreshIcon,
  ArrowForward as ArrowForwardIcon,
  Mic as MicIcon,
  Stop as StopIcon,
  PersonAdd as NewHcpIcon,
  LocationOn as LocationIcon,
  MedicalServices as SpecialtyIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";
import aiService from "../../services/aiService";

const SAMPLE_TRANSCRIPTS = [
  {
    title: "Cardiology Detailing (Existing HCP)",
    tag: "Dr Sharma (Existing)",
    text: "Met Dr Sharma at Apollo Hospital Mumbai this morning. Discussed Cardiopress-50 and LipiGuard for hypertensive patients. Dr. Sharma noted good efficacy with Cardiopress-50 and requested a follow-up meeting on 2026-09-15T10:00:00 to review phase-4 trial safety endpoints.",
  },
  {
    title: "Oncology Visit (New HCP)",
    tag: "Dr Rajesh (New HCP)",
    text: "Today I met Dr Rajesh at Apollo Hospital in Visakhapatnam. We discussed CardioPress-50 for hypertension patients. He was interested and asked me to send the clinical information. We agreed to meet again on 2026-09-22T14:30:00.",
  },
  {
    title: "Endocrinology Note (New HCP)",
    tag: "Dr Ananya (New HCP)",
    text: "Conducted detailing session with Dr Ananya at Tata Memorial Hospital Mumbai. Presented clinical efficacy data for OncoShield-XL in solid tumor protocols. Agreed on follow-up on 2026-10-05T11:00:00.",
  },
];

const PIPELINE_STEPS = [
  "Extracting doctor, hospital, and products",
  "Validating clinical dates & ISO compliance",
  "Resolving or creating HCP entity in territory database",
  "Preparing and logging CRM interaction record",
];

export function LogMeeting() {
  const navigate = useNavigate();
  const [meetingText, setMeetingText] = useState("");

  // Pipeline states: 'idle' | 'processing' | 'extracted' | 'error'
  const [pipelineState, setPipelineState] = useState("idle");
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [extractedData, setExtractedData] = useState(null);
  const [saveResult, setSaveResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  // Voice recording state
  const [isRecording, setIsRecording] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [voiceError, setVoiceError] = useState("");

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerIntervalRef = useRef(null);
  const lastAudioBlobRef = useRef(null);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  const startRecording = async () => {
    setVoiceError("");

    if (isRecording) return;
    if (isTranscribing || pipelineState === "processing") {
      setVoiceError("Cannot start a new recording while transcription or AI processing is in progress.");
      return;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setVoiceError("Your browser does not support microphone capture.");
      return;
    }

    if (typeof MediaRecorder === "undefined") {
      setVoiceError("Audio recording is not supported by this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      const audioTracks = stream ? stream.getAudioTracks() : [];
      if (!audioTracks || audioTracks.length === 0) {
        setVoiceError("No active audio track found on microphone.");
        return;
      }
      const activeTrack = audioTracks[0];
      if (!activeTrack || activeTrack.readyState !== "live" || !activeTrack.enabled) {
        setVoiceError("Microphone stream is not active or disabled.");
        return;
      }

      audioChunksRef.current = [];
      lastAudioBlobRef.current = null;

      const preferredMimeTypes = [
        "audio/webm;codecs=opus",
        "audio/webm",
        "audio/mp4",
        "audio/ogg;codecs=opus",
        "audio/wav",
      ];

      let selectedMimeType = "";
      for (const type of preferredMimeTypes) {
        if (MediaRecorder.isTypeSupported(type)) {
          selectedMimeType = type;
          break;
        }
      }

      const recorderOptions = selectedMimeType ? { mimeType: selectedMimeType } : {};
      const recorder = new MediaRecorder(stream, recorderOptions);
      mediaRecorderRef.current = recorder;

      const actualMimeType = recorder.mimeType || selectedMimeType || "audio/webm";

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = async () => {
        // Stop all audio tracks to release microphone
        try {
          stream.getTracks().forEach((track) => track.stop());
        } catch (e) {
          // ignore
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: actualMimeType });
        lastAudioBlobRef.current = audioBlob;

        console.log("Audio recording metadata:", {
          mimeType: audioBlob.type,
          size: audioBlob.size,
          chunksCount: audioChunksRef.current.length,
        });

        if (audioChunksRef.current.length === 0 || audioBlob.size < 100) {
          setVoiceError("No usable audio was recorded. Please try recording again.");
          return;
        }

        setIsTranscribing(true);
        try {
          const resp = await aiService.transcribeAudio(audioBlob);
          if (resp && resp.transcript) {
            setMeetingText((prev) => (prev ? `${prev}\n${resp.transcript}` : resp.transcript));
            setVoiceError("");
          } else {
            setVoiceError("No speech recognized. Please try again or type directly.");
          }
        } catch (err) {
          console.error("Transcription error:", err);
          const friendly = err?.response?.data?.detail || err?.userMessage || "No usable audio was recorded. Please try recording again.";
          setVoiceError(friendly);
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start(250);
      setIsRecording(true);
      setRecordingSeconds(0);

      timerIntervalRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.error("Microphone access error:", err);
      if (err && err.name) {
        switch (err.name) {
          case "NotAllowedError":
          case "SecurityError":
            setVoiceError("Microphone access was denied. Please allow microphone use in your browser settings.");
            break;
          case "NotFoundError":
          case "DevicesNotFoundError":
            setVoiceError("No microphone was found. Please connect a microphone and try again.");
            break;
          case "NotReadableError":
            setVoiceError("Microphone is not available. Another application may be using it.");
            break;
          default:
            setVoiceError("Microphone access denied or not available in this browser.");
        }
      } else {
        setVoiceError("Microphone access denied or not available in this browser.");
      }
    }
  };

  const stopRecording = () => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  const retryTranscription = async () => {
    if (!lastAudioBlobRef.current) return;
    setVoiceError("");
    setIsTranscribing(true);
    try {
      const resp = await aiService.transcribeAudio(lastAudioBlobRef.current);
      if (resp && resp.transcript) {
        setMeetingText((prev) => (prev ? `${prev}\n${resp.transcript}` : resp.transcript));
        setVoiceError("");
      } else {
        setVoiceError("No speech recognized. Please try again or type notes manually.");
      }
    } catch (err) {
      console.error("Retry transcription error:", err);
      setVoiceError(err?.response?.data?.detail || "Retry failed. You can try again or type notes manually.");
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleSelectSample = (sample) => {
    setMeetingText(sample.text);
    setPipelineState("idle");
    setExtractedData(null);
    setSaveResult(null);
    setErrorMessage("");
    setVoiceError("");
  };

  const handleExtract = async () => {
    if (!meetingText.trim()) {
      setErrorMessage("Please enter, record, or paste meeting notes before extracting.");
      return;
    }

    setPipelineState("processing");
    setCurrentStepIndex(-1); // will show pending stages until backend responds
    setErrorMessage("");
    setVoiceError("");

    try {
      const response = await aiService.logMeeting(meetingText);

      if (response && response.success) {
        setSaveResult(response);
        setExtractedData(response.extraction || {});
        // mark all steps complete visually
        setCurrentStepIndex(PIPELINE_STEPS.length);
        setPipelineState("extracted");
      } else {
        setErrorMessage(response?.message || "Failed to process meeting notes.");
        setPipelineState("error");
      }
    } catch (err) {
      console.error("AI meeting error:", err);
      setErrorMessage(
        err?.response?.data?.detail ||
        err?.message ||
        "Could not process meeting notes. Please check your notes and try again."
      );
      setPipelineState("error");
    }
  };

  const handleReset = () => {
    setMeetingText("");
    setPipelineState("idle");
    setExtractedData(null);
    setSaveResult(null);
    setErrorMessage("");
    setVoiceError("");
  };

  const formatSeconds = (sec) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return "No follow-up requested";
    try {
      return new Intl.DateTimeFormat("en-US", {
        weekday: "short",
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      }).format(new Date(isoStr));
    } catch {
      return isoStr;
    }
  };

  return (
    <AppShell title="AI Meeting Intelligence">
      <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem", maxWidth: "1000px", margin: "0 auto" }}>
        <PageHeader
          tag="Agentic CRM Pipeline"
          title="Log Meeting with AI"
          description="Dictate voice notes or type field transcripts to automatically extract HCP commitments, register new doctors, and schedule follow-ups."
          actions={
            pipelineState !== "idle" && (
              <button
                type="button"
                onClick={handleReset}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  padding: "0.55rem 0.9rem",
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  backgroundColor: "#ffffff",
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  color: "#475569",
                }}
              >
                <RefreshIcon style={{ fontSize: "1rem" }} />
                <span>New Meeting Note</span>
              </button>
            )
          }
        />

        {/* STEP 1: Meeting Input Canvas (Voice & Text) */}
        <div className="pulse-card" style={{ padding: "1.5rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem", flexWrap: "wrap", gap: "0.5rem" }}>
            <label style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>
              Field Notes / Voice Transcript
            </label>

            {/* Sample Prompts */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: 600 }}>
                Try sample:
              </span>
              {SAMPLE_TRANSCRIPTS.map((sample, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelectSample(sample)}
                  style={{
                    fontSize: "0.72rem",
                    fontWeight: 600,
                    padding: "0.25rem 0.6rem",
                    borderRadius: "9999px",
                    border: "1px solid #bae6fd",
                    backgroundColor: "#f0f9ff",
                    color: "#0284c7",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#e0f2fe")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "#f0f9ff")}
                >
                  {sample.tag}
                </button>
              ))}
            </div>
          </div>

          <textarea
            rows={5}
            placeholder="Dictate using microphone or paste notes... (e.g., 'Today I met Dr Rajesh at Apollo Hospital in Visakhapatnam. We discussed CardioPress-50 for hypertension patients. He asked for clinical information...')"
            value={meetingText}
            onChange={(e) => setMeetingText(e.target.value)}
            disabled={pipelineState === "processing" || isRecording}
            style={{
              width: "100%",
              padding: "0.85rem 1rem",
              borderRadius: "12px",
              border: "1px solid #cbd5e1",
              backgroundColor: isRecording ? "#fff5f5" : "#f8fafc",
              fontSize: "0.9rem",
              color: "#0f172a",
              lineHeight: 1.6,
              resize: "vertical",
            }}
          />

          {/* Transcription Banner */}
          {isTranscribing && (
            <div
              style={{
                marginTop: "0.75rem",
                padding: "0.65rem 0.85rem",
                borderRadius: "8px",
                backgroundColor: "#eef2ff",
                border: "1px solid #c7d2fe",
                color: "#3730a3",
                fontSize: "0.9rem",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "0.6rem",
              }}
            >
              <div style={{ width: 12, height: 12, borderRadius: 6, backgroundColor: "#6366f1", animation: "pulse 1.2s infinite" }} />
              <span>Transcribing your meeting... Please wait.</span>
            </div>
          )}

          {voiceError && (
            <div
              style={{
                marginTop: "0.75rem",
                padding: "0.55rem 0.85rem",
                borderRadius: "8px",
                backgroundColor: "#fffbeb",
                border: "1px solid #fde68a",
                color: "#b45309",
                fontSize: "0.8125rem",
              }}
            >
              {voiceError}
            </div>
          )}

          {errorMessage && (
            <div
              style={{
                marginTop: "0.75rem",
                padding: "0.65rem 0.85rem",
                borderRadius: "8px",
                backgroundColor: "#fef2f2",
                border: "1px solid #fecaca",
                color: "#dc2626",
                fontSize: "0.8125rem",
              }}
            >
              {errorMessage}
            </div>
          )}

          {/* Action Row: Voice Recording button on Left, Extract Action on Right */}
          <div
            style={{
              marginTop: "1rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "0.75rem",
            }}
          >
            {/* Voice controls */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              {!isRecording ? (
                <button
                  type="button"
                  onClick={startRecording}
                  disabled={isTranscribing || pipelineState === "processing"}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.4rem",
                    padding: "0.65rem 1rem",
                    borderRadius: "10px",
                    backgroundColor: isTranscribing ? "#f1f5f9" : "#ffffff",
                    border: "1px solid #cbd5e1",
                    color: isTranscribing ? "#94a3b8" : "#334155",
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                  }}
                >
                  <MicIcon style={{ fontSize: "1.15rem", color: "#0284c7" }} />
                  <span>Start Recording</span>
                </button>
              ) : (
                <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                  <button
                    type="button"
                    onClick={stopRecording}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.4rem",
                      padding: "0.65rem 1.1rem",
                      borderRadius: "10px",
                      backgroundColor: "#dc2626",
                      color: "#ffffff",
                      fontSize: "0.8125rem",
                      fontWeight: 600,
                      boxShadow: "0 2px 6px rgba(220, 38, 38, 0.25)",
                    }}
                  >
                    <StopIcon style={{ fontSize: "1.15rem" }} />
                    <span>Stop Recording ({formatSeconds(recordingSeconds)})</span>
                  </button>
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: "50%",
                      backgroundColor: "#dc2626",
                      animation: "pulse 1.2s infinite",
                    }}
                  />
                </div>
              )}

              {/* Retry button when previous recording exists and transcription not active */}
              {lastAudioBlobRef.current && !isTranscribing && (
                <button
                  type="button"
                  onClick={retryTranscription}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.4rem",
                    padding: "0.55rem 0.9rem",
                    borderRadius: "8px",
                    backgroundColor: "#fff7ed",
                    border: "1px solid #fde68a",
                    color: "#92400e",
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                  }}
                >
                  <RefreshIcon style={{ fontSize: "1rem" }} />
                  <span>Retry Transcription</span>
                </button>
              )}
            </div>

            {/* Extract Button */}
            <button
              type="button"
              onClick={handleExtract}
              disabled={pipelineState === "processing" || isRecording || isTranscribing || !meetingText.trim()}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.75rem 1.5rem",
                borderRadius: "10px",
                backgroundColor:
                  !meetingText.trim() || pipelineState === "processing" || isRecording || isTranscribing
                    ? "#94a3b8"
                    : "#0284c7",
                color: "#ffffff",
                fontSize: "0.875rem",
                fontWeight: 600,
                boxShadow: "0 2px 6px rgba(2, 132, 199, 0.25)",
                cursor:
                  !meetingText.trim() || pipelineState === "processing" || isRecording || isTranscribing
                    ? "not-allowed"
                    : "pointer",
              }}
            >
              <AiIcon style={{ fontSize: "1.2rem" }} />
              <span>
                {pipelineState === "processing" ? "Analyzing Intelligence..." : "Extract Meeting Intelligence"}
              </span>
            </button>
          </div>
        </div>

        {/* STEP 2: Processing Progress State */}
        {pipelineState === "processing" && (
          <div
            className="pulse-card"
            style={{
              padding: "1.5rem",
              backgroundColor: "#f0f9ff",
              borderColor: "#bae6fd",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
              <div
                style={{
                  width: 28,
                  height: 28,
                  border: "3px solid #bae6fd",
                  borderTopColor: "#0284c7",
                  borderRadius: "50%",
                  animation: "spin 0.8s linear infinite",
                }}
              />
              <span style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0369a1" }}>
                AI Relationship Engine Processing
              </span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {PIPELINE_STEPS.map((step, idx) => {
                const isDone = idx < currentStepIndex;
                const isCurrent = idx === currentStepIndex;

                return (
                  <div
                    key={idx}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "0.6rem",
                      fontSize: "0.8125rem",
                      color: isDone ? "#059669" : isCurrent ? "#0284c7" : "#94a3b8",
                      fontWeight: isCurrent || isDone ? 600 : 400,
                    }}
                  >
                    {isDone ? (
                      <CheckIcon style={{ fontSize: "1.1rem" }} />
                    ) : (
                      <span
                        style={{
                          width: 8,
                          height: 8,
                          borderRadius: "50%",
                          backgroundColor: isCurrent ? "#0284c7" : "#cbd5e1",
                        }}
                      />
                    )}
                    <span>{step}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* STEP 3 & 4: Extracted Intelligence Review & HCP Resolution */}
        {pipelineState === "extracted" && extractedData && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
            {/* Header banner showing status */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "0.85rem 1.25rem",
                borderRadius: "12px",
                backgroundColor: saveResult?.is_new_hcp ? "#fffbeb" : "#ecfdf5",
                border: `1px solid ${saveResult?.is_new_hcp ? "#fde68a" : "#a7f3d0"}`,
                flexWrap: "wrap",
                gap: "0.5rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                {saveResult?.is_new_hcp ? (
                  <NewHcpIcon style={{ color: "#d97706", fontSize: "1.35rem" }} />
                ) : (
                  <CheckIcon style={{ color: "#059669", fontSize: "1.25rem" }} />
                )}
                <span
                  style={{
                    fontSize: "0.875rem",
                    fontWeight: 700,
                    color: saveResult?.is_new_hcp ? "#92400e" : "#065f46",
                  }}
                >
                  {saveResult?.is_new_hcp
                    ? "✨ New Healthcare Professional Detected & Automatically Registered"
                    : "Interaction Successfully Processed & Linked to Existing HCP"}
                </span>
              </div>
              <StatusBadge variant={saveResult?.is_new_hcp ? "scheduled" : "teal"} size="sm">
                {saveResult?.is_new_hcp ? "New HCP Added" : "Matched HCP"}
              </StatusBadge>
            </div>

            {/* Extracted Data Grid */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "1rem",
              }}
            >
              {/* Doctor Card */}
              <div className="pulse-card" style={{ padding: "1.25rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#64748b", marginBottom: "0.5rem" }}>
                  <DoctorIcon style={{ fontSize: "1.15rem", color: "#0284c7" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase" }}>Doctor Identified</span>
                </div>
                <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#0f172a" }}>
                  {extractedData.doctor_name || "Unknown Doctor"}
                </div>
                <div style={{ marginTop: "0.4rem", fontSize: "0.85rem", color: "#475569" }}>
                  Specialization: {extractedData.specialization || "Not provided"}
                </div>
                <div style={{ marginTop: "0.25rem", fontSize: "0.85rem", color: "#475569" }}>
                  Phone: {extractedData.phone || "Not provided"}
                </div>
                <div style={{ marginTop: "0.25rem", fontSize: "0.85rem", color: "#475569" }}>
                  Email: {extractedData.email || "Not provided"}
                </div>
                {saveResult?.is_new_hcp && (
                  <div style={{ marginTop: "0.35rem", fontSize: "0.75rem", color: "#d97706", fontWeight: 600 }}>
                    Newly created HCP ID #{saveResult?.doctor_id}
                  </div>
                )}
              </div>

              {/* Hospital & City Card */}
              <div className="pulse-card" style={{ padding: "1.25rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#64748b", marginBottom: "0.5rem" }}>
                  <HospitalIcon style={{ fontSize: "1.15rem", color: "#0d9488" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase" }}>Hospital & Location</span>
                </div>
                <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a" }}>
                  {extractedData.hospital || "Not Specified"}
                </div>
                {extractedData.city && (
                  <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", marginTop: "0.25rem", fontSize: "0.75rem", color: "#64748b" }}>
                    <LocationIcon style={{ fontSize: "0.9rem", color: "#0d9488" }} />
                    <span>{extractedData.city}</span>
                  </div>
                )}
              </div>

              {/* Products Discussed Card */}
              <div className="pulse-card" style={{ padding: "1.25rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#64748b", marginBottom: "0.5rem" }}>
                  <MedicineIcon style={{ fontSize: "1.15rem", color: "#2563eb" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase" }}>Products Discussed</span>
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginTop: "0.25rem" }}>
                  {extractedData.products_discussed ? (
                    extractedData.products_discussed.split(",").map((p, i) => (
                      <StatusBadge key={i} variant="product" size="sm" withDot={false}>
                        {p.trim()}
                      </StatusBadge>
                    ))
                  ) : (
                    <span style={{ color: "#94a3b8", fontSize: "0.875rem" }}>None listed</span>
                  )}
                </div>
              </div>

              {/* Follow-up Date Card */}
              <div className="pulse-card" style={{ padding: "1.25rem" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#64748b", marginBottom: "0.5rem" }}>
                  <CalendarIcon style={{ fontSize: "1.15rem", color: "#d97706" }} />
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase" }}>Follow-up Scheduled</span>
                </div>
                <div style={{ fontSize: "0.95rem", fontWeight: 600, color: extractedData.follow_up_date ? "#92400e" : "#64748b" }}>
                  {formatDate(extractedData.follow_up_date)}
                </div>
              </div>
            </div>

            {/* Meeting Summary Card */}
            <div className="pulse-card" style={{ padding: "1.25rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#64748b", marginBottom: "0.5rem" }}>
                <NotesIcon style={{ fontSize: "1.15rem", color: "#0284c7" }} />
                <span style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase" }}>Structured Meeting Summary</span>
              </div>
              <p style={{ fontSize: "0.875rem", color: "#334155", lineHeight: 1.6 }}>
                {extractedData.meeting_summary || "No summary provided."}
              </p>
            </div>

            {/* Resolution Actions */}
            <div
              className="pulse-card"
              style={{
                padding: "1.5rem",
                backgroundColor: "#f8fafc",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "1rem",
              }}
            >
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a" }}>
                  {saveResult?.message || "Interaction saved in Relationship CRM"}
                </div>
                <div style={{ fontSize: "0.8125rem", color: "#64748b", marginTop: "2px" }}>
                  Interaction ID #{saveResult?.interaction_id} linked to Doctor ID #{saveResult?.doctor_id}
                </div>
              </div>

              <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
                {saveResult?.is_new_hcp && (
                  <button
                    type="button"
                    onClick={() => navigate("/hcps")}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "0.4rem",
                      padding: "0.65rem 1rem",
                      borderRadius: "8px",
                      backgroundColor: "#ffffff",
                      border: "1px solid #cbd5e1",
                      color: "#334155",
                      fontSize: "0.875rem",
                      fontWeight: 600,
                    }}
                  >
                    <span>View in HCP Directory</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={() => navigate("/interactions")}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.4rem",
                    padding: "0.65rem 1.25rem",
                    borderRadius: "8px",
                    backgroundColor: "#0284c7",
                    color: "#ffffff",
                    fontSize: "0.875rem",
                    fontWeight: 600,
                  }}
                >
                  <span>View in Interactions Log</span>
                  <ArrowForwardIcon style={{ fontSize: "1rem" }} />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default LogMeeting;
