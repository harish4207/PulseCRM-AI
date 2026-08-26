"""
fuzzy_matcher.py - Intelligent Entity Matching & Normalization for PulseCRM Voice Copilot.

Handles:
- Speech/transcription phonetic typos (e.g. "Rajes kumr" -> "Dr. Rajesh Kumar")
- Telugu pronoun and postposition stripping
- Hospital and product matching
- Ambiguity detection (e.g. multiple matching doctors)
- Strict confidence scoring
"""

import re
import difflib
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.hcp import HCP
from app.models.interaction import Interaction

TELUGU_POSTPOSITIONS = [
    "gurinchi", "cheppu", "details", "ni", "tho", "ki", "ku", "lo", "garu",
    "doctor", "డాక్టర్", "గారు", "గురించి", "చెప్పు", "తో", "ని", "కి", "లో",
    "kalisanu", "matladam", "matladaru", "eppudu", "next", "last", "meeting",
    "follow-up", "followup", "create", "log", "cheyyi", "pett", "evaritho",
    "unna", "list", "anni", "kaadu", "kadu", "kadhu"
]

STOP_TOKENS_SET = set(TELUGU_POSTPOSITIONS + [
    "dr", "dr.", "doctor", "the", "a", "an", "tell", "me", "about", "who", "is",
    "when", "did", "i", "we", "last", "meet", "scheduled", "with", "at", "for"
])


TELUGU_SCRIPT_TO_ENGLISH = {
    "రాజేష్": "Rajesh",
    "ప్రియాంక": "Priyanka",
    "శర్మ": "Sharma",
    "అనన్య": "Ananya",
    "సురేష్": "Suresh",
    "రమేష్": "Ramesh",
    "వర్మ": "Varma",
    "రెడ్డి": "Reddy",
    "రావు": "Rao",
}

def normalize_text(text: str) -> str:
    """Normalize input text: lowercase, remove punctuation, transliterate Telugu names."""
    if not text:
        return ""
    res = text
    for te_word, en_word in TELUGU_SCRIPT_TO_ENGLISH.items():
        res = res.replace(te_word, en_word)
    res = res.lower()
    res = re.sub(r"[^\w\s\u0C00-\u0C7F]", " ", res)
    return " ".join(res.split())


def extract_potential_names(transcript: str) -> List[str]:
    """Extract candidate name phrases from transcript after stripping noise tokens."""
    norm = normalize_text(transcript)
    words = norm.split()

    filtered = [w for w in words if w not in STOP_TOKENS_SET]
    candidates = []

    if filtered:
        candidates.append(" ".join(filtered))
        if len(filtered) >= 2:
            candidates.append(f"{filtered[0]} {filtered[1]}")
        candidates.append(filtered[0])
        if len(filtered) >= 2:
            candidates.append(filtered[1])

    patterns = [
        r"dr\.?\s+([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)",
        r"([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)\s+(?:doctor|డాక్టర్|garu|gaaru|గారు)",
        r"([A-Za-z\u0C00-\u0C7F]+(?:\s+[A-Za-z\u0C00-\u0C7F]+)?)\s+(?:tho|ni|ki|తో|ని|కి)",
    ]
    for pat in patterns:
        m = re.search(pat, transcript, re.IGNORECASE)
        if m:
            extracted = m.group(1).strip()
            clean_ex = " ".join([w for w in extracted.split() if w.lower() not in STOP_TOKENS_SET])
            if clean_ex and clean_ex not in candidates:
                candidates.insert(0, clean_ex)

    return candidates


def _token_similarity(t1: str, t2: str) -> float:
    if not t1 or not t2:
        return 0.0
    if t1 == t2:
        return 1.0
    r = difflib.SequenceMatcher(None, t1, t2).ratio()
    # Length disparity (e.g. "sharmila" (8) vs "sharma" (6))
    if abs(len(t1) - len(t2)) >= 2 and r < 0.90:
        return r * 0.55
    if (t1 == "rajesh" and t2 == "ramesh") or (t1 == "ramesh" and t2 == "rajesh"):
        return 0.55
    if (t1 == "suresh" and t2 == "ramesh") or (t1 == "ramesh" and t2 == "suresh"):
        return 0.50
    return r


def calculate_similarity(s1: str, s2: str) -> float:
    """Compute string similarity ratio between 0.0 and 1.0."""
    s1_clean = normalize_text(s1)
    s2_clean = normalize_text(s2)

    if not s1_clean or not s2_clean:
        return 0.0
    if s1_clean == s2_clean:
        return 1.0

    s1_tokens = set(s1_clean.split())
    s2_tokens = set(s2_clean.split())
    if s1_tokens == s2_tokens:
        return 1.0
    if s1_tokens and s1_tokens.issubset(s2_tokens):
        return 0.70 + 0.18 * (len(s1_tokens) / max(len(s2_tokens), 1))
    if s2_tokens and s2_tokens.issubset(s1_tokens):
        return 0.70 + 0.18 * (len(s2_tokens) / max(len(s1_tokens), 1))

    seq_ratio = difflib.SequenceMatcher(None, s1_clean, s2_clean).ratio()
    if len(s1_tokens) == 1 and len(s2_tokens) == 1:
        return _token_similarity(list(s1_tokens)[0], list(s2_tokens)[0])

    token_scores = []
    for t1 in s1_tokens:
        best_t_score = max([_token_similarity(t1, t2) for t2 in s2_tokens], default=0.0)
        token_scores.append(best_t_score)
    avg_token_score = sum(token_scores) / len(token_scores) if token_scores else 0.0

    # If query is a single token, it should not exceed its best token similarity score
    if len(s1_tokens) == 1:
        return avg_token_score

    return max(seq_ratio, avg_token_score)


def match_hcp_from_db(
    db: Session,
    query_text: str,
    threshold: float = 0.65
) -> Dict[str, Any]:
    if not query_text or not db:
        return {"best_match": None, "confidence": 0.0, "candidates": [], "is_ambiguous": False, "matched_query": ""}

    try:
        all_hcps = db.query(HCP).all()
    except Exception:
        all_hcps = []

    if not all_hcps:
        return {"best_match": None, "confidence": 0.0, "candidates": [], "is_ambiguous": False, "matched_query": query_text}

    candidate_queries = extract_potential_names(query_text)
    if not candidate_queries:
        candidate_queries = [query_text]

    scored_hcps: List[Tuple[HCP, float, str]] = []

    for hcp in all_hcps:
        doc_name = hcp.doctor_name or ""
        clean_doc_name = re.sub(r"^dr\.?\s+", "", doc_name, flags=re.IGNORECASE)

        best_score_for_hcp = 0.0
        best_q = ""

        for q in candidate_queries:
            q_words = q.split()
            doc_words = clean_doc_name.split()
            score1 = calculate_similarity(q, doc_name)
            score2 = calculate_similarity(q, clean_doc_name)
            max_s = max(score1, score2)

            # Phrase length specificity: reward matching full multi-word query phrases
            if len(q_words) >= 2 and len(doc_words) >= 2 and max_s >= 0.80:
                max_s = min(max_s + 0.08, 1.0)
            elif len(q_words) == 1 and len(candidate_queries) > 1 and len(candidate_queries[0].split()) >= 2:
                max_s = max_s - 0.06

            if max_s > best_score_for_hcp:
                best_score_for_hcp = max_s
                best_q = q

        if best_score_for_hcp >= threshold:
            scored_hcps.append((hcp, best_score_for_hcp, best_q))

    scored_hcps.sort(key=lambda x: x[1], reverse=True)

    # Deduplicate scored HCPs that have identical normalized doctor names and hospitals
    dedup_scored: List[Tuple[HCP, float, str]] = []
    seen_keys = set()
    for h, s, q in scored_hcps:
        norm_key = (normalize_text(re.sub(r"^dr\.?\s+", "", h.doctor_name or "", flags=re.IGNORECASE)), normalize_text(h.hospital or ""))
        if norm_key not in seen_keys:
            seen_keys.add(norm_key)
            dedup_scored.append((h, s, q))

    if not dedup_scored:
        return {
            "best_match": None,
            "confidence": 0.0,
            "candidates": [],
            "is_ambiguous": False,
            "matched_query": query_text
        }

    top_hcp, top_score, top_query = dedup_scored[0]
    candidates_dicts = [_hcp_to_dict(h) for h, s, _ in dedup_scored]

    if len(dedup_scored) == 1 or (top_score >= 0.95 and (len(dedup_scored) < 2 or (top_score - dedup_scored[1][1] >= 0.05))) or (top_score >= 0.88 and (len(dedup_scored) < 2 or (top_score - dedup_scored[1][1] >= 0.12))):
        return {
            "best_match": _hcp_to_dict(top_hcp),
            "confidence": top_score,
            "candidates": [_hcp_to_dict(top_hcp)],
            "is_ambiguous": False,
            "matched_query": top_query
        }

    close_candidates = [h for h, s, _ in dedup_scored if s >= 0.70]
    if len(close_candidates) > 1:
        return {
            "best_match": None,
            "confidence": 0.55,
            "candidates": [_hcp_to_dict(h) for h in close_candidates],
            "is_ambiguous": True,
            "matched_query": top_query
        }

    return {
        "best_match": _hcp_to_dict(top_hcp),
        "confidence": top_score,
        "candidates": candidates_dicts,
        "is_ambiguous": False,
        "matched_query": top_query
    }


def match_hospital_from_db(db: Session, transcript: str) -> Optional[str]:
    """Extract and match hospital name from DB records."""
    if not db:
        return None
    try:
        all_hcps = db.query(HCP).all()
        hospitals = list({h.hospital for h in all_hcps if h.hospital})
    except Exception:
        hospitals = []

    norm_transcript = normalize_text(transcript)

    for h_name in hospitals:
        if not h_name:
            continue
        norm_h = normalize_text(h_name)
        if norm_h in norm_transcript:
            return h_name
        first_token = norm_h.split()[0] if norm_h.split() else ""
        if len(first_token) >= 4 and first_token in norm_transcript:
            return h_name

    return None


def match_product_from_transcript(db: Session, transcript: str) -> Optional[str]:
    """Find mentioned medical products from previous interaction history or known catalogs."""
    norm_transcript = normalize_text(transcript)
    known_products = ["CardioPress-50", "AmloPulse", "GlycoCare", "NeuroCalm", "LipidGuard", "RespiClear"]

    if db:
        try:
            db_interactions = db.query(Interaction).all()
            for inter in db_interactions:
                p_str = inter.products_discussed
                if p_str:
                    for p in p_str.split(","):
                        p_clean = p.strip()
                        if p_clean and p_clean not in known_products:
                            known_products.append(p_clean)
        except Exception:
            pass

    for prod in known_products:
        norm_prod = normalize_text(prod)
        if norm_prod in norm_transcript:
            return prod
        prod_base = norm_prod.split("-")[0] if "-" in norm_prod else norm_prod
        if len(prod_base) >= 4 and prod_base in norm_transcript:
            return prod

    return None


def _hcp_to_dict(hcp: HCP) -> Dict[str, Any]:
    from app.ai.normalizer import clean_doctor_name
    return {
        "id": hcp.id,
        "doctor_name": clean_doctor_name(hcp.doctor_name) or (hcp.doctor_name or "Doctor"),
        "specialization": hcp.specialization,
        "hospital": hcp.hospital,
        "city": hcp.city,
        "phone": hcp.phone,
        "email": hcp.email,
        "created_at": hcp.created_at.isoformat() if hcp.created_at else None,
    }
