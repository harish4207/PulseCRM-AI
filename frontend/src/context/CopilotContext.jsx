import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import aiService from "../services/aiService";
import { cancelSpeech, speakResponse, findTeluguVoice, detectResponseLanguage } from "../utils/speechUtils";

const CopilotContext = createContext(null);

const STORAGE_KEYS = {
  CONV_ID: "pulse_copilot_conv_id",
  CHAT_HIST: "pulse_copilot_chat_history",
  API_HIST: "pulse_copilot_api_history",
  HCP_ID: "pulse_copilot_hcp_id",
  HCP_NAME: "pulse_copilot_hcp_name",
  HCP_HOSPITAL: "pulse_copilot_hcp_hospital",
  HCP_CITY: "pulse_copilot_hcp_city",
  HCP_SPEC: "pulse_copilot_hcp_specialization",
  PENDING_CONF: "pulse_copilot_pending_conf",
  PENDING_ACT: "pulse_copilot_pending_act",
  EXEC_ACTIONS: "pulse_copilot_exec_actions",
  READ_ALOUD: "pulse_copilot_read_aloud",
  TTS_DISMISSED: "pulse_copilot_tts_dismissed",
};

const UI_STATES = {
  IDLE: "idle",
  LISTENING: "listening",
  TRANSCRIBING: "transcribing",
  THINKING: "thinking",
  RESPONDED: "responded",
  SPEAKING: "speaking",
};

function generateConvId() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `conv_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

function safeGetStorage(key, fallback = null) {
  try {
    if (typeof sessionStorage === "undefined") return fallback;
    const val = sessionStorage.getItem(key);
    if (val === null || val === undefined) return fallback;
    return JSON.parse(val);
  } catch (e) {
    return fallback;
  }
}

function safeSetStorage(key, value) {
  try {
    if (typeof sessionStorage === "undefined") return;
    if (value === null || value === undefined) {
      sessionStorage.removeItem(key);
    } else {
      sessionStorage.setItem(key, JSON.stringify(value));
    }
  } catch (e) {
    // quota exceeded or private mode
  }
}

export function CopilotProvider({ children }) {
  // Persistent States
  const [conversationId, setConversationId] = useState(() => {
    return safeGetStorage(STORAGE_KEYS.CONV_ID) || generateConvId();
  });

  const [chatHistory, setChatHistory] = useState(() => {
    return safeGetStorage(STORAGE_KEYS.CHAT_HIST, []);
  });

  const [apiHistory, setApiHistory] = useState(() => {
    return safeGetStorage(STORAGE_KEYS.API_HIST, []);
  });

  const [selectedHcpId, setSelectedHcpId] = useState(() => {
    return safeGetStorage(STORAGE_KEYS.HCP_ID, null);
  });

  const [selectedHcpName, setSelectedHcpName] = useState(() => {
    return safeGetStorage(STORAGE_KEYS.HCP_NAME, null);
  });

  const [selectedHcpHospital, setSelectedHcpHospital] = useState(() => {
    return safeGetStorage(STORAGE_KEYS.HCP_HOSPITAL, null);
  });

  const [selectedHcpCity, setSelectedHcpCity] = useState(() => {
    return safeGetStorage(STORAGE_KEYS.HCP_CITY, null);
  });

  const [selectedHcpSpecialization, setSelectedHcpSpecialization] = useState(() => {
    return safeGetStorage(STORAGE_KEYS.HCP_SPEC, null);
  });

  const [pendingConfirmation, setPendingConfirmation] = useState(() => {
    return !!safeGetStorage(STORAGE_KEYS.PENDING_CONF, false);
  });

  const [pendingAction, setPendingAction] = useState(() => {
    return safeGetStorage(STORAGE_KEYS.PENDING_ACT, null);
  });

  const [executedActionIds, setExecutedActionIds] = useState(() => {
    return safeGetStorage(STORAGE_KEYS.EXEC_ACTIONS, []);
  });

  const [readAloudEnabled, setReadAloudEnabled] = useState(() => {
    return !!safeGetStorage(STORAGE_KEYS.READ_ALOUD, false);
  });

  const [ttsNotificationDismissed, setTtsNotificationDismissed] = useState(() => {
    return !!safeGetStorage(STORAGE_KEYS.TTS_DISMISSED, false);
  });

  // Ephemeral UI States
  const [uiState, setUiState] = useState(UI_STATES.IDLE);
  const [thinkingStep, setThinkingStep] = useState("Checking CRM...");
  const [currentTranscript, setCurrentTranscript] = useState("");
  const [error, setError] = useState(null);
  const [speakingMsgIndex, setSpeakingMsgIndex] = useState(null);

  // Sync persistent states to sessionStorage
  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.CONV_ID, conversationId);
  }, [conversationId]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.CHAT_HIST, chatHistory);
  }, [chatHistory]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.API_HIST, apiHistory);
  }, [apiHistory]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.HCP_ID, selectedHcpId);
  }, [selectedHcpId]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.HCP_NAME, selectedHcpName);
  }, [selectedHcpName]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.HCP_HOSPITAL, selectedHcpHospital);
  }, [selectedHcpHospital]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.HCP_CITY, selectedHcpCity);
  }, [selectedHcpCity]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.HCP_SPEC, selectedHcpSpecialization);
  }, [selectedHcpSpecialization]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.PENDING_CONF, pendingConfirmation);
  }, [pendingConfirmation]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.PENDING_ACT, pendingAction);
  }, [pendingAction]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.EXEC_ACTIONS, executedActionIds);
  }, [executedActionIds]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.READ_ALOUD, readAloudEnabled);
  }, [readAloudEnabled]);

  useEffect(() => {
    safeSetStorage(STORAGE_KEYS.TTS_DISMISSED, ttsNotificationDismissed);
  }, [ttsNotificationDismissed]);

  const clearHcpContext = useCallback(() => {
    setSelectedHcpId(null);
    setSelectedHcpName(null);
    setSelectedHcpHospital(null);
    setSelectedHcpCity(null);
    setSelectedHcpSpecialization(null);
  }, []);

  const resetConversation = useCallback((force = false) => {
    if (pendingConfirmation && !force) {
      return false; // Requires confirmation dialog
    }
    cancelSpeech();
    setSpeakingMsgIndex(null);
    const newId = generateConvId();
    setConversationId(newId);
    setChatHistory([]);
    setApiHistory([]);
    clearHcpContext();
    setPendingConfirmation(false);
    setPendingAction(null);
    setUiState(UI_STATES.IDLE);
    setError(null);
    return true;
  }, [pendingConfirmation, clearHcpContext]);

  const sendQuery = useCallback(
    async (queryText, inputMode = "text", onSpeakCallback = null) => {
      const trimmed = (queryText || "").trim();
      if (!trimmed) return;

      setError(null);
      setUiState(UI_STATES.THINKING);
      setThinkingStep("Analyzing request...");

      const userMsg = {
        role: "user",
        content: trimmed,
        input_mode: inputMode,
        timestamp: new Date().toISOString(),
      };

      const newApiHistory = [...apiHistory, { role: "user", content: trimmed }];
      setChatHistory((prev) => [...prev, userMsg]);
      setApiHistory(newApiHistory);

      let stepTimer = setTimeout(() => {
        setThinkingStep("Checking CRM database...");
      }, 700);

      let data = null;
      try {
        data = await aiService.copilotChat({
          message: trimmed,
          conversationId,
          inputMode,
          history: newApiHistory,
          selectedHcpId,
          selectedHcpName,
          pendingConfirmation,
          pendingAction,
        });
      } catch (err) {
        clearTimeout(stepTimer);
        const errMsg =
          err?.response?.data?.detail ||
          err?.message ||
          "Could not connect to PulseCRM assistant. Please try again.";
        setError(errMsg);
        const fallbackMsg = {
          role: "assistant",
          content: "I encountered a connection issue. Please verify your network or try again.",
          intent: "error",
          language: "en",
          timestamp: new Date().toISOString(),
        };
        setChatHistory((prev) => [...prev, fallbackMsg]);
        setUiState(UI_STATES.RESPONDED);
        return;
      } finally {
        clearTimeout(stepTimer);
      }

      const response = data?.response || "";
      const intent = data?.intent || "";
      const language = data?.language || "en";
      const newHcpId = data?.hcp_id ?? null;
      const newHcpName = data?.hcp_name ?? null;
      const newPending = !!data?.pending_confirmation;
      const newPendingAction = data?.pending_action ?? null;
      const cardData = data?.card_data ?? null;

      if (newHcpId !== null) setSelectedHcpId(newHcpId);
      if (newHcpName !== null) setSelectedHcpName(newHcpName);
      setPendingConfirmation(newPending);
      setPendingAction(newPendingAction);

      const assistantMsg = {
        role: "assistant",
        content: response,
        intent,
        language,
        cardData,
        input_mode: inputMode,
        timestamp: new Date().toISOString(),
      };

      setChatHistory((prev) => {
        const updated = !newPending
          ? prev.map((msg) => {
              if (msg.role === "assistant" && msg.cardData) {
                const cType = msg.cardData.type;
                if (
                  cType === "meeting_schedule_confirmation" ||
                  cType === "meeting_capture_confirmation" ||
                  cType === "confirmation_action" ||
                  msg.cardData.pending_confirmation
                ) {
                  return {
                    ...msg,
                    cardData: {
                      ...msg.cardData,
                      is_completed: true,
                      status: "completed",
                    },
                  };
                }
              }
              return msg;
            })
          : prev;
        return [...updated, assistantMsg];
      });

      setApiHistory([...newApiHistory, { role: "assistant", content: response }]);
      setUiState(UI_STATES.RESPONDED);

      if (onSpeakCallback && response) {
        onSpeakCallback(response, language, chatHistory.length + 1);
      }
    },
    [
      apiHistory,
      selectedHcpId,
      selectedHcpName,
      pendingConfirmation,
      pendingAction,
      conversationId,
      chatHistory.length,
    ]
  );

  const confirmPendingAction = useCallback(() => {
    sendQuery("Confirm", "text");
  }, [sendQuery]);

  const cancelPendingAction = useCallback(() => {
    sendQuery("Cancel", "text");
  }, [sendQuery]);

  const updatePendingAction = useCallback(
    (correctedText) => {
      sendQuery(correctedText, "text");
    },
    [sendQuery]
  );

  const selectAmbiguityCandidate = useCallback(
    (candidate) => {
      if (candidate?.id) setSelectedHcpId(candidate.id);
      if (candidate?.doctor_name) setSelectedHcpName(candidate.doctor_name);
      sendQuery(`I meant ${candidate?.doctor_name || "that doctor"}`, "text");
    },
    [sendQuery]
  );

  const value = {
    // Persistent
    conversationId,
    chatHistory,
    apiHistory,
    selectedHcpId,
    selectedHcpName,
    selectedHcpHospital,
    selectedHcpCity,
    selectedHcpSpecialization,
    pendingConfirmation,
    pendingAction,
    executedActionIds,
    readAloudEnabled,
    ttsNotificationDismissed,

    // Ephemeral
    uiState,
    setUiState,
    thinkingStep,
    setThinkingStep,
    currentTranscript,
    setCurrentTranscript,
    error,
    setError,
    speakingMsgIndex,
    setSpeakingMsgIndex,

    // Setters
    setReadAloudEnabled,
    setTtsNotificationDismissed,
    setSelectedHcpId,
    setSelectedHcpName,

    // Actions
    sendQuery,
    confirmPendingAction,
    cancelPendingAction,
    updatePendingAction,
    selectAmbiguityCandidate,
    clearHcpContext,
    resetConversation,
  };

  return <CopilotContext.Provider value={value}>{children}</CopilotContext.Provider>;
}

export function useCopilot() {
  const ctx = useContext(CopilotContext);
  if (!ctx) {
    throw new Error("useCopilot must be used within a CopilotProvider");
  }
  return ctx;
}

export default CopilotContext;
