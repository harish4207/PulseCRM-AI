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
};

export default aiService;
