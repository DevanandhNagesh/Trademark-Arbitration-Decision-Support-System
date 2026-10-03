"""agents/citation_verifier.py

Extracts and verifies case citations from statutory provisions and adversarial
legal analysis against retrieved LandmarkMatch objects and the LANDMARK_CASES
registry in config.py. Flags unverified / hallucinated citations so downstream
reports can annotate them rather than presenting them as confirmed authorities.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set

from config import LANDMARK_CASES
from logging_config import logger

# Regex patterns for Indian case citations
# e.g., "(2011) 5 SCC 532", "AIR 1972 SC 1359", "2021 SCC OnLine Del 1058", "2009 (39) PTC 1 (Del)"
CITATION_PATTERNS = [
    r"\(\d{4}\)\s+\d+\s+SCC\s+\d+",
    r"\b\d{4}\s+SCC\s+OnLine\s+[A-Za-z]+\s+\d+\b",
    r"\bAIR\s+\d{4}\s+[A-Za-z]+\s+\d+\b",
    r"\b\d{4}\s+\(\d+\)\s+PTC\s+\d+(?:\s*\([A-Za-z]+\))?\b",
    r"\(\d{4}\)\s+\d+\s+[A-Za-z\.]+\s+\d+",
    r"\b\d{4}\s+SCR\s+\d+\b",
    r"\b\d{4}\s+\(\d+\)\s+SCC\s+\d+\b",
]

COMPILED_CITATION_RE = re.compile("|".join(CITATION_PATTERNS), flags=re.IGNORECASE)


def _normalize_citation(citation_str: str) -> str:
    """Normalize citation text by removing non-alphanumerics and lowercasing."""
    if not citation_str:
        return ""
    return re.sub(r"[^\w]", "", citation_str).lower()


def _extract_citations_from_text(text: str) -> List[str]:
    """Extract all citation pattern matches from a string."""
    if not text or not isinstance(text, str):
        return []
    return [m.group(0).strip() for m in COMPILED_CITATION_RE.finditer(text)]


def _extract_all_citations(
    statutory_provisions: Optional[List[Dict[str, Any]]],
    adversarial_analysis: Optional[Dict[str, Any]],
) -> List[str]:
    """Recursively collect citation strings from statutory provisions and adversarial analysis."""
    citations: List[str] = []

    # 1. Statutory provisions / legal principles
    if statutory_provisions and isinstance(statutory_provisions, list):
        for provision in statutory_provisions:
            if isinstance(provision, dict):
                for key in (
                    "statute",
                    "statute_text",
                    "judicial_interpretation",
                    "principle_name",
                    "application",
                    "authority",
                    "description",
                ):
                    val = provision.get(key)
                    if isinstance(val, str):
                        citations.extend(_extract_citations_from_text(val))

    # 2. Adversarial legal analysis
    if adversarial_analysis and isinstance(adversarial_analysis, dict):
        # Law for claimant
        for item in adversarial_analysis.get("law_for_claimant", []) or []:
            if isinstance(item, dict):
                for k in ("statute", "statute_text", "case_interpretation", "application"):
                    val = item.get(k)
                    if isinstance(val, str):
                        citations.extend(_extract_citations_from_text(val))

        # Law against claimant
        for item in adversarial_analysis.get("law_against_claimant", []) or []:
            if isinstance(item, dict):
                for k in ("statute", "statute_text", "case_interpretation", "application"):
                    val = item.get(k)
                    if isinstance(val, str):
                        citations.extend(_extract_citations_from_text(val))

        # Options if law against
        for opt in adversarial_analysis.get("options_if_law_against", []) or []:
            if isinstance(opt, dict):
                for k in ("option_title", "strategy", "statute_basis", "case_support", "reasoning"):
                    val = opt.get(k)
                    if isinstance(val, str):
                        citations.extend(_extract_citations_from_text(val))

        # Overall legal position
        overall = adversarial_analysis.get("overall_legal_position")
        if isinstance(overall, str):
            citations.extend(_extract_citations_from_text(overall))

    return citations


def verify_citations(
    statutory_provisions: Optional[List[Dict[str, Any]]] = None,
    adversarial_analysis: Optional[Dict[str, Any]] = None,
    landmark_matches: Optional[List[Any]] = None,
) -> Dict[str, bool]:
    """Extract case citations from legal provisions and adversarial analysis, and

    verify each against retrieved landmark matches and the LANDMARK_CASES registry.

    Returns:
        dict: Mapping of {citation_text: bool} indicating verification status.
    """
    # 1. Build set of known normalized citations
    known_normalized: Set[str] = set()

    # From LANDMARK_CASES registry
    if LANDMARK_CASES and isinstance(LANDMARK_CASES, dict):
        for case_info in LANDMARK_CASES.values():
            if isinstance(case_info, dict):
                cit = case_info.get("citation")
                if cit and isinstance(cit, str):
                    norm = _normalize_citation(cit)
                    if norm:
                        known_normalized.add(norm)

    # From retrieved LandmarkMatch objects
    if landmark_matches and isinstance(landmark_matches, list):
        for lm in landmark_matches:
            cit = getattr(lm, "citation", None)
            if not cit and isinstance(lm, dict):
                cit = lm.get("citation")
            if cit and isinstance(cit, str):
                norm = _normalize_citation(cit)
                if norm:
                    known_normalized.add(norm)

    # 2. Extract citations from inputs
    extracted_citations = _extract_all_citations(statutory_provisions, adversarial_analysis)

    # 3. Verify each citation
    verification_results: Dict[str, bool] = {}

    for raw_cit in extracted_citations:
        if not raw_cit or raw_cit in verification_results:
            continue

        raw_norm = _normalize_citation(raw_cit)
        if not raw_norm:
            verification_results[raw_cit] = False
            continue

        # Check exact or partial normalized match
        is_verified = False
        if raw_norm in known_normalized:
            is_verified = True
        else:
            for k_norm in known_normalized:
                if raw_norm == k_norm or (
                    len(raw_norm) >= 6 and (raw_norm in k_norm or k_norm in raw_norm)
                ):
                    is_verified = True
                    break

        verification_results[raw_cit] = is_verified

    logger.info(
        f"Verified {len(verification_results)} citation(s): "
        f"{sum(1 for v in verification_results.values() if v)} verified, "
        f"{sum(1 for v in verification_results.values() if not v)} unverified"
    )

    return verification_results
