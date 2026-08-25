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
    const response = await api.post("/ai/transcribe", audioBlob, {
      headers: {
        "Content-Type": audioBlob.type || "audio/webm",
      },
    });
    return response.data;
  },
};

export default aiService;
