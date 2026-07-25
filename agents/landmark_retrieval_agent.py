"""Landmark case retrieval agent — ZERO LLM calls.

Primary source  : iKanoon API (dynamic, live Indian case law)
Fallback source : ChromaDB semantic search (local, offline)
Final fallback  : Hard-coded LANDMARK_CASES registry

All post-retrieval logic (deduplication, category reordering, Booz Allen
indicator cleanup, arbitrability filtering) is unchanged from the ChromaDB
version so the rest of the system sees an identical interface.
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import List, Optional

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    CHROMA_COLLECTION,
    CHROMA_PATH,
    EMBEDDING_MODEL,
    IKANOON_API_KEY,
    LANDMARK_CASES,
)
from logging_config import logger

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class LandmarkMatch:
    case_key: str
    case_name: str
    citation: str
    year: int
    court: str
    principle: str
    relevant_text: str
    similarity_score: float
    category: str


# ---------------------------------------------------------------------------
# iKanoon API helpers
# ---------------------------------------------------------------------------

IKANOON_SEARCH_URL = "https://api.indiankanoon.org/search/"
IKANOON_DOC_URL    = "https://api.indiankanoon.org/doc/{doc_id}/"

# How many raw iKanoon hits to fetch before mapping to LANDMARK_CASES
_IKANOON_FETCH_MULTIPLIER = 5

# Seconds to wait between paginated iKanoon requests (rate-limit safety)
_IKANOON_REQUEST_DELAY = 0.3


def _detect_dispute_type(dispute_description: str) -> str:
    """Infer dispute type from free-form description."""
    desc = dispute_description.lower()
    if "passing off" in desc:
        return "passing_off"
    if "assignment" in desc:
        return "assignment"
    if "license" in desc or "licence" in desc or "licensing" in desc:
        return "licensing"
    if "brand similarity" in desc or "deceptive similarity" in desc or "phonetic" in desc:
        return "brand_similarity"
    if "infringement" in desc:
        return "infringement"
    return "trademark"


def _build_ikanoon_query(dispute_description: str) -> str:
    """
    Construct a focused iKanoon full-text search query from the free-form
    dispute description using dispute-type-aware legal keywords.

    Requirements
    ------------
    - Keep under 120 characters.
    - Avoid party-specific facts.
    - Prefer Supreme Court / High Court precedent cues.
    """
    dispute_type = _detect_dispute_type(dispute_description)

    base = ["Supreme Court", "High Court", "India"]
    type_queries = {
        "infringement": "trademark infringement deceptive similarity",
        "passing_off": "passing off trademark landmark judgment",
        "licensing": "trademark licensing arbitration landmark",
        "assignment": "trademark assignment ownership dispute",
        "brand_similarity": "deceptive similarity trademark landmark",
        "trademark": "trademark dispute landmark judgment",
    }
    query = " ".join([type_queries.get(dispute_type, type_queries["trademark"])] + base)
    return query[:120].strip()


def _fetch_ikanoon_results(query: str, max_results: int) -> list[dict]:
    """
    Call the iKanoon /search/ endpoint and return a list of raw hit dicts.

    Each dict contains at minimum:
        tid       — iKanoon document ID
        title     — case name as indexed
        citation  — citation string (may be empty)
        publishdate — YYYY-MM-DD or year string
        court     — court name string
        headline  — short excerpt / headnote

    Returns [] on any network or auth failure (caller handles fallback).
    """
    if not IKANOON_API_KEY:
        raise ValueError("IKANOON_API_KEY is not set in environment / config.py")

    headers = {
        "Authorization": f"Token {IKANOON_API_KEY}",
        "Accept":        "application/json",
    }

    hits: list[dict] = []
    pagenum = 0
    per_page = 10  # iKanoon default page size

    while len(hits) < max_results:
        params = {
            "formInput": query,
            "pagenum":   pagenum,
        }
        resp = requests.post(
            IKANOON_SEARCH_URL,
            headers=headers,
            data=params,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        docs = data.get("docs", [])
        if not docs:
            break  # no more pages

        hits.extend(docs)
        pagenum += 1

        if len(docs) < per_page:
            break  # last page reached

        time.sleep(_IKANOON_REQUEST_DELAY)

    return hits[:max_results]


def _fetch_ikanoon_snippet(doc_id: str) -> str:
    """
    Fetch the first 500 characters of the full judgement text for a given
    iKanoon document ID.  Used to populate `relevant_text` on the match.
    Returns empty string on failure.
    """
    if not IKANOON_API_KEY:
        return ""
    try:
        headers = {
            "Authorization": f"Token {IKANOON_API_KEY}",
            "Accept":        "application/json",
        }
        resp = requests.get(
            IKANOON_DOC_URL.format(doc_id=doc_id),
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        doc_data = resp.json()
        # iKanoon returns the full text under the "doc" key
        full_text: str = doc_data.get("doc", "") or doc_data.get("judgement", "")
        # Strip basic HTML tags that iKanoon sometimes includes
        full_text = re.sub(r"<[^>]+>", " ", full_text)
        full_text = re.sub(r"\s+", " ", full_text).strip()
        return full_text[:500]
    except Exception as e:
        logger.warning(f"Failed to fetch iKanoon snippet for doc {doc_id}: {e}")
        return ""


def _map_ikanoon_hit_to_landmark(hit: dict) -> Optional[LandmarkMatch]:
    """
    Try to map a raw iKanoon search hit to a known entry in LANDMARK_CASES.

    Matching strategy (ordered by specificity):
    1. Exact citation match            — most reliable
    2. Case-name substring match       — moderately reliable
    3. Year + partial name match       — last resort

    Returns None when no mapping can be established so the caller can fall
    back to a dynamic LandmarkMatch.

    The corresponding iKanoon-integration prompt (used by the orchestrator):
        "For each iKanoon search result, check whether its title or citation
         matches any entry in LANDMARK_CASES.  Prefer citation match over name
         match.  If no match, skip the result.  Never fabricate a case_key."
    """
    raw_title    = (hit.get("title") or "").lower()
    raw_citation = (hit.get("citation") or "").strip()
    raw_year_str = str(hit.get("publishdate") or "")
    raw_year     = int(raw_year_str[:4]) if raw_year_str[:4].isdigit() else 0

    for case_key, info in LANDMARK_CASES.items():
        # 1. Citation match (case-insensitive, stripped)
        if raw_citation and info["citation"].lower() == raw_citation.lower():
            return _build_match_from_registry(
                case_key, info,
                relevant_text=hit.get("headline", info["principle"])[:500],
                similarity_score=0.95,
            )

        # 2. Case-name substring match
        registered_name_lower = info["name"].lower()
        # Use first meaningful token (>4 chars) from registered name for fuzzy match
        tokens = [t for t in registered_name_lower.split() if len(t) > 4]
        if tokens and any(token in raw_title for token in tokens[:2]):
            if raw_year == 0 or abs(raw_year - info["year"]) <= 1:
                return _build_match_from_registry(
                    case_key, info,
                    relevant_text=hit.get("headline", info["principle"])[:500],
                    similarity_score=0.75,
                )

    return None  # no mapping found


def _build_dynamic_landmark_from_ikanoon(hit: dict) -> LandmarkMatch:
    title = (hit.get("title") or "Unknown Case").strip()
    citation = (hit.get("citation") or "Unknown Citation").strip()
    raw_year_str = str(hit.get("publishdate") or "")
    year = int(raw_year_str[:4]) if raw_year_str[:4].isdigit() else 0
    court = (hit.get("court") or "Indian Court").strip()
    headline = (hit.get("headline") or "").strip()
    principle = headline[:300] if headline else title
    relevant_text = headline[:500] if headline else title

    raw_key = f"{title}|{citation}|{year}|{court}"
    case_hash = hashlib.md5(raw_key.encode("utf-8")).hexdigest()[:12]
    case_key = f"ik_dynamic_{case_hash}"

    return LandmarkMatch(
        case_key=case_key,
        case_name=title,
        citation=citation or "Unknown Citation",
        year=year or 0,
        court=court or "Indian Court",
        principle=principle,
        relevant_text=relevant_text,
        similarity_score=0.7,
        category="dynamic_ikanoon",
    )


def _build_match_from_registry(
    case_key: str,
    info: dict,
    relevant_text: str,
    similarity_score: float,
) -> LandmarkMatch:
    return LandmarkMatch(
        case_key=case_key,
        case_name=info["name"],
        citation=info["citation"],
        year=info["year"],
        court=info["court"],
        principle=info["principle"],
        relevant_text=relevant_text or info["principle"],
        similarity_score=round(similarity_score, 4),
        category=info["category"],
    )


def _retrieve_via_ikanoon(
    dispute_description: str,
    n_results: int,
) -> list[LandmarkMatch]:
    """
    Full iKanoon retrieval pipeline:
        build query → fetch hits → map to LANDMARK_CASES → deduplicate

    Raises on auth / network failure so the caller can fall back to ChromaDB.
    """
    query = _build_ikanoon_query(dispute_description)
    fetch_n = max(n_results * _IKANOON_FETCH_MULTIPLIER, 20)

    raw_hits = _fetch_ikanoon_results(query, max_results=fetch_n)

    seen_keys: set[str] = set()
    matches: list[LandmarkMatch] = []

    for hit in raw_hits:
        match = _map_ikanoon_hit_to_landmark(hit)
        if match is None:
            match = _build_dynamic_landmark_from_ikanoon(hit)
        if match.case_key in seen_keys:
            continue
        seen_keys.add(match.case_key)

        # Optionally enrich relevant_text with full-doc snippet
        if not match.relevant_text or match.relevant_text == match.principle:
            doc_id = str(hit.get("tid") or "")
            if doc_id:
                snippet = _fetch_ikanoon_snippet(doc_id)
                if snippet:
                    match.relevant_text = snippet

        matches.append(match)
        if len(matches) >= n_results * 2:  # gather extras for reordering
            break

    return matches


# ---------------------------------------------------------------------------
# ChromaDB fallback (identical to original implementation)
# ---------------------------------------------------------------------------

def _get_chroma_collection():
    """Get ChromaDB collection (lazy import — only used as fallback)."""
    import pydantic_v1_compat  # noqa: F401
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return client.get_collection(
        name=CHROMA_COLLECTION,
        embedding_function=embedding_fn,
    )


def _retrieve_via_chromadb(
    dispute_description: str,
    n_results: int,
) -> list[LandmarkMatch]:
    """Semantic search via local ChromaDB — unchanged from original agent."""
    collection = _get_chroma_collection()
    query_n = max(n_results * 3, 10)
    results = collection.query(
        query_texts=[dispute_description],
        n_results=query_n,
    )

    seen_case_keys: set[str] = set()
    matches: list[LandmarkMatch] = []

    for i in range(len(results["ids"][0])):
        case_key = results["metadatas"][0][i].get("case_key", "unknown")
        if case_key in seen_case_keys or case_key not in LANDMARK_CASES:
            continue
        seen_case_keys.add(case_key)

        distance   = results["distances"][0][i]
        similarity = 1 - distance
        info       = LANDMARK_CASES[case_key]

        matches.append(LandmarkMatch(
            case_key=case_key,
            case_name=info["name"],
            citation=info["citation"],
            year=info["year"],
            court=info["court"],
            principle=info["principle"],
            relevant_text=results["documents"][0][i][:500],
            similarity_score=round(similarity, 4),
            category=info["category"],
        ))

    return matches


# ---------------------------------------------------------------------------
# Public interface — retrieve_landmarks (signature unchanged)
# ---------------------------------------------------------------------------

def retrieve_landmarks(
    dispute_description: str,
    arbitrability_result=None,
    n_results: int = 3,
) -> List[LandmarkMatch]:
    """
    Retrieve top landmark cases for the given dispute description.

    Retrieval order
    ---------------
    1. iKanoon API          — live, dynamic Indian case law
    2. ChromaDB             — local semantic search (offline fallback)
    3. get_fallback_landmarks() — hard-coded registry (last resort)

    All post-retrieval logic (Booz Allen cleanup, category reordering,
    arbitrability filtering, supplement from fallback) is applied uniformly
    regardless of which source succeeded.
    """
    matches: list[LandmarkMatch] = []
    seen_case_keys: set[str] = set()

    # ── 1. Primary: iKanoon ──────────────────────────────────────────
    ikanoon_ok = False
    try:
        matches = _retrieve_via_ikanoon(dispute_description, n_results)
        seen_case_keys = {m.case_key for m in matches}
        ikanoon_ok = True
        logger.info(f"[landmark_retrieval] iKanoon returned {len(matches)} results.")
    except Exception as ik_err:
        logger.warning(f"[landmark_retrieval] iKanoon failed: {ik_err}. Trying ChromaDB...")

    # ── 2. Secondary: ChromaDB ───────────────────────────────────────
    if not ikanoon_ok:
        try:
            matches = _retrieve_via_chromadb(dispute_description, n_results)
            seen_case_keys = {m.case_key for m in matches}
            logger.info(f"[landmark_retrieval] ChromaDB returned {len(matches)} results.")
        except Exception as chroma_err:
            logger.warning(f"[landmark_retrieval] ChromaDB failed: {chroma_err}. Using registry fallback.")

    # ── 3. Supplement if still below n_results ───────────────────────
    if len(matches) < n_results:
        fallback = get_fallback_landmarks(arbitrability_result)
        for fb in fallback:
            if fb.case_key not in seen_case_keys:
                matches.append(fb)
                seen_case_keys.add(fb.case_key)
                if len(matches) >= n_results:
                    break

    # ── Post-retrieval: Booz Allen indicator cleanup ─────────────────
    if arbitrability_result:
        booz = getattr(arbitrability_result, "booz_allen_test", None)
        if booz and isinstance(booz.get("personam_indicators"), list):
            if not booz["passes"]:
                booz["personam_indicators"] = [
                    ind for ind in booz["personam_indicators"]
                    if "is contractual in nature" not in ind
                ]

    # ── Post-retrieval: category reordering ─────────────────────────
    matches = _reorder_by_dispute_category(matches, arbitrability_result)

    # ── Post-retrieval: exclude arbitrability-only when ARBITRABLE ───
    if arbitrability_result and getattr(arbitrability_result, "is_arbitrable", False):
        matches = [
            m for m in matches
            if m.case_key not in {"booz_allen", "vidya_drolia"}
        ]

    return matches[:n_results]


# ---------------------------------------------------------------------------
# Post-retrieval helpers (unchanged from original)
# ---------------------------------------------------------------------------

def _extract_dispute_type(arbitrability_result) -> str:
    if not arbitrability_result:
        return ""
    booz = getattr(arbitrability_result, "booz_allen_test", None) or {}
    for indicator_list in [booz.get("rem_indicators", []), booz.get("personam_indicators", [])]:
        for ind in indicator_list:
            m = re.search(r"Dispute type '(.+?)'", ind)
            if m:
                return m.group(1)
    return ""


def _make_landmark_from_key(case_key: str) -> LandmarkMatch:
    info = LANDMARK_CASES[case_key]
    return LandmarkMatch(
        case_key=case_key,
        case_name=info["name"],
        citation=info["citation"],
        year=info["year"],
        court=info["court"],
        principle=info["principle"],
        relevant_text=info["principle"],
        similarity_score=0.5,
        category=info["category"],
    )


def _reorder_by_dispute_category(
    matches: List[LandmarkMatch],
    arbitrability_result,
) -> List[LandmarkMatch]:
    """Reorder matches by priority/depriority categories based on dispute type.
    Never removes results — only reorders them."""
    if not arbitrability_result:
        return matches

    is_arbitrable      = getattr(arbitrability_result, "is_arbitrable", False)
    dispute_type_lower = _extract_dispute_type(arbitrability_result).lower()

    if not dispute_type_lower:
        return matches

    # ── NOT ARBITRABLE / infringement / passing off ──────────────────
    if not is_arbitrable and any(
        kw in dispute_type_lower
        for kw in ["brand similarity", "trademark infringement", "passing off", "infringement"]
    ):
        priority_cats   = {"trademark_similarity", "trademark_infringement"}
        secondary_cats  = {"arbitrability"}
        depriority_cats = {"ipr_licensing", "trademark_licensing", "trademark_assignment"}

        forced_keys = ["amritdhara", "parle_products", "cadila"]
        existing_keys = {m.case_key for m in matches}

        forced_matches = []
        for fk in forced_keys:
            found = [m for m in matches if m.case_key == fk]
            if found:
                forced_matches.append(found[0])
            elif fk in LANDMARK_CASES:
                forced_matches.append(_make_landmark_from_key(fk))

        remaining         = [m for m in matches if m.case_key not in forced_keys]
        priority_rem      = [m for m in remaining if m.category in priority_cats]
        secondary_rem     = [m for m in remaining if m.category in secondary_cats]
        neutral_rem       = [m for m in remaining if m.category not in priority_cats
                             and m.category not in secondary_cats
                             and m.category not in depriority_cats]
        depriority_rem    = [m for m in remaining if m.category in depriority_cats]

        return forced_matches + priority_rem + secondary_rem + neutral_rem + depriority_rem

    if not is_arbitrable:
        return matches

    # ── ARBITRABLE path ──────────────────────────────────────────────
    category_map = {
        "license":       {"priority": {"ipr_licensing", "trademark_licensing", "trademark_assignment"},
                          "depriority": {"trademark_territoriality", "trademark_similarity"}},
        "franchise":     {"priority": {"ipr_licensing", "trademark_licensing", "trademark_assignment"},
                          "depriority": {"trademark_territoriality", "trademark_similarity"}},
        "assignment":    {"priority": {"trademark_assignment", "ipr_licensing"},
                          "depriority": {"trademark_territoriality", "trademark_similarity"}},
        "infringement":  {"priority": {"trademark_infringement", "trademark_similarity"},
                          "depriority": {"ipr_licensing", "trademark_licensing"}},
        "passing off":   {"priority": {"trademark_infringement", "trademark_similarity"},
                          "depriority": {"ipr_licensing", "trademark_licensing"}},
        "brand similarity": {"priority": {"trademark_infringement", "trademark_similarity"},
                             "depriority": {"ipr_licensing", "trademark_licensing"}},
    }

    selected = next(
        (mapping for keyword, mapping in category_map.items() if keyword in dispute_type_lower),
        None,
    )
    if selected is None:
        return matches

    priority_cats   = selected["priority"]
    depriority_cats = selected["depriority"]

    priority_m   = [m for m in matches if m.category in priority_cats]
    neutral_m    = [m for m in matches if m.category not in priority_cats and m.category not in depriority_cats]
    depriority_m = [m for m in matches if m.category in depriority_cats]

    return priority_m + neutral_m + depriority_m


def get_fallback_landmarks(arbitrability_result=None) -> List[LandmarkMatch]:
    """Return default landmark cases when all dynamic sources are unavailable."""
    default_keys = ["booz_allen", "vidya_drolia", "hero_electric"]

    if arbitrability_result and hasattr(arbitrability_result, "applicable_landmark"):
        applicable = arbitrability_result.applicable_landmark
        if applicable and applicable not in default_keys:
            default_keys.insert(0, applicable)

    matches = []
    for case_key in default_keys:
        if case_key not in LANDMARK_CASES:
            continue
        info = LANDMARK_CASES[case_key]
        matches.append(LandmarkMatch(
            case_key=case_key,
            case_name=info["name"],
            citation=info["citation"],
            year=info["year"],
            court=info["court"],
            principle=info["principle"],
            relevant_text=info["principle"],
            similarity_score=0.5,
            category=info["category"],
        ))

    return matches[:3]


# ---------------------------------------------------------------------------
# Applicability analysis (unchanged from original)
# ---------------------------------------------------------------------------

def analyze_landmark_applicability(dispute: dict, landmark: LandmarkMatch) -> dict:
    """Analyze how a landmark case applies to the current dispute. No LLM calls."""
    dispute_type = dispute.get("dispute_type", "").lower()
    has_contract = dispute.get("has_contract", False)
    right_source = dispute.get("right_source", "statute")

    similarities: list[str] = []
    differences:  list[str] = []

    if landmark.category == "arbitrability":
        if has_contract:
            similarities.append("Both cases involve parties with a prior contractual relationship")
        else:
            similarities.append("Both cases involve disputes over trademark rights without a direct contract")
        similarities.append("Both require determination of whether the dispute is arbitrable under Indian law")
        if right_source == "contract":
            similarities.append("Rights in both cases arise from contractual obligations (in personam)")
        else:
            differences.append("In the landmark case, the right source analysis differs from the current dispute")

    elif landmark.category in ["trademark_similarity", "trademark_infringement"]:
        similarities.append("Both cases involve allegations of trademark similarity or infringement")
        similarities.append("Consumer confusion and deceptive similarity are central issues in both")
        if not has_contract:
            similarities.append("Neither case involves a prior contractual relationship between the parties")
        else:
            differences.append("The current dispute involves a contractual relationship, unlike the landmark case")

    elif landmark.category == "trademark_assignment":
        if "assignment" in dispute_type:
            similarities.append("Both cases involve trademark assignment disputes")
            similarities.append("The finality and irrevocability of trademark assignment is at issue in both")
        else:
            differences.append("The current dispute does not directly involve trademark assignment")
        if has_contract:
            similarities.append("Both involve contractual obligations governing the trademark")

    elif landmark.category in ["trademark_licensing", "ipr_licensing"]:
        if any(kw in dispute_type for kw in ["license", "licence", "distribution"]):
            similarities.append("Both cases involve licensing or distribution agreements concerning trademarks")
            similarities.append("Post-termination use of licensed trademark is at issue in both")
        else:
            differences.append("The current dispute does not involve a licensing arrangement")
        if has_contract:
            similarities.append("Both arise from contractual relationships between the parties")

    elif landmark.category == "trademark_territoriality":
        similarities.append("Both cases involve questions of trademark recognition and territorial rights")
        if not has_contract:
            similarities.append("Both involve parties without a prior contractual relationship")

    elif landmark.category == "procedural":
        similarities.append("Procedural aspects of arbitration timelines are relevant to both")
        if has_contract:
            similarities.append("Both involve disputes arising from contractual relationships")

    if len(similarities) < 2:
        similarities.append("Both cases are governed by Indian trademark law and arbitration jurisprudence")
    if len(similarities) < 2:
        similarities.append("The legal principles established apply to the facts of the current dispute")

    if landmark.year < 2020 and has_contract:
        differences.append(
            f"The landmark case ({landmark.year}) predates recent developments "
            "in arbitrability jurisprudence (Vidya Drolia 2021, Mangayarkarasi 2025)"
        )
    if landmark.court == "Supreme Court of India":
        differences.append(
            "The landmark is a Supreme Court decision with binding authority, "
            "while the current dispute may involve different factual nuances"
        )
    if not differences:
        differences.append(
            "The specific factual matrix of the current dispute may differ in material particulars"
        )

    binding_force = "Binding" if "Supreme Court" in landmark.court else "Persuasive"

    return {
        "case_key":             landmark.case_key,
        "case_name":            landmark.case_name,
        "similarities":         similarities,
        "differences":          differences,
        "applicable_principle": landmark.principle,
        "binding_force":        binding_force,
    }