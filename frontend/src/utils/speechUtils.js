/**
 * speechUtils.js - Browser SpeechSynthesis & Multilingual Voice Selection Utilities
 *
 * Provides:
 * - Telugu Unicode & Mixed-Language Detection
 * - Asynchronous Voice Discovery
 * - Strict Voice Selection (NO English fallback for Telugu)
 * - Development TTS Diagnostics
 */

// Telugu Unicode character range: U+0C00 - U+0C7F
export const TELUGU_UNICODE_REGEX = /[\u0C00-\u0C7F]/;

/**
 * Detects whether text contains Telugu characters.
 * Returns 'te' if Telugu characters exist (pure or mixed with English entities),
 * otherwise returns 'en'.
 */
export function detectResponseLanguage(text) {
  if (!text || typeof text !== "string") return "en";
  if (TELUGU_UNICODE_REGEX.test(text)) {
    return "te";
  }
  return "en";
}

/**
 * Finds a Telugu-capable voice in the available SpeechSynthesisVoice list.
 * Matches on lang ('te-IN', 'te_IN', 'te', 'te-*') or voice name containing 'telugu'.
 * Returns null if no Telugu voice is found.
 */
export function findTeluguVoice(voiceList) {
  if (!Array.isArray(voiceList) || voiceList.length === 0) return null;

  // 1. Exact match for 'te-IN' or 'te_IN' or 'te'
  let voice = voiceList.find(
    (v) =>
      v.lang === "te-IN" ||
      v.lang === "te_IN" ||
      v.lang === "te" ||
      v.lang?.toLowerCase() === "te-in"
  );
  if (voice) return voice;

  // 2. Prefix match for 'te-' or 'te_'
  voice = voiceList.find(
    (v) =>
      v.lang?.toLowerCase().startsWith("te-") ||
      v.lang?.toLowerCase().startsWith("te_")
  );
  if (voice) return voice;

  // 3. Match 'telugu' in the voice name
  voice = voiceList.find((v) =>
    (v.name || "").toLowerCase().includes("telugu")
  );
  if (voice) return voice;

  return null;
}

/**
 * Finds the best available English voice.
 * Prioritizes: en-IN -> en-US/en-GB -> any 'en-*' voice -> fallback voice.
 */
export function findEnglishVoice(voiceList) {
  if (!Array.isArray(voiceList) || voiceList.length === 0) return null;

  // 1. Indian English preferred for Indian healthcare context
  let voice = voiceList.find(
    (v) =>
      v.lang === "en-IN" ||
      v.lang === "en_IN" ||
      (v.name || "").toLowerCase().includes("india")
  );
  if (voice) return voice;

  // 2. US or GB English
  voice = voiceList.find(
    (v) =>
      v.lang === "en-US" ||
      v.lang === "en_US" ||
      v.lang === "en-GB" ||
      v.lang === "en_GB"
  );
  if (voice) return voice;

  // 3. Any English voice
  voice = voiceList.find((v) => (v.lang || "").toLowerCase().startsWith("en"));
  if (voice) return voice;

  return voiceList[0] || null;
}

/**
 * Selects the appropriate voice and language code based on text content and available voices.
 * STRICT: If the text is Telugu and NO Telugu voice is available, returns voice: null.
 * NEVER falls back to an English voice for Telugu text.
 */
export function selectVoiceForText(text, voiceList, declaredLanguage = "en") {
  const detected = detectResponseLanguage(text);
  const isTelugu = detected === "te" || declaredLanguage === "te" || declaredLanguage === "mixed";

  if (isTelugu) {
    const teluguVoice = findTeluguVoice(voiceList);
    return {
      voice: teluguVoice,
      lang: teluguVoice ? (teluguVoice.lang || "te-IN") : "te-IN",
      detectedLanguage: "te",
      isSupported: !!teluguVoice,
    };
  }

  const englishVoice = findEnglishVoice(voiceList);
  return {
    voice: englishVoice,
    lang: englishVoice ? (englishVoice.lang || "en-IN") : "en-IN",
    detectedLanguage: "en",
    isSupported: true,
  };
}

/**
 * Executes SpeechSynthesis with proper voice selection, lifecycle events, and diagnostics.
 */
export function speakResponse({
  text,
  language = "en",
  voices = [],
  onStart = null,
  onEnd = null,
  onError = null,
  onNoVoice = null,
}) {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) {
    if (onNoVoice) onNoVoice({ reason: "speech_synthesis_unsupported" });
    if (onEnd) onEnd();
    return { success: false, reason: "speech_synthesis_unsupported" };
  }

  // Cancel any existing speech to prevent overlapping utterances
  window.speechSynthesis.cancel();

  if (!text || typeof text !== "string" || !text.trim()) {
    if (onEnd) onEnd();
    return { success: false, reason: "empty_text" };
  }

  const { voice, lang, detectedLanguage, isSupported } = selectVoiceForText(
    text,
    voices,
    language
  );

  // Development / Debug Diagnostic Logging
  console.groupCollapsed(`[PulseCRM TTS] Speaking Request (${detectedLanguage})`);
  console.log("TTS TEXT:", text);
  console.log("TTS DETECTED LANGUAGE:", detectedLanguage);
  console.log("DECLARED LANGUAGE:", language);
  console.log(
    "AVAILABLE VOICES:",
    voices.map((v) => `${v.name} (${v.lang})`)
  );
  console.log("SELECTED VOICE:", voice ? voice.name : "NONE");
  console.log("SELECTED VOICE LANG:", voice ? voice.lang : "NONE");
  console.log(
    "TTS STATUS:",
    isSupported
      ? "Proceeding with speech synthesis"
      : "Telugu voice unavailable - Falling back to text-only"
  );
  console.groupEnd();

  // If Telugu was detected but no Telugu voice is available in the browser
  if (detectedLanguage === "te" && !voice) {
    if (onNoVoice) {
      onNoVoice({
        reason: "telugu_voice_unavailable",
        text,
        detectedLanguage,
      });
    }
    if (onEnd) onEnd();
    return {
      success: false,
      reason: "telugu_voice_unavailable",
      detectedLanguage,
    };
  }

  try {
    const utterance = new SpeechSynthesisUtterance(text);
    if (voice) {
      utterance.voice = voice;
    }
    utterance.lang = lang;
    utterance.rate = 0.9;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    utterance.onstart = () => {
      if (onStart) onStart({ voice, lang, detectedLanguage });
    };

    utterance.onend = () => {
      if (onEnd) onEnd();
    };

    utterance.onerror = (event) => {
      console.warn("[PulseCRM TTS] SpeechSynthesis error:", event);
      if (onError) onError(event);
      if (onEnd) onEnd();
    };

    window.speechSynthesis.speak(utterance);
    return {
      success: true,
      voice,
      lang,
      detectedLanguage,
    };
  } catch (err) {
    console.error("[PulseCRM TTS] Failed to execute speech synthesis:", err);
    if (onError) onError(err);
    if (onEnd) onEnd();
    return { success: false, reason: "exception", error: err };
  }
}

/**
 * Immediately cancels any active browser speech synthesis.
 */
export function cancelSpeech() {
  if (typeof window !== "undefined" && "speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}
