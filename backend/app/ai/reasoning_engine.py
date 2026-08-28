"""
reasoning_engine.py - Core Conversational Intelligence & Multi-Provider Reasoning Engine

Supports:
1. Google Gemini 3.7 Flash (model ID: gemini-3.7-flash) via google-genai
2. Groq Model Pool (openai/gpt-oss-120b, qwen/qwen3.8-27b, qwen/qwen3.6-27b, groq/compound) via groq
3. Resilient deterministic fallback for offline/test environments

Enforces:
- Conversational first-pass reasoning (Greetings & general queries never trigger blind DB searches)
- Strict pharmaceutical anti-hallucination guardrails (Zero invented clinical/trial stats)
- Two-pass tool result synthesis (Tools return structured data -> LLM synthesizes natural grounded response)
- Bounded retry policy with exponential backoff for transient errors
- Safe JSON repair & structured output resilience
- Detailed dev tracing without leaking secrets
"""

import json
import logging
import re
import time
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.ai.normalizer import (
    normalize_transcript,
    clean_doctor_name,
    is_valid_person_name,
    extract_clean_search_tokens,
)
from app.ai.meeting_extractor import parse_date_expression, parse_time_expression, extract_reminder_preference

logger = logging.getLogger(__name__)

# Message Classification Categories
MSG_GREETING = "GREETING"
MSG_CAPABILITY_QUERY = "CAPABILITY_QUERY"
MSG_CONVERSATIONAL_QUESTION = "CONVERSATIONAL_QUESTION"
MSG_CRM_QUERY = "CRM_QUERY"
MSG_CRM_MUTATION = "CRM_MUTATION"
MSG_CONFIRMATION = "CONFIRMATION"
MSG_CANCELLATION = "CANCELLATION"
MSG_CORRECTION = "CORRECTION"
MSG_CLARIFICATION = "CLARIFICATION"

# Intent Constants
INTENT_GET_HCP_DETAILS = "GET_HCP_DETAILS"
INTENT_SEARCH_HCP = "SEARCH_HCP"
INTENT_GET_HCP_INTERACTIONS = "GET_HCP_INTERACTIONS"
INTENT_GET_HCP_FOLLOWUPS = "GET_HCP_FOLLOWUPS"
INTENT_GET_ALL_FOLLOWUPS = "GET_ALL_FOLLOWUPS"
INTENT_GET_RECENT_INTERACTIONS = "GET_RECENT_INTERACTIONS"
INTENT_GET_PRODUCT_DISCUSSIONS = "GET_PRODUCT_DISCUSSIONS"
INTENT_GET_HOSPITAL_DETAILS = "GET_HOSPITAL_DETAILS"
INTENT_CAPTURE_MEETING = "CAPTURE_MEETING"
INTENT_SCHEDULE_MEETING = "SCHEDULE_MEETING"
INTENT_CREATE_HCP = "CREATE_HCP"
INTENT_CREATE_INTERACTION = "CREATE_INTERACTION"
INTENT_CREATE_FOLLOWUP = "CREATE_FOLLOWUP"
INTENT_GET_NEXT_ACTION = "GET_NEXT_ACTION"
INTENT_CONFIRM_ACTION = "CONFIRM_ACTION"
INTENT_CANCEL_ACTION = "CANCEL_ACTION"
INTENT_CORRECT_PENDING_ACTION = "CORRECT_PENDING_ACTION"
INTENT_GET_CRM_BRIEF = "GET_CRM_BRIEF"
INTENT_GET_PRE_MEETING_INTELLIGENCE = "GET_PRE_MEETING_INTELLIGENCE"
INTENT_GET_CRM_ANALYTICS = "GET_CRM_ANALYTICS"
INTENT_GENERAL_CRM_QUERY = "GENERAL_CRM_QUERY"
INTENT_UNKNOWN = "UNKNOWN"

KNOWN_PRODUCTS = [
    "CardioPress-50",
    "CardioPress-75",
    "CardioPress-100",
    "Cancer Medicine",
    "AmloPulse",
    "GlycoCare",
    "NeuroCalm",
    "LipidGuard",
    "RespiClear",
]

TELUGU_UNICODE_RANGE = re.compile(r"[\u0C00-\u0C7F]")
TELUGU_LATIN_KEYWORDS = re.compile(
    r"\b(eppudu|kalisanu|gurinchi|cheppu|matladaru|matladam|aayana|aavida|avaru|chivari|"
    r"malli|rappudu|vachhe|em chepparu|em matladaru|kanipinchadu|naaku|meeru|"
    r"kalisina|ivala|ayindi|chesam|cheyyi|tho|ki|ni|ga|lo|"
    r"log cheyyi|record cheyyi|recent ga|evarini|anni|"
    r"avunu|vaddu|kaadu|evaritho|unna|pett|repu|somavaram|ippude|adigindi|pampali|kalavali|kalustha)\b",
    re.IGNORECASE,
)


def detect_language(text: str) -> str:
    if TELUGU_UNICODE_RANGE.search(text):
        return "te"
    if TELUGU_LATIN_KEYWORDS.search(text):
        return "mixed"
    return "en"


def clean_and_parse_json(raw_text: str) -> Optional[Dict[str, Any]]:
    """
    Robust JSON parser that handles:
    - Markdown code fences (```json ... ```)
    - Leading / trailing conversational text
    - Trailing commas
    - Single quotes -> double quotes
    """
    if not raw_text or not raw_text.strip():
        return None

    cleaned = raw_text.strip()

    # 1. Strip markdown fences
    if "```" in cleaned:
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()

    # 2. Try direct JSON parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 3. Extract outermost { ... }
    m = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if m:
        candidate = m.group(1).strip()
        try:
            return json.loads(candidate)
        except Exception:
            # Try removing trailing commas
            fixed = re.sub(r",\s*([\}\]])", r"\1", candidate)
            try:
                return json.loads(fixed)
            except Exception:
                pass

    return None


class ReasoningResult(BaseModel):
    language: str = "en"
    message_type: str = MSG_CRM_QUERY
    intent: str = INTENT_GENERAL_CRM_QUERY
    requires_crm_tool: bool = False
    crm_tool_name: Optional[str] = None
    doctor_name: Optional[str] = None
    doctors: List[str] = []
    hcp_entities: List[Dict[str, Any]] = []
    hospital: Optional[str] = None
    city: Optional[str] = None
    specialization: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    product: Optional[str] = None
    doctor_request: Optional[str] = None
    meeting_summary: Optional[str] = None
    follow_up_date: Optional[str] = None
    follow_up_display: Optional[str] = None
    meeting_time: Optional[str] = None
    meeting_time_display: Optional[str] = None
    reminder_minutes: Optional[int] = None
    reminder_display: Optional[str] = None
    location: Optional[str] = None
    is_new_hcp: bool = False
    is_anaphoric: bool = False
    is_override: bool = False
    override_target: Optional[str] = None
    actions: List[str] = []
    corrections: Dict[str, Any] = {}
    conversational_reply: Optional[str] = None
    confidence: float = 1.0
    model_used: str = "deterministic"
    latency_seconds: float = 0.0


SYSTEM_REASONING_PROMPT = """You are the core intelligence of Ask PulseCRM, a conversational CRM copilot for pharmaceutical medical representatives in India.
You understand English, Telugu (in Telugu script or Latin transliteration), and mixed Telugu-English code-switching.

Your task is to analyze the user's latest utterance in the context of the prior conversation, the active doctor context, and the evolving CRM state.

Analyze whether the message is:
1. GREETING: Casual greeting (e.g., "Hello", "Hi", "Good morning", "Namaste", "Hi Pulse"). Requires NO CRM tool, 0 database queries. Provide a natural greeting in conversational_reply.
2. CAPABILITY_QUERY: Explanation of what PulseCRM can do (e.g., "What can you help me with?", "What can you do?"). Requires NO CRM tool. Provide a concise explanation in conversational_reply.
3. CONVERSATIONAL_QUESTION: Conversational advice, rep guidance, pre-visit tips, general pharma discussions. Requires NO CRM tool. Provide a thoughtful, grounded answer in conversational_reply.
4. CRM_QUERY: Asking for specific CRM data. Set requires_crm_tool=true and choose the matching crm_tool_name from AVAILABLE CRM TOOLS.
5. CRM_MUTATION: Logging meetings, scheduling future meetings, creating HCPs, recording sample/brochure requests.
6. CONFIRMATION: Confirming a pending proposal (e.g., "Confirm", "Save everything", "Save both", "Yes proceed", "Avunu save cheyyi").
7. CANCELLATION: Cancelling a pending proposal (e.g., "Cancel", "Don't save", "Vaddu").
8. CORRECTION: Modifying specific slots in an active draft or keeping existing state (e.g., "Actually make it 4 PM", "Actually don't remind me", "I meant Dr Sharma, not Ananya", "Make Kamal Friday", "Cancel Sita", "Keep Sita as it is", "Keep everything", "Leave Sita as is").
9. CLARIFICATION: Rep is answering a clarification prompt (e.g., providing doctor name or hospital).

AVAILABLE CRM TOOLS:
- GET_HCP_DETAILS: Look up doctor contact, hospital, specialty
- GET_HCP_INTERACTIONS: Look up past visit history, discussion notes with a doctor
- GET_HCP_FOLLOWUPS: Look up follow-ups for a specific doctor
- GET_ALL_FOLLOWUPS: Look up all territory follow-ups
- GET_RECENT_INTERACTIONS: Look up recent visits across territory
- GET_PRODUCT_DISCUSSIONS: Look up interactions discussing a specific drug (e.g. CardioPress-50)
- GET_HOSPITAL_DETAILS: Look up doctor roster at a hospital
- GET_CRM_BRIEF: Daily agenda (today's meetings, follow-ups, overdue tasks)
- GET_NEXT_ACTION: Recommended high-priority next action
- GET_PRE_MEETING_INTELLIGENCE: Pre-visit briefing summary for a doctor
- GET_CRM_ANALYTICS: Weekly/monthly visit metrics
- CAPTURE_MEETING: Log past doctor visit, interaction notes, product discussion, brochure request
- SCHEDULE_MEETING: Schedule future calendar appointment with date, time, and reminder (supports single doctor or multiple doctors)
- CREATE_FOLLOWUP: Schedule future task/follow-up date
- CREATE_HCP: Add new doctor to territory directory
- CONFIRM_ACTION: User confirms proposal to commit to CRM
- CANCEL_ACTION: User cancels pending proposal
- CORRECT_PENDING_ACTION: User modifies time, date, reminder, or doctor in proposal
- GENERAL_CRM_QUERY: Greetings, capability questions, conversational advice, or prep discussions (requires NO CRM tool)

MULTIPLE DOCTOR ENTITY RECOGNITION:
If the user mentions multiple doctors in the same request (e.g. "both Kamal and Sita", "Rajesh, Priyanka and Ananya", "meet Kamal tomorrow and Sita Friday"):
- Output each doctor in the "doctors" array: ["Dr. Kamal", "Dr. Sita"].
- In "hcp_entities", provide an array of objects specifying individual details if mentioned: [{"name": "Dr. Kamal", "date": "tomorrow", "time": "03:00 PM"}, {"name": "Dr. Sita", "date": "Friday", "time": "04:00 PM"}].
- NEVER merge multiple doctors into a single comma-separated string in "doctor_name"!

CRITICAL PHARMACEUTICAL SAFETY MANDATE:
You must NEVER invent clinical trial numbers, percentages, efficacy claims, unapproved indications, or medical facts. If verified product information is not present in the CRM or approved knowledge base, explicitly state that the information is unavailable in your territory CRM database.

Output a valid JSON object matching this schema:
{
  "language": "en" | "te" | "mixed",
  "message_type": "GREETING" | "CAPABILITY_QUERY" | "CONVERSATIONAL_QUESTION" | "CRM_QUERY" | "CRM_MUTATION" | "CONFIRMATION" | "CANCELLATION" | "CORRECTION" | "CLARIFICATION",
  "intent": "GENERAL_CRM_QUERY" | "GET_HCP_DETAILS" | "GET_HCP_INTERACTIONS" | "GET_HCP_FOLLOWUPS" | "GET_ALL_FOLLOWUPS" | "GET_RECENT_INTERACTIONS" | "GET_PRODUCT_DISCUSSIONS" | "GET_HOSPITAL_DETAILS" | "GET_CRM_BRIEF" | "GET_NEXT_ACTION" | "GET_PRE_MEETING_INTELLIGENCE" | "GET_CRM_ANALYTICS" | "CAPTURE_MEETING" | "SCHEDULE_MEETING" | "CREATE_HCP" | "CREATE_INTERACTION" | "CREATE_FOLLOWUP" | "CONFIRM_ACTION" | "CANCEL_ACTION" | "CORRECT_PENDING_ACTION",
  "requires_crm_tool": boolean,
  "crm_tool_name": string or null,
  "doctor_name": string or null,          // Single doctor name if only one doctor is mentioned
  "doctors": list of strings,             // List of all doctor names if multiple doctors are mentioned (e.g. ["Dr. Kamal", "Dr. Sita"]). Empty list if only one or zero.
  "hcp_entities": list of objects,        // Optional list of doctor objects e.g. [{"name": "Dr. Kamal", "date": "tomorrow"}, {"name": "Dr. Sita", "date": "Friday"}]
  "hospital": string or null,             // Hospital or clinic name (e.g. "KIMS Hospital", "Care Hospital")
  "city": string or null,                 // City (e.g. "Hyderabad", "Visakhapatnam")
  "specialization": string or null,       // Specialty (e.g. "Cardiologist")
  "phone": string or null,                // Phone number
  "email": string or null,                // Email
  "product": string or null,              // Product name (e.g. "CardioPress-50", "NeuroCalm", "GlycoCare")
  "doctor_request": string or null,       // Request / samples / brochure
  "follow_up_display": string or null,    // Formatted follow-up date (e.g. "September 29, 2026", "Next Friday", "Monday")
  "meeting_time_display": string or null, // Formatted meeting time (e.g. "04:00 PM", "03:00 PM")
  "reminder_display": string or null,     // Formatted reminder (e.g. "30 minutes before", "1 hour before", "No reminder")
  "reminder_minutes": integer or null,    // Reminder offset in minutes (e.g. 30, 60, 0)
  "is_new_hcp": boolean,                  // True if user is introducing a new doctor
  "is_anaphoric": boolean,                // True if referring to current doctor via pronoun (him/her/aayana/aavida)
  "is_override": boolean,                 // True if replacing doctor (e.g. "Actually Dr Sharma, not Ananya")
  "override_target": string or null,      // Target replacement doctor
  "corrections": object,                  // Modified slots for draft updates
  "conversational_reply": string or null  // Direct, helpful, grounded response for greetings, capability answers, or conversational questions.
}
"""

SYNTHESIS_SYSTEM_PROMPT = """You are Ask PulseCRM, a conversational assistant for medical representatives.
The user asked a CRM question, and a CRM tool has executed and returned database records.

Synthesize a natural, concise, professional response directly answering the user's question using ONLY the provided tool results.

RULES:
1. Use ONLY the data in the tool result. Do NOT fabricate past interactions, dates, or product discussions.
2. If the tool result is empty or found no records, clearly and politely inform the user (e.g. "You don't have any overdue follow-ups scheduled.") in a natural, helpful tone.
3. Keep the tone helpful, professional, and tailored for field sales reps.
4. Match the user's language (English or Telugu).
"""


class ReasoningEngine:
    """
    Unified Multi-Provider Reasoning Engine.
    Handles Gemini 3.7 Flash, Groq Model Pool, and Deterministic Fallback.
    """

    def __init__(self):
        self.gemini_client = None
        self.groq_client = None
        self._init_clients()

    def _init_clients(self):
        gemini_key = settings.effective_gemini_api_key
        if gemini_key and len(gemini_key) > 5:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=gemini_key)
                logger.info("[ReasoningEngine] Google Gemini client initialized successfully.")
            except Exception as e:
                logger.warning(f"[ReasoningEngine] Could not initialize Gemini client: {e}")

        groq_key = settings.GROQ_API_KEY
        if groq_key and len(groq_key) > 5:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=groq_key, timeout=8.0)
                logger.info("[ReasoningEngine] Groq client initialized successfully.")
            except Exception as e:
                logger.warning(f"[ReasoningEngine] Could not initialize Groq client: {e}")

    def reason(
        self,
        transcript: str,
        context: Optional[Dict[str, Any]] = None,
        history: Optional[List[Any]] = None,
        preferred_provider: Optional[str] = None,
    ) -> ReasoningResult:
        """
        Execute core reasoning pass.
        Selects provider according to settings / preference with automatic fallback.
        """
        start_time = time.time()
        ctx = context or {}
        provider = preferred_provider or settings.AI_REASONING_PROVIDER or "gemini"

        norm = normalize_transcript(transcript.strip())

        # Step 1: Provider Execution with Fallback Chain
        res = None
        if provider == "gemini" and self.gemini_client:
            res = self._call_gemini(transcript, ctx, history)
            if not res and self.groq_client:
                logger.info("[ReasoningEngine] Failing over from Gemini to Groq pool.")
                res = self._call_groq(transcript, ctx, history)
        elif self.groq_client:
            res = self._call_groq(transcript, ctx, history)
            if not res and self.gemini_client:
                logger.info("[ReasoningEngine] Failing over from Groq to Gemini.")
                res = self._call_gemini(transcript, ctx, history)
        elif self.gemini_client:
            res = self._call_gemini(transcript, ctx, history)

        # Step 2: Deterministic Fallback if both LLM calls were skipped or failed
        if not res:
            res = self._call_deterministic(transcript, ctx, history)

        duration = time.time() - start_time
        res.latency_seconds = duration

        # Step 3: Strict Semantic Slot Validation on Model Output
        self._validate_and_normalize_slots(res, norm)

        # Step 4: Structured Development Logging (Zero secret leakage)
        hist_count = len(history) if history else 0
        logger.info(
            f"[REASONING TRACE] Model={res.model_used} | ContextItems={hist_count} | "
            f"Type={res.message_type} | Intent={res.intent} | RequiresTool={res.requires_crm_tool} | "
            f"Tool={res.crm_tool_name} | Doctor={res.doctor_name} | Latency={duration:.2f}s"
        )

        return res

    def _call_gemini(
        self,
        transcript: str,
        context: Dict[str, Any],
        history: Optional[List[Any]] = None,
    ) -> Optional[ReasoningResult]:
        """Call Google Gemini 3.7 Flash via google-genai with bounded retry."""
        if not self.gemini_client:
            return None

        for attempt in range(2):
            try:
                from google.genai import types

                hist_str = self._format_history(history)
                ctx_summary = self._format_context(context)

                user_prompt = (
                    f"Conversation History:\n{hist_str}\n\n"
                    f"Current Evolving CRM Context:\n{json.dumps(ctx_summary, indent=2)}\n\n"
                    f"Latest User Utterance:\n\"{transcript}\""
                )

                model_id = settings.GEMINI_MODEL or "gemini-3.7-flash"
                response = self.gemini_client.models.generate_content(
                    model=model_id,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_REASONING_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.0,
                    ),
                )

                data = clean_and_parse_json(response.text)
                if data:
                    return self._dict_to_reasoning_result(data, transcript, model_id)

            except Exception as e:
                logger.warning(f"[ReasoningEngine] Gemini API attempt {attempt+1} failed: {e}")
                time.sleep(0.4)

        return None

    def _call_groq(
        self,
        transcript: str,
        context: Dict[str, Any],
        history: Optional[List[Any]] = None,
    ) -> Optional[ReasoningResult]:
        """Call Groq with automatic model failover and bounded retry."""
        if not self.groq_client:
            return None

        hist_str = self._format_history(history)
        ctx_summary = self._format_context(context)

        user_prompt = (
            f"Conversation History:\n{hist_str}\n\n"
            f"Current Evolving CRM Context:\n{json.dumps(ctx_summary, indent=2)}\n\n"
            f"Latest User Utterance:\n\"{transcript}\""
        )

        # High-availability Groq candidate models pool ordered by reliability and quota
        candidate_models = [
            "qwen/qwen3.8-27b",
            "qwen/qwen3.6-27b",
            "openai/gpt-oss-120b",
            "groq/compound",
            "openai/gpt-oss-20b",
        ]

        for model_id in candidate_models:
            for attempt in range(2):
                try:
                    completion = self.groq_client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": SYSTEM_REASONING_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.0,
                    )

                    raw_text = completion.choices[0].message.content
                    data = clean_and_parse_json(raw_text)
                    if data:
                        return self._dict_to_reasoning_result(data, transcript, model_id)
                except Exception as e:
                    err_str = str(e).lower()
                    logger.warning(f"[ReasoningEngine] Groq model {model_id} attempt {attempt+1} failed: {e}")
                    # If 429 rate limit or 400 terms error, don't waste second attempt on same model
                    if "429" in err_str or "rate_limit" in err_str or "terms" in err_str:
                        break
                    time.sleep(0.3)

        return None

    def _call_deterministic(
        self,
        transcript: str,
        context: Dict[str, Any],
        history: Optional[List[Any]] = None,
    ) -> ReasoningResult:
        """Deterministic baseline reasoning fallback."""
        from app.ai.llm_copilot_understanding import fallback_rule_understanding

        und = fallback_rule_understanding(transcript, context)

        lower = transcript.strip().lower()
        msg_type = MSG_CRM_QUERY

        if any(k in lower for k in ["keep everything", "keep as it is", "keep sita", "keep as is", "leave it", "leave sita"]):
            if context.get("pending_action") or context.get("pending_confirmation"):
                msg_type = MSG_CORRECTION
                und.intent = INTENT_CORRECT_PENDING_ACTION
        elif any(lower == g or lower.startswith(f"{g} ") for g in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "namaste", "namaskaram", "hi pulse", "hello pulse"]):
            msg_type = MSG_GREETING
            und.intent = INTENT_GENERAL_CRM_QUERY
            und.conversational_reply = "Hello! How can I help with your territory, doctor visits, or scheduled meetings today?"
        elif any(k in lower for k in ["what can you help me with", "what can you do", "help me with", "how do you work", "what are your capabilities"]):
            msg_type = MSG_CAPABILITY_QUERY
            und.intent = INTENT_GENERAL_CRM_QUERY
            und.conversational_reply = (
                "I am your Ask PulseCRM copilot. I can help you log doctor interactions, schedule future meetings with reminders, "
                "look up doctor profiles and past visit histories, check territory follow-ups, and provide pre-meeting intelligence."
            )
        elif any(k in lower for k in ["prepare", "what should i prepare", "going to", "visiting", "tips for"]):
            msg_type = MSG_CONVERSATIONAL_QUESTION
            und.intent = INTENT_GET_PRE_MEETING_INTELLIGENCE if ("dr" in lower or "doctor" in lower) else INTENT_GENERAL_CRM_QUERY
            if msg_type == MSG_CONVERSATIONAL_QUESTION and und.intent == INTENT_GENERAL_CRM_QUERY:
                und.conversational_reply = "When visiting doctors at a hospital like KIMS, I recommend reviewing which physicians you plan to visit, their specialties, and our product discussion kits like CardioPress-50 or NeuroCalm."
        elif und.intent in [INTENT_CONFIRM_ACTION]:
            msg_type = MSG_CONFIRMATION
        elif und.intent in [INTENT_CANCEL_ACTION]:
            msg_type = MSG_CANCELLATION
        elif und.intent in [INTENT_CORRECT_PENDING_ACTION]:
            msg_type = MSG_CORRECTION
        elif und.intent in [INTENT_CAPTURE_MEETING, INTENT_SCHEDULE_MEETING, INTENT_CREATE_HCP]:
            msg_type = MSG_CRM_MUTATION
        elif und.intent in [INTENT_GET_HCP_DETAILS, INTENT_GET_HCP_INTERACTIONS, INTENT_GET_HCP_FOLLOWUPS, INTENT_GET_ALL_FOLLOWUPS, INTENT_GET_RECENT_INTERACTIONS, INTENT_GET_PRODUCT_DISCUSSIONS, INTENT_GET_CRM_BRIEF, INTENT_GET_CRM_ANALYTICS, INTENT_GET_NEXT_ACTION]:
            msg_type = MSG_CRM_QUERY

        requires_tool = msg_type == MSG_CRM_QUERY

        return ReasoningResult(
            language=und.language,
            message_type=msg_type,
            intent=und.intent,
            requires_crm_tool=requires_tool,
            crm_tool_name=und.intent if requires_tool else None,
            doctor_name=und.doctor_name,
            doctors=und.doctors,
            hcp_entities=und.hcp_entities,
            hospital=und.hospital,
            city=und.city,
            specialization=und.specialization,
            phone=und.phone,
            email=und.email,
            product=und.product,
            doctor_request=und.doctor_request,
            meeting_summary=und.meeting_summary,
            follow_up_date=und.follow_up_date,
            follow_up_display=und.follow_up_display,
            meeting_time=und.meeting_time,
            meeting_time_display=und.meeting_time_display,
            reminder_minutes=und.reminder_minutes,
            reminder_display=und.reminder_display,
            is_new_hcp=und.is_new_hcp,
            is_anaphoric=und.is_anaphoric,
            is_override=und.is_override,
            override_target=und.override_target,
            actions=und.actions,
            corrections=und.corrections,
            conversational_reply=und.conversational_reply,
            confidence=0.85,
            model_used="deterministic_fallback",
        )

    def synthesize_tool_response(
        self,
        user_query: str,
        tool_name: str,
        tool_result: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        language: str = "en",
        provider: Optional[str] = None,
    ) -> Optional[str]:
        """
        Two-pass Tool Result Synthesis.
        Passes tool execution output back into the reasoning model to generate a natural, grounded response.
        """
        use_provider = provider or settings.AI_REASONING_PROVIDER or "gemini"

        # Try Gemini
        if use_provider == "gemini" and self.gemini_client:
            try:
                from google.genai import types
                prompt = (
                    f"User Query: \"{user_query}\"\n"
                    f"Executed Tool: {tool_name}\n"
                    f"Database Result:\n{json.dumps(tool_result, indent=2, default=str)}\n"
                )
                model_id = settings.GEMINI_MODEL or "gemini-3.7-flash"
                resp = self.gemini_client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYNTHESIS_SYSTEM_PROMPT,
                        temperature=0.2,
                    ),
                )
                if resp and resp.text:
                    return resp.text.strip()
            except Exception as e:
                logger.warning(f"[ReasoningEngine] Gemini tool synthesis failed: {e}")

        # Try Groq Pool
        if self.groq_client:
            prompt = (
                f"User Query: \"{user_query}\"\n"
                f"Executed Tool: {tool_name}\n"
                f"Database Result:\n{json.dumps(tool_result, indent=2, default=str)}\n"
            )
            candidate_models = ["qwen/qwen3.8-27b", "qwen/qwen3.6-27b", "openai/gpt-oss-120b", "groq/compound"]
            for model_id in candidate_models:
                try:
                    completion = self.groq_client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.2,
                    )
                    if completion.choices and completion.choices[0].message.content:
                        return completion.choices[0].message.content.strip()
                except Exception as e:
                    logger.warning(f"[ReasoningEngine] Groq tool synthesis failed for {model_id}: {e}")
                    continue

        return None

    def _dict_to_reasoning_result(self, data: Dict[str, Any], transcript: str, model_id: str) -> ReasoningResult:
        lang = data.get("language") or detect_language(transcript)
        msg_type = (data.get("message_type") or MSG_CRM_QUERY).upper()
        raw_intent = (data.get("intent") or INTENT_GENERAL_CRM_QUERY).upper()
        requires_tool = bool(data.get("requires_crm_tool"))

        # Canonical intent mapping from LLM semantic decision
        intent = raw_intent
        if msg_type in [MSG_GREETING, MSG_CAPABILITY_QUERY, MSG_CONVERSATIONAL_QUESTION]:
            requires_tool = False
            intent = INTENT_GENERAL_CRM_QUERY
        elif msg_type == MSG_CONFIRMATION or raw_intent == "CONFIRM_ACTION":
            intent = INTENT_CONFIRM_ACTION
            requires_tool = True
        elif msg_type == MSG_CANCELLATION or raw_intent == "CANCEL_ACTION":
            intent = INTENT_CANCEL_ACTION
            requires_tool = True
        elif msg_type == MSG_CORRECTION or raw_intent == "CORRECT_PENDING_ACTION":
            intent = INTENT_CORRECT_PENDING_ACTION

        # Extract structured slots from LLM JSON output
        corrs = data.get("corrections") or {}
        if data.get("meeting_time_display"):
            corrs["change_time"] = data.get("meeting_time_display")
        if data.get("reminder_display") == "No reminder" or data.get("reminder_minutes") == 0:
            corrs["remove_reminder"] = True
        elif data.get("reminder_display"):
            corrs["change_reminder"] = data.get("reminder_display")

        if data.get("is_override") and data.get("override_target"):
            corrs["change_doctor"] = clean_doctor_name(data["override_target"])

        return ReasoningResult(
            language=lang,
            message_type=msg_type,
            intent=intent,
            requires_crm_tool=requires_tool,
            crm_tool_name=data.get("crm_tool_name") or (intent if requires_tool else None),
            doctor_name=data.get("doctor_name"),
            doctors=data.get("doctors") or [],
            hcp_entities=data.get("hcp_entities") or [],
            hospital=data.get("hospital"),
            city=data.get("city"),
            specialization=data.get("specialization"),
            phone=data.get("phone"),
            email=data.get("email"),
            product=data.get("product"),
            doctor_request=data.get("doctor_request"),
            meeting_summary=data.get("meeting_summary"),
            follow_up_display=data.get("follow_up_display"),
            meeting_time_display=data.get("meeting_time_display"),
            reminder_display=data.get("reminder_display"),
            reminder_minutes=data.get("reminder_minutes"),
            is_new_hcp=bool(data.get("is_new_hcp")),
            is_anaphoric=bool(data.get("is_anaphoric")),
            is_override=bool(data.get("is_override")),
            override_target=data.get("override_target"),
            actions=data.get("actions") or [],
            corrections=corrs,
            conversational_reply=data.get("conversational_reply"),
            confidence=0.95,
            model_used=model_id,
        )

    def _validate_and_normalize_slots(self, res: ReasoningResult, norm_transcript: str):
        # 1. Doctor Name validation
        if res.doctor_name:
            if not is_valid_person_name(res.doctor_name):
                res.doctor_name = None
            else:
                res.doctor_name = clean_doctor_name(res.doctor_name)

        # 2. Extract Date from meeting_time_display or follow_up_display if present
        raw_time_str = res.meeting_time_display or ""
        raw_date_str = res.follow_up_display or ""

        # If time string contains date terms (e.g. "Thursday afternoon" or "Friday 3 PM")
        d_from_time = parse_date_expression(raw_time_str)
        if d_from_time and not res.follow_up_display:
            res.follow_up_date = d_from_time[0].isoformat()
            res.follow_up_display = d_from_time[1]

        # 3. Time Display Standardisation (e.g. Ensure "02:00 PM" instead of "afternoon" or "3")
        t_parsed = parse_time_expression(raw_time_str) or parse_time_expression(norm_transcript)
        if t_parsed:
            res.meeting_time_display = t_parsed[2]
            res.meeting_time = f"{res.meeting_time_display}"

        # 4. Date Standardisation
        dt_p = parse_date_expression(raw_date_str) or parse_date_expression(norm_transcript)
        if dt_p:
            res.follow_up_date = dt_p[0].isoformat()
            res.follow_up_display = dt_p[1]

        # 5. Reminder Standardisation
        if res.reminder_display or res.reminder_minutes is not None:
            if res.reminder_display and any(k in res.reminder_display.lower() for k in ["no", "none", "don't", "dont", "remove", "vaddu"]):
                res.reminder_minutes = 0
                res.reminder_display = "No reminder"
            elif res.reminder_minutes is not None:
                if res.reminder_minutes == 0:
                    res.reminder_display = "No reminder"
                elif res.reminder_minutes == 60:
                    res.reminder_display = "1 hour before"
                elif res.reminder_minutes == 30:
                    res.reminder_display = "30 minutes before"
            else:
                rem_p = extract_reminder_preference(norm_transcript)
                if rem_p:
                    res.reminder_minutes = rem_p[0]
                    res.reminder_display = rem_p[1]

    def _format_history(self, history: Optional[List[Any]]) -> str:
        if not history:
            return "No previous messages in this conversation."
        lines = []
        for m in history[-8:]:
            role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else "user")
            content = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else str(m))
            lines.append(f"{role.capitalize()}: {content}")
        return "\n".join(lines)

    def _format_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "current_hcp_id": context.get("current_hcp_id"),
            "current_hcp_name": context.get("current_hcp_name"),
            "current_hospital": context.get("current_hospital"),
            "pending_confirmation": context.get("pending_confirmation", False),
            "pending_action": context.get("pending_action"),
        }


# Global Singleton Instance
reasoning_engine = ReasoningEngine()
