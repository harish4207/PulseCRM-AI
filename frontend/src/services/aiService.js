import api from "./api";

export const aiService = {
  async logMeeting(meetingText) {
    const payload = {
      meeting_text: meetingText,
    };
    const response = await api.post("/ai/log-meeting", payload);
    return response.data;
  },

  async transcribeAudio(audioBlob) {
    if (!audioBlob || audioBlob.size === 0) {
      throw new Error("No usable audio was recorded. Please try recording again.");
    }
    const contentType = audioBlob.type || "audio/webm";
    const response = await api.post("/ai/transcribe", audioBlob, {
      headers: {
        "Content-Type": contentType,
      },
    });
    return response.data;
  },

  async copilotChat({
    message,
    conversationId = null,
    inputMode = "text",
    history = [],
    selectedHcpId = null,
    selectedHcpName = null,
    pendingConfirmation = false,
    pendingAction = null,
  }) {
    const response = await api.post("/ai/copilot/chat", {
      message,
      conversation_id: conversationId,
      input_mode: inputMode,
      history,
      selected_hcp_id: selectedHcpId,
      selected_hcp_name: selectedHcpName,
      pending_confirmation: pendingConfirmation,
      pending_action: pendingAction,
    });
    return response.data;
  },

  async voiceChat(params) {
    return this.copilotChat({
      ...params,
      message: params.transcript || params.message,
      inputMode: "voice",
    });
  },
};

export default aiService;
