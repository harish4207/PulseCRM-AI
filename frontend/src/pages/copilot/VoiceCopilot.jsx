import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  Mic as MicIcon,
  Stop as StopIcon,
  GraphicEq as WaveIcon,
  Person as PersonIcon,
  SmartToy as BotIcon,
  VolumeUp as SpeakIcon,
  VolumeOff as MuteIcon,
  Send as SendIcon,
  KeyboardArrowDown as ScrollDownIcon,
  AutoAwesome as SparkleIcon,
  Add as AddIcon,
  Check as CheckIcon,
  ContentCopy as CopyIcon,
} from "@mui/icons-material";

import AppShell from "../../components/dashboard/AppShell";
import aiService from "../../services/aiService";
import { useCopilot } from "../../context/CopilotContext";
import {
  speakResponse,
  cancelSpeech,
  findTeluguVoice,
  detectResponseLanguage,
} from "../../utils/speechUtils";
import {
  HcpCard,
  FollowupsListCard,
  InteractionCard,
  ConfirmationActionCard,
  MeetingCaptureCard,
  AmbiguityCard,
  CrmBriefCard,
  PreMeetingIntelligenceCard,
  AnalyticsCard,
  MeetingScheduleCard,
  NextActionCard,
} from "../../components/copilot/CopilotCards";

const S = {
  IDLE: "idle",
  LISTENING: "listening",
  TRANSCRIBING: "transcribing",
  THINKING: "thinking",
  RESPONDED: "responded",
  SPEAKING: "speaking",
};

function formatSeconds(s) {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

const ttsSupportedInBrowser =
  typeof window !== "undefined" && "speechSynthesis" in window;

const SUGGESTED_PROMPTS = [
  { label: "What should I do next?", query: "What should I do next?", icon: "🎯" },
  { label: "Schedule Meeting", query: "Meet Dr Rajesh Friday at 3 PM", icon: "🗓️" },
  { label: "My Day Briefing", query: "What do I have today?", icon: "☀️" },
  { label: "Dr. Rajesh Profile", query: "Tell me about Dr Rajesh", icon: "👨‍⚕️" },
  { label: "Pre-Meeting Prep", query: "I'm meeting Dr Priyanka today. What should I know?", icon: "💡" },
  { label: "New HCP & Meeting", query: "I met a new doctor Dr Sheila at Apollo Hospital. Her phone is 94326891. Schedule a meeting next Tuesday at 11.", icon: "✍️" },
];

function ChatBubble({
  message,
  index,
  isSpeaking,
  onSpeak,
  isTeluguVoiceAvailable,
  onConfirmAction,
  onCancelAction,
  onSelectCandidate,
  onUpdateMeeting,
  onQuickQuery,
}) {
  const { role, content, intent, language, cardData, input_mode } = message;
  const isUser = role === "user";
  const detectedLang = !isUser ? detectResponseLanguage(content) : language;
  const isTeluguContent =
    detectedLang === "te" || language === "te" || language === "mixed";

  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (content) {
      navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: isUser ? "row-reverse" : "row",
        alignItems: "flex-start",
        gap: "0.5rem",
        maxWidth: "100%",
        marginBottom: "0.45rem",
      }}
    >
      {/* Avatar */}
      <div
        style={{
          width: 30,
          height: 30,
          borderRadius: "50%",
          backgroundColor: isUser ? "#0284c7" : "#0f172a",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          boxShadow: isUser ? "0 2px 4px rgba(2,132,199,0.2)" : "0 2px 4px rgba(15,23,42,0.15)",
        }}
      >
        {isUser ? (
          <PersonIcon style={{ fontSize: "0.95rem", color: "#ffffff" }} />
        ) : (
          <BotIcon style={{ fontSize: "0.95rem", color: "#38bdf8" }} />
        )}
      </div>

      {/* Bubble Container */}
      <div style={{ maxWidth: isUser ? "82%" : "92%", minWidth: "160px", display: "flex", flexDirection: "column", gap: "0.2rem" }}>
        <div
          style={{
            padding: "0.75rem 1rem",
            borderRadius: isUser
              ? "16px 4px 16px 16px"
              : "4px 16px 16px 16px",
            backgroundColor: isUser ? "#0284c7" : "#ffffff",
            border: isUser ? "none" : "1px solid #e2e8f0",
            boxShadow: isSpeaking
              ? "0 0 0 2px #0284c7"
              : "0 1px 3px rgba(15,23,42,0.05)",
            transition: "all 0.2s ease",
          }}
        >
          {content && (
            <p
              style={{
                fontSize: "0.9rem",
                lineHeight: 1.55,
                color: isUser ? "#ffffff" : "#0f172a",
                margin: 0,
                wordBreak: "break-word",
                whiteSpace: "pre-wrap",
              }}
            >
              {content}
            </p>
          )}

          {!isUser && cardData && (
            <>
              {cardData.type === "hcp_card" && <HcpCard data={cardData} />}
              {cardData.type === "followups_list_card" && <FollowupsListCard data={cardData} />}
              {cardData.type === "interaction_card" && <InteractionCard data={cardData} />}
              {cardData.type === "crm_brief_card" && <CrmBriefCard data={cardData} onQuickQuery={onQuickQuery} />}
              {cardData.type === "pre_meeting_intelligence_card" && <PreMeetingIntelligenceCard data={cardData} />}
              {cardData.type === "analytics_card" && <AnalyticsCard data={cardData} />}
              {cardData.type === "confirmation_action" && (
                <ConfirmationActionCard
                  data={cardData}
                  onConfirm={onConfirmAction}
                  onCancel={onCancelAction}
                />
              )}
              {cardData.type === "meeting_capture_confirmation" && (
                <MeetingCaptureCard
                  data={cardData}
                  onConfirm={onConfirmAction}
                  onCancel={onCancelAction}
                  onUpdateMeeting={onUpdateMeeting}
                />
              )}
              {(cardData.type === "meeting_schedule_confirmation" || cardData.type === "meeting_schedule_card") && (
                <MeetingScheduleCard
                  data={cardData}
                  onConfirm={onConfirmAction}
                  onCancel={onCancelAction}
                  onUpdateMeeting={onUpdateMeeting}
                />
              )}
              {cardData.type === "next_action_card" && (
                <NextActionCard
                  data={cardData}
                  onActionClick={onQuickQuery}
                />
              )}
              {cardData.type === "ambiguity_card" && (
                <AmbiguityCard
                  data={cardData}
                  onSelectCandidate={onSelectCandidate}
                />
              )}
            </>
          )}
        </div>

        {/* Action / Meta row */}
        <div
          style={{
            display: "flex",
            gap: "0.4rem",
            flexWrap: "wrap",
            marginTop: "0.15rem",
            alignItems: "center",
            justifyContent: isUser ? "flex-end" : "flex-start",
          }}
        >
          {isUser && input_mode === "voice" && (
            <span
              style={{
                fontSize: "0.68rem",
                fontWeight: 600,
                color: "#64748b",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.2rem",
              }}
            >
              <MicIcon style={{ fontSize: "0.75rem" }} /> Spoken
            </span>
          )}

          {!isUser && (
            <>
              {ttsSupportedInBrowser && onSpeak && (
                <button
                  type="button"
                  onClick={onSpeak}
                  title={
                    isSpeaking
                      ? "Stop speaking"
                      : isTeluguContent && !isTeluguVoiceAvailable
                      ? "Telugu voice not available in browser/OS"
                      : "Listen to response"
                  }
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.2rem",
                    fontSize: "0.7rem",
                    fontWeight: 600,
                    padding: "0.15rem 0.45rem",
                    borderRadius: "9999px",
                    border: "1px solid #e2e8f0",
                    backgroundColor: isSpeaking ? "#dbeafe" : "#f8fafc",
                    color: isSpeaking ? "#1d4ed8" : "#475569",
                    cursor: "pointer",
                  }}
                  aria-label={isSpeaking ? "Stop speaking" : "Listen to response"}
                >
                  {isSpeaking ? (
                    <>
                      <MuteIcon style={{ fontSize: "0.75rem" }} /> Stop
                    </>
                  ) : (
                    <>
                      <SpeakIcon style={{ fontSize: "0.75rem" }} /> Replay
                    </>
                  )}
                </button>
              )}

              <button
                type="button"
                onClick={handleCopy}
                title="Copy response"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.2rem",
                  fontSize: "0.7rem",
                  fontWeight: 500,
                  padding: "0.15rem 0.45rem",
                  borderRadius: "9999px",
                  border: "1px solid #e2e8f0",
                  backgroundColor: "#f8fafc",
                  color: copied ? "#16a34a" : "#64748b",
                  cursor: "pointer",
                }}
                aria-label="Copy assistant response"
              >
                {copied ? <CheckIcon style={{ fontSize: "0.75rem" }} /> : <CopyIcon style={{ fontSize: "0.75rem" }} />}
                {copied ? "Copied" : "Copy"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function ThinkingIndicator({ step }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.6rem",
        padding: "0.55rem 0.9rem",
        borderRadius: "10px",
        backgroundColor: "#f0f9ff",
        border: "1px solid #bae6fd",
        maxWidth: "fit-content",
        marginBottom: "0.45rem",
      }}
    >
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: "#0284c7",
          animation: "pulse 1.2s infinite",
        }}
      />
      <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#0369a1" }}>
        {step || "Checking CRM database..."}
      </span>
    </div>
  );
}

export function VoiceCopilot() {
  const {
    conversationId,
    chatHistory,
    selectedHcpId,
    selectedHcpName,
    pendingConfirmation,
    pendingAction,
    readAloudEnabled,
    setReadAloudEnabled,
    ttsNotificationDismissed,
    setTtsNotificationDismissed,
    uiState,
    setUiState,
    thinkingStep,
    error,
    setError,
    speakingMsgIndex,
    setSpeakingMsgIndex,
    sendQuery,
    confirmPendingAction,
    cancelPendingAction,
    updatePendingAction,
    selectAmbiguityCandidate,
    clearHcpContext,
    resetConversation,
  } = useCopilot();

  const [inputText, setInputText] = useState("");
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [voices, setVoices] = useState([]);
  const [isTeluguVoiceAvailable, setIsTeluguVoiceAvailable] = useState(false);
  const [showScrollDown, setShowScrollDown] = useState(false);
  const [showUnsavedModal, setShowUnsavedModal] = useState(false);

  const chatContainerRef = useRef(null);
  const chatBottomRef = useRef(null);
  const textareaRef = useRef(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  const scrollToBottom = (behavior = "smooth") => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior });
    }
  };

  useEffect(() => {
    if (!showScrollDown) {
      scrollToBottom();
    }
  }, [chatHistory, uiState, showScrollDown]);

  const handleScroll = () => {
    if (!chatContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
    const isUp = scrollHeight - scrollTop - clientHeight > 100;
    setShowScrollDown(isUp);
  };

  useEffect(() => {
    if (!ttsSupportedInBrowser) return;

    const loadVoices = () => {
      const available = window.speechSynthesis.getVoices() || [];
      setVoices(available);
      const teluguVoice = findTeluguVoice(available);
      setIsTeluguVoiceAvailable(!!teluguVoice);
    };

    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;

    return () => {
      if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = null;
        cancelSpeech();
      }
    };
  }, []);

  const handleSpeak = useCallback(
    (text, language, msgIndex) => {
      cancelSpeech();

      if (!text) return;

      const res = speakResponse({
        text,
        language,
        voices,
        onStart: () => {
          setSpeakingMsgIndex(msgIndex);
          setUiState(S.SPEAKING);
        },
        onEnd: () => {
          setSpeakingMsgIndex(null);
          setUiState((prev) => (prev === S.SPEAKING ? S.RESPONDED : prev));
        },
        onError: (err) => {
          console.warn("[VoiceCopilot] TTS playback error:", err);
          setSpeakingMsgIndex(null);
          setUiState((prev) => (prev === S.SPEAKING ? S.RESPONDED : prev));
        },
        onNoVoice: ({ reason }) => {
          setSpeakingMsgIndex(null);
          setUiState((prev) => (prev === S.SPEAKING ? S.RESPONDED : prev));
        },
      });
    },
    [voices, setSpeakingMsgIndex, setUiState]
  );

  const handleStopSpeaking = useCallback(() => {
    cancelSpeech();
    setSpeakingMsgIndex(null);
    setUiState(S.RESPONDED);
  }, [setSpeakingMsgIndex, setUiState]);

  const handleNewConversationClick = () => {
    if (pendingConfirmation) {
      setShowUnsavedModal(true);
    } else {
      resetConversation(true);
    }
  };

  const handleTextareaChange = (e) => {
    setInputText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (inputText.trim() && uiState !== S.THINKING && uiState !== S.TRANSCRIBING) {
        const text = inputText;
        setInputText("");
        if (textareaRef.current) textareaRef.current.style.height = "auto";
        sendQuery(text, "text", (t, l, idx) => {
          if (readAloudEnabled) handleSpeak(t, l, idx);
        });
      }
    }
  };

  const handleSendClick = () => {
    if (inputText.trim() && uiState !== S.THINKING && uiState !== S.TRANSCRIBING) {
      const text = inputText;
      setInputText("");
      if (textareaRef.current) textareaRef.current.style.height = "auto";
      sendQuery(text, "text", (t, l, idx) => {
        if (readAloudEnabled) handleSpeak(t, l, idx);
      });
    }
  };

  const startRecording = useCallback(async () => {
    setError(null);
    cancelSpeech();
    setSpeakingMsgIndex(null);

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      console.warn("Microphone access denied:", e);
      setError("Microphone permission denied. Please allow microphone access.");
      setUiState(S.IDLE);
      return;
    }

    const mimeTypes = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/mp4",
      "audio/wav",
      "audio/ogg;codecs=opus",
      "",
    ];
    let selectedMime = "";
    for (const m of mimeTypes) {
      if (m === "" || (window.MediaRecorder && MediaRecorder.isTypeSupported(m))) {
        selectedMime = m;
        break;
      }
    }

    let recorder;
    try {
      recorder = selectedMime
        ? new MediaRecorder(stream, { mimeType: selectedMime })
        : new MediaRecorder(stream);
    } catch (e) {
      console.warn("MediaRecorder creation error:", e);
      recorder = new MediaRecorder(stream);
    }

    audioChunksRef.current = [];
    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) {
        audioChunksRef.current.push(e.data);
      }
    };

    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      clearInterval(timerRef.current);

      const mimeType = recorder.mimeType || selectedMime || "audio/webm";
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });

      if (audioBlob.size < 200) {
        setError("Audio recording was too short. Please try speaking again.");
        setUiState(S.IDLE);
        return;
      }

      setUiState(S.TRANSCRIBING);

      let transcript = "";
      try {
        const transcribeRes = await aiService.transcribeAudio(audioBlob);
        transcript = (transcribeRes?.transcript || "").trim();
      } catch (e) {
        const errMsg =
          e?.response?.data?.detail || e.message || "Failed to transcribe audio.";
        setError(errMsg);
        setUiState(S.IDLE);
        return;
      }

      if (!transcript) {
        setError("Could not transcribe any words. Please speak clearly and try again.");
        setUiState(S.IDLE);
        return;
      }

      sendQuery(transcript, "voice", (t, l, idx) => {
        handleSpeak(t, l, idx);
      });
    };

    mediaRecorderRef.current = recorder;
    recorder.start(250);

    setRecordingSeconds(0);
    setUiState(S.LISTENING);

    timerRef.current = setInterval(() => {
      setRecordingSeconds((prev) => prev + 1);
    }, 1000);
  }, [sendQuery, setError, setSpeakingMsgIndex, setUiState, handleSpeak]);

  const stopRecording = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const isRecording = uiState === S.LISTENING;
  const isBusy = uiState === S.TRANSCRIBING || uiState === S.THINKING;

  return (
    <AppShell>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          height: "calc(100vh - 85px)",
          maxHeight: "calc(100vh - 85px)",
          backgroundColor: "#f8fafc",
          position: "relative",
          width: "100%",
          boxSizing: "border-box",
        }}
      >
        <div
          style={{
            maxWidth: "1150px",
            width: "100%",
            margin: "0 auto",
            display: "flex",
            flexDirection: "column",
            height: "100%",
            position: "relative",
            backgroundColor: "#ffffff",
            borderRadius: "12px",
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(15,23,42,0.06)",
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "0.6rem 1rem",
              backgroundColor: "#ffffff",
              borderBottom: "1px solid #e2e8f0",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexShrink: 0,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "8px",
                  backgroundColor: "#0284c7",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: "0 2px 4px rgba(2,132,199,0.25)",
                }}
              >
                <SparkleIcon style={{ color: "#ffffff", fontSize: "1.1rem" }} />
              </div>
              <div>
                <h1 style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0f172a", margin: 0, lineHeight: 1.2 }}>
                  Ask PulseCRM
                </h1>
                <span style={{ fontSize: "0.7rem", color: "#64748b" }}>
                  Multimodal CRM Relationship Copilot
                </span>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
              <button
                type="button"
                onClick={() => setReadAloudEnabled(!readAloudEnabled)}
                title="Automatically read text responses aloud"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.3rem",
                  padding: "0.3rem 0.55rem",
                  borderRadius: "6px",
                  border: "1px solid #e2e8f0",
                  backgroundColor: readAloudEnabled ? "#e0f2fe" : "#ffffff",
                  color: readAloudEnabled ? "#0369a1" : "#64748b",
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                  minHeight: "36px",
                }}
                aria-label={readAloudEnabled ? "Disable Read Aloud" : "Enable Read Aloud"}
              >
                {readAloudEnabled ? <SpeakIcon style={{ fontSize: "0.85rem" }} /> : <MuteIcon style={{ fontSize: "0.85rem" }} />}
                <span className="hidden sm:inline">{readAloudEnabled ? "Speech ON" : "Speech OFF"}</span>
              </button>

              <button
                type="button"
                onClick={handleNewConversationClick}
                title="Start new conversation context"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "0.25rem",
                  padding: "0.3rem 0.6rem",
                  borderRadius: "6px",
                  border: "1px solid #e2e8f0",
                  backgroundColor: "#ffffff",
                  color: "#334155",
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  cursor: "pointer",
                  minHeight: "36px",
                }}
                aria-label="Start new conversation"
              >
                <AddIcon style={{ fontSize: "0.85rem" }} />
                <span>New</span>
              </button>
            </div>
          </div>

          {/* Compact Context Indicator Bar */}
          <div
            style={{
              padding: "0.35rem 1rem",
              backgroundColor: "#f8fafc",
              borderBottom: "1px solid #f1f5f9",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              fontSize: "0.72rem",
              color: "#475569",
              flexShrink: 0,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              <span style={{ fontWeight: 700, color: "#0f172a" }}>Context:</span>
              {selectedHcpName ? (
                <span style={{ color: "#0284c7", fontWeight: 600 }}>
                  {selectedHcpName}
                </span>
              ) : (
                <span style={{ color: "#94a3b8" }}>None</span>
              )}
            </div>
            {selectedHcpName && (
              <button
                type="button"
                onClick={clearHcpContext}
                title="Clear active doctor context"
                style={{
                  background: "none",
                  border: "none",
                  color: "#94a3b8",
                  cursor: "pointer",
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  padding: "0.1rem 0.35rem",
                  borderRadius: "4px",
                }}
                aria-label="Clear active doctor context"
              >
                ✕ Clear
              </button>
            )}
          </div>

          {/* Compact Dismissible Speech Warning Pill */}
          {!ttsNotificationDismissed && !isTeluguVoiceAvailable && (
            <div
              style={{
                margin: "0.35rem 1rem 0 1rem",
                padding: "0.25rem 0.65rem",
                backgroundColor: "#fffbeb",
                border: "1px solid #fde68a",
                borderRadius: "9999px",
                fontSize: "0.7rem",
                color: "#92400e",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "0.5rem",
                maxWidth: "fit-content",
                alignSelf: "center",
                flexShrink: 0,
              }}
            >
              <span>🔊 Telugu voice unavailable in browser · Text mode active</span>
              <button
                type="button"
                onClick={() => setTtsNotificationDismissed(true)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#92400e", fontWeight: 700, fontSize: "0.75rem", padding: "0 0.2rem" }}
                aria-label="Dismiss voice notice"
              >
                ✕
              </button>
            </div>
          )}

          {error && (
            <div
              style={{
                margin: "0.4rem 1rem 0 1rem",
                padding: "0.4rem 0.8rem",
                backgroundColor: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "8px",
                fontSize: "0.775rem",
                color: "#dc2626",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexShrink: 0,
              }}
            >
              <span>{error}</span>
              <button
                type="button"
                onClick={() => setError(null)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#dc2626", fontWeight: 700 }}
                aria-label="Dismiss error message"
              >
                ✕
              </button>
            </div>
          )}

          {/* Chat message list */}
          <div
            ref={chatContainerRef}
            onScroll={handleScroll}
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "0.75rem 1rem 1.25rem 1rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.35rem",
              backgroundColor: "#f8fafc",
            }}
          >
            {chatHistory.length === 0 ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "auto",
                  maxWidth: "580px",
                  textAlign: "center",
                  padding: "1rem",
                }}
              >
                <div
                  style={{
                    width: 48,
                    height: 48,
                    borderRadius: "14px",
                    backgroundColor: "#e0f2fe",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: "0.75rem",
                  }}
                >
                  <BotIcon style={{ fontSize: "1.6rem", color: "#0284c7" }} />
                </div>

                <h2 style={{ fontSize: "1.05rem", fontWeight: 700, color: "#0f172a", marginBottom: "0.25rem" }}>
                  How can I assist your territory today?
                </h2>
                <p style={{ fontSize: "0.8rem", color: "#64748b", maxWidth: "420px", marginBottom: "1rem", lineHeight: 1.5 }}>
                  Type or speak in English, Telugu, or mixed speech. Query doctor relationships, schedule meetings, or log field interactions.
                </p>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                    gap: "0.45rem",
                    width: "100%",
                    textAlign: "left",
                  }}
                >
                  {SUGGESTED_PROMPTS.map((p, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => sendQuery(p.query, "text", (t, l, i) => { if (readAloudEnabled) handleSpeak(t, l, i); })}
                      style={{
                        padding: "0.55rem 0.75rem",
                        borderRadius: "8px",
                        backgroundColor: "#ffffff",
                        border: "1px solid #e2e8f0",
                        display: "flex",
                        alignItems: "center",
                        gap: "0.45rem",
                        fontSize: "0.75rem",
                        color: "#334155",
                        cursor: "pointer",
                        boxShadow: "0 1px 2px rgba(15,23,42,0.03)",
                        transition: "all 0.15s ease",
                        minHeight: "44px",
                      }}
                      aria-label={p.label}
                    >
                      <span style={{ fontSize: "0.95rem" }}>{p.icon}</span>
                      <span style={{ fontWeight: 500 }}>{p.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {chatHistory.map((msg, idx) => (
                  <ChatBubble
                    key={idx}
                    message={msg}
                    index={idx}
                    isSpeaking={speakingMsgIndex === idx}
                    onSpeak={() =>
                      speakingMsgIndex === idx
                        ? handleStopSpeaking()
                        : handleSpeak(msg.content, msg.language, idx)
                    }
                    isTeluguVoiceAvailable={isTeluguVoiceAvailable}
                    onConfirmAction={confirmPendingAction}
                    onCancelAction={cancelPendingAction}
                    onSelectCandidate={selectAmbiguityCandidate}
                    onUpdateMeeting={updatePendingAction}
                    onQuickQuery={(q) => sendQuery(q, "text", (t, l, i) => { if (readAloudEnabled) handleSpeak(t, l, i); })}
                  />
                ))}

                {isBusy && <ThinkingIndicator step={thinkingStep} />}

                <div ref={chatBottomRef} />
              </>
            )}
          </div>

          {showScrollDown && (
            <button
              type="button"
              onClick={() => {
                scrollToBottom();
                setShowScrollDown(false);
              }}
              style={{
                position: "absolute",
                bottom: "75px",
                right: "20px",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.25rem",
                padding: "0.35rem 0.7rem",
                borderRadius: "9999px",
                backgroundColor: "#0284c7",
                color: "#ffffff",
                border: "none",
                boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)",
                fontSize: "0.72rem",
                fontWeight: 600,
                cursor: "pointer",
                zIndex: 10,
              }}
              aria-label="Scroll to latest message"
            >
              <ScrollDownIcon style={{ fontSize: "0.9rem" }} />
              <span>Latest</span>
            </button>
          )}

          {/* Sticky Composer */}
          <div
            style={{
              padding: "0.55rem 0.9rem 0.75rem 0.9rem",
              backgroundColor: "#ffffff",
              borderTop: "1px solid #e2e8f0",
              flexShrink: 0,
            }}
          >
            {isRecording && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0.4rem 0.7rem",
                  borderRadius: "8px",
                  backgroundColor: "#fef2f2",
                  border: "1px solid #fecaca",
                  marginBottom: "0.4rem",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.45rem" }}>
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      backgroundColor: "#dc2626",
                      animation: "pulse 1.2s infinite",
                    }}
                  />
                  <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "#dc2626" }}>
                    Listening... · {formatSeconds(recordingSeconds)}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={stopRecording}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.2rem",
                    padding: "0.2rem 0.5rem",
                    borderRadius: "4px",
                    backgroundColor: "#dc2626",
                    color: "#ffffff",
                    border: "none",
                    fontSize: "0.72rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    minHeight: "36px",
                  }}
                  aria-label="Stop recording voice message"
                >
                  <StopIcon style={{ fontSize: "0.8rem" }} /> Stop
                </button>
              </div>
            )}

            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: "0.45rem",
                backgroundColor: "#f8fafc",
                border: "1px solid #cbd5e1",
                borderRadius: "10px",
                padding: "0.35rem 0.55rem",
                boxShadow: "0 1px 2px rgba(15,23,42,0.04)",
              }}
            >
              <textarea
                ref={textareaRef}
                rows={1}
                value={inputText}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                disabled={isBusy || isRecording}
                placeholder="Ask about doctors, meetings, follow-ups, products, or your territory..."
                style={{
                  flex: 1,
                  border: "none",
                  background: "transparent",
                  resize: "none",
                  outline: "none",
                  fontSize: "0.875rem",
                  lineHeight: 1.45,
                  color: "#0f172a",
                  maxHeight: "120px",
                  fontFamily: "inherit",
                  padding: "0.2rem",
                }}
                aria-label="Ask PulseCRM message input"
              />

              <button
                type="button"
                onClick={isRecording ? stopRecording : startRecording}
                disabled={isBusy}
                title={isRecording ? "Stop recording" : "Record voice message"}
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  backgroundColor: isRecording ? "#dc2626" : "#ffffff",
                  color: isRecording ? "#ffffff" : "#0284c7",
                  border: isRecording ? "none" : "1px solid #cbd5e1",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: isBusy ? "not-allowed" : "pointer",
                  flexShrink: 0,
                }}
                aria-label={isRecording ? "Stop recording" : "Record voice message"}
              >
                {isRecording ? <StopIcon style={{ fontSize: "1rem" }} /> : <MicIcon style={{ fontSize: "1rem" }} />}
              </button>

              <button
                type="button"
                onClick={handleSendClick}
                disabled={!inputText.trim() || isBusy || isRecording}
                title="Send message (Enter)"
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "50%",
                  backgroundColor: inputText.trim() && !isBusy && !isRecording ? "#0284c7" : "#e2e8f0",
                  color: inputText.trim() && !isBusy && !isRecording ? "#ffffff" : "#94a3b8",
                  border: "none",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: inputText.trim() && !isBusy && !isRecording ? "pointer" : "default",
                  flexShrink: 0,
                }}
                aria-label="Send message"
              >
                <SendIcon style={{ fontSize: "0.95rem" }} />
              </button>
            </div>
          </div>
        </div>

        {/* Unsaved Action Confirmation Modal */}
        {showUnsavedModal && (
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="unsaved-modal-title"
            style={{
              position: "fixed",
              inset: 0,
              backgroundColor: "rgba(15, 23, 42, 0.45)",
              backdropFilter: "blur(3px)",
              zIndex: 50,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: "1rem",
            }}
          >
            <div
              style={{
                backgroundColor: "#ffffff",
                borderRadius: "12px",
                maxWidth: "420px",
                width: "100%",
                padding: "1.25rem",
                boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
                border: "1px solid #e2e8f0",
              }}
            >
              <h3
                id="unsaved-modal-title"
                style={{ fontSize: "1rem", fontWeight: 700, color: "#0f172a", marginBottom: "0.5rem" }}
              >
                Unsaved Action in Progress
              </h3>
              <p style={{ fontSize: "0.85rem", color: "#475569", lineHeight: 1.5, marginBottom: "1.25rem" }}>
                You have an unsaved action. Starting a new conversation will discard this pending action. Do you want to continue?
              </p>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
                <button
                  type="button"
                  onClick={() => setShowUnsavedModal(false)}
                  style={{
                    padding: "0.45rem 0.9rem",
                    borderRadius: "6px",
                    border: "1px solid #cbd5e1",
                    backgroundColor: "#ffffff",
                    color: "#475569",
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    minHeight: "40px",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowUnsavedModal(false);
                    resetConversation(true);
                  }}
                  style={{
                    padding: "0.45rem 0.9rem",
                    borderRadius: "6px",
                    border: "none",
                    backgroundColor: "#dc2626",
                    color: "#ffffff",
                    fontSize: "0.8125rem",
                    fontWeight: 600,
                    cursor: "pointer",
                    minHeight: "40px",
                  }}
                >
                  Start New
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}

export default VoiceCopilot;
