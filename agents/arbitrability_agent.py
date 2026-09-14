"""Arbitrability determination agent — ZERO LLM calls, pure deterministic logic."""

import os
import re
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LANDMARK_CASES, FOURFOLD_TEST


@dataclass
class ArbitrabilityResult:
    is_arbitrable: bool
    status: str
    right_type: str
    booz_allen_test: dict = field(default_factory=dict)
    vidya_drolia_test: dict = field(default_factory=dict)
    primary_authority: str = ""
    reason: str = ""
    recommendation: str = ""
    applicable_landmark: str = ""
    narrative_warning: dict = field(default_factory=dict)
    clause_text_contradiction: bool = False
    # Narrative severity fields — set when the free-text description strongly
    # implies in rem rights while the structured dispute_type suggests arbitrability.
    # The verdict is NOT auto-flipped; this is a prominence signal only.
    requires_manual_review: bool = False
    review_reason: str = ""
    # Contract-narrative mismatch — set when has_contract=True but the
    # dispute_description contains no contractual language at all.
    # Purely informational; does not affect is_arbitrable.
    contract_narrative_mismatch: dict = field(default_factory=dict)


def apply_booz_allen_test(dispute: dict) -> dict:
    """Apply the Booz Allen right in rem vs right in personam test.
    
    NOT ARBITRABLE if: has_contract=False OR right_source='statute' OR
    dispute_type contains registration/cancellation/rectification/passing off.
    """
    has_contract = dispute.get("has_contract", False)
    right_source = dispute.get("right_source", "statute")
    dispute_type = dispute.get("dispute_type", "").lower()

    # Check for purely statutory / in rem indicators
    rem_keywords = ["registration", "cancellation", "rectification", "passing off"]
    has_rem_keyword = any(kw in dispute_type for kw in rem_keywords)

    is_in_rem = (not has_contract) or (right_source == "statute") or has_rem_keyword

    if is_in_rem:
        right_type = "in_rem"
        right_type_label = "Right in Rem (against the world at large)"
        passes = False
        if not has_contract:
            explanation = (
                "No contractual relationship exists between the parties. "
                "The dispute involves rights enforceable against the world at large "
                "(right in rem), not specific contractual obligations between parties "
                "(right in personam). Per Booz Allen (2011), rights in rem are not arbitrable."
            )
        elif right_source == "statute":
            explanation = (
                "The right in dispute arises from statute (Trade Marks Act 1999), "
                "not from a private contract. Statutory rights are rights in rem "
                "enforceable erga omnes. Per Booz Allen (2011), such disputes "
                "require adjudication by competent civil courts."
            )
        else:
            explanation = (
                f"The dispute type '{dispute.get('dispute_type', '')}' involves "
                "matters that are inherently in rem (registration, cancellation, "
                "rectification, or passing off against a stranger), requiring "
                "determination by the appropriate judicial authority."
            )
    else:
        right_type = "in_personam"
        right_type_label = "Right in Personam (against a specific person)"
        passes = True
        explanation = (
            "A contractual relationship exists between the parties and the right "
            "in dispute arises from the contract (right in personam). Per Booz Allen "
            "(2011), disputes involving rights in personam are amenable to arbitration "
            "as they concern obligations between specific parties, not rights "
            "enforceable against the world at large."
        )

    rem_indicators = []
    personam_indicators = []

    if not has_contract:
        rem_indicators.append("No contractual relationship between parties")
    else:
        personam_indicators.append("Contractual relationship exists between parties")

    if right_source == "statute":
        rem_indicators.append("Right arises from statute (Trade Marks Act 1999)")
    else:
        personam_indicators.append("Right arises from contract between parties")

    if has_rem_keyword:
        rem_indicators.append(f"Dispute type '{dispute.get('dispute_type', '')}' involves in rem determination")
    else:
        personam_indicators.append(f"Dispute type '{dispute.get('dispute_type', '')}' is contractual in nature")

    if dispute.get("affects_third_parties", False):
        rem_indicators.append("Dispute affects third parties / public interest")
    else:
        personam_indicators.append("Dispute is confined to the contracting parties")

    return {
        "test": "Sections 2(1)(a) and 7, Arbitration and Conciliation Act 1996",
        "judicial_authority": (
            "Booz Allen and Hamilton Inc. v. SBI Home Finance Ltd. "
            "(2011) 5 SCC 532 — held that rights in rem fall outside "
            "Section 7 arbitration agreements"
        ),
        "test_name": "Booz Allen & Hamilton Test (Right in Rem vs Right in Personam)",
        "authority": LANDMARK_CASES["booz_allen"]["name"],
        "citation": LANDMARK_CASES["booz_allen"]["citation"],
        "right_type": right_type,
        "right_type_label": right_type_label,
        "passes": passes,
        "explanation": explanation,
        "rem_indicators": rem_indicators,
        "personam_indicators": personam_indicators,
    }


def apply_vidya_drolia_test(dispute: dict) -> dict:
    """Apply the Vidya Drolia fourfold test. All four must be NO to pass."""
    has_contract = dispute.get("has_contract", False)
    affects_third_parties = dispute.get("affects_third_parties", False)
    dispute_type = dispute.get("dispute_type", "").lower()

    # Q1: Actions in rem?
    q1_answer = (not has_contract) or affects_third_parties
    q1 = {
        "question": FOURFOLD_TEST[0],
        "answer": q1_answer,
        "passes": not q1_answer,
        "reasoning": (
            "The dispute involves actions in rem as there is no private contract "
            "governing the parties' relationship, or the dispute affects the public at large."
            if q1_answer
            else "The dispute arises from a contractual relationship and is confined "
            "to the contracting parties, constituting an action in personam."
        ),
    }

    # Q2: Affects third party rights?
    q2_answer = affects_third_parties
    q2 = {
        "question": FOURFOLD_TEST[1],
        "answer": q2_answer,
        "passes": not q2_answer,
        "reasoning": (
            "The dispute affects the rights of third parties or the public "
            "who are not party to any arbitration agreement."
            if q2_answer
            else "The dispute is limited to the rights and obligations of the "
            "contracting parties and does not affect third-party rights."
        ),
    }

    # Q3: Requires centralized adjudication?
    centralized_keywords = ["registration", "cancellation", "rectification", "opposition"]
    q3_answer = any(kw in dispute_type for kw in centralized_keywords)
    q3 = {
        "question": FOURFOLD_TEST[2],
        "answer": q3_answer,
        "passes": not q3_answer,
        "reasoning": (
            f"The dispute type '{dispute.get('dispute_type', '')}' requires "
            "adjudication by specialized statutory tribunals (e.g., Trademark Registry, IPAB)."
            if q3_answer
            else "The dispute does not require centralized adjudication by "
            "specialized courts or tribunals and can be resolved through arbitration."
        ),
    }

    # Q4: Expressly excluded by statute?
    excluded_keywords = ["criminal", "competition", "antitrust"]
    q4_answer = any(kw in dispute_type for kw in excluded_keywords)
    q4 = {
        "question": FOURFOLD_TEST[3],
        "answer": q4_answer,
        "passes": not q4_answer,
        "reasoning": (
            "The dispute falls within a category expressly or impliedly "
            "excluded from arbitration by statute."
            if q4_answer
            else "No statute expressly or impliedly bars arbitration "
            "for this category of dispute."
        ),
    }

    questions = [q1, q2, q3, q4]
    all_pass = all(q["passes"] for q in questions)

    return {
        "test": "Section 7 read with Section 2(1)(a), Arbitration and Conciliation Act 1996",
        "judicial_authority": (
            "Vidya Drolia v. Durga Trading Corporation (2021) 2 SCC 1 "
            "— laid down the fourfold test for Section 7 compliance"
        ),
        "test_name": "Vidya Drolia Fourfold Test",
        "authority": LANDMARK_CASES["vidya_drolia"]["name"],
        "citation": LANDMARK_CASES["vidya_drolia"]["citation"],
        "questions": questions,
        "all_pass": all_pass,
        "has_arbitration_clause": dispute.get("has_arbitration_clause", False),
    }


# ---------------------------------------------------------------------------
# Exclusion-language patterns that override a True has_arbitration_clause flag
# ---------------------------------------------------------------------------
_EXCLUSION_PATTERNS = [
    r"shall\s+not\s+be\s+referred\s+to\s+arbitration",
    r"(?:exclusively|only|solely)\s+by\s+(?:the\s+)?(?:civil|competent)\s+court",
    r"(?:civil|competent)\s+courts?\s+(?:of|in|at)\b",   # e.g. "civil courts of Mumbai"
    r"not\s+by\s+arbitration",
    r"arbitration\s+is\s+excluded",
    r"no\s+arbitration",
    r"disputes?\s+shall\s+be\s+(?:resolved|settled|adjudicated)\s+(?:exclusively|only|solely)\s+by",
    r"exclude[sd]?\s+(?:from\s+)?arbitration",
    r"oust(?:ing)?\s+(?:the\s+)?jurisdiction\s+of\s+(?:any\s+)?arbitr",
]
_EXCLUSION_RE = re.compile(
    "|".join(_EXCLUSION_PATTERNS),
    flags=re.IGNORECASE,
)


def _check_clause_contradiction(dispute: dict) -> tuple[bool, str]:
    """Return (contradicted, matched_snippet) if arbitration_clause_text contains
    exclusion language that contradicts a True has_arbitration_clause flag.

    Returns (False, "") when:
      - has_arbitration_clause is False (nothing to contradict), or
      - arbitration_clause_text is absent / empty, or
      - no exclusion pattern is found.
    """
    if not dispute.get("has_arbitration_clause", False):
        return False, ""

    clause_text = dispute.get("arbitration_clause_text", "") or ""
    if not clause_text.strip():
        return False, ""

    match = _EXCLUSION_RE.search(clause_text)
    if match:
        return True, match.group(0).strip()

    return False, ""


def check_narrative_disagreement(dispute: dict) -> dict:
    """Check for keywords in dispute_description that conflict with selected dispute_type."""
    dispute_description = dispute.get("dispute_description", "").lower()
    dispute_type = dispute.get("dispute_type", "").lower()

    rem_keywords = ["registration", "cancellation", "rectification", "passing off"]
    centralized_keywords = ["registration", "cancellation", "rectification", "opposition"]
    excluded_keywords = ["criminal", "competition", "antitrust"]

    # Combine in_rem and centralized since they represent same category of non-arbitrability
    in_rem_central_keywords = list(set(rem_keywords + centralized_keywords))

    # Check if dispute_type itself falls into any of these classifications
    type_is_in_rem_central = any(kw in dispute_type for kw in in_rem_central_keywords)
    type_is_excluded = any(kw in dispute_type for kw in excluded_keywords)

    conflicting_keywords = []

    # If dispute type is NOT classified as in_rem/central, check if description suggests it
    if not type_is_in_rem_central:
        for kw in in_rem_central_keywords:
            if kw in dispute_description:
                if kw not in conflicting_keywords:
                    conflicting_keywords.append(kw)

    # If dispute type is NOT classified as excluded, check if description suggests it
    if not type_is_excluded:
        for kw in excluded_keywords:
            if kw in dispute_description:
                if kw not in conflicting_keywords:
                    conflicting_keywords.append(kw)

    if conflicting_keywords:
        suggested_concepts = []
        has_rem_or_central = any(kw in conflicting_keywords for kw in in_rem_central_keywords)
        has_excluded = any(kw in conflicting_keywords for kw in excluded_keywords)

        if has_rem_or_central:
            suggested_concepts.append("in rem or centralized adjudication matters")
        if has_excluded:
            suggested_concepts.append("statutorily excluded matters")

        concepts_str = " and ".join(suggested_concepts)

        conflicting_keywords_str = ", ".join(f'"{k}"' for k in conflicting_keywords)
        message = (
            f"The dispute description contains language suggesting {concepts_str} "
            f"(specifically: {conflicting_keywords_str}), "
            f"which conflicts with the selected dispute type '{dispute.get('dispute_type', '')}'. "
            f"Please verify this classification manually."
        )
        return {
            "has_disagreement": True,
            "conflicting_keywords": conflicting_keywords,
            "message": message
        }

    return {
        "has_disagreement": False,
        "conflicting_keywords": [],
        "message": ""
    }


# ---------------------------------------------------------------------------
# Narrative-severity keywords: these are the in rem signals that, when found in
# dispute_description while dispute_type is on the arbitrable path, warrant a
# "MANUAL REVIEW REQUIRED" flag rather than just the softer amber warning.
# ---------------------------------------------------------------------------
_SEVERE_IN_REM_KEYWORDS: list[str] = [
    "cancellation",
    "rectification",
    "removal from register",
    "revocation",
    "expungement",
    "removal from the register",
    "strike off",
    "struck off",
]

# dispute_type values that are on the arbitrable / in-personam path and should
# NOT themselves contain in rem language (if they did, narrative disagreement
# would not fire — the existing check already handles that).
_ARBITRABLE_DISPUTE_TYPES: list[str] = [
    "license",
    "licence",
    "assignment",
    "distribution",
    "brand similarity",
    "franchise",
    "co-existence",
    "coexistence",
]


# ---------------------------------------------------------------------------
# Contract-narrative mismatch check
# ---------------------------------------------------------------------------
# Keywords that a dispute description is expected to contain when
# has_contract=True.  At least ONE must match (whole-word, case-insensitive)
# for the claim to be plausible.  Multi-word phrases are matched as a unit.
#
# Design note: use word-boundary anchors (\b) to avoid false positives like
# 'mou' matching inside 'famous', or 'agreed' inside 'trademark'.
_CONTRACT_INDICATOR_KEYWORDS: list[str] = [
    r"\bagreement\b",
    r"\blicen[sc]e\b",          # license / licence
    r"\bcontract\b",
    r"\bmemorandum of understanding\b",
    r"\bm\.?o\.?u\.?\b",       # MOU / M.O.U.
    r"\bclause\b",
    r"\blicensor\b",
    r"\blicensee\b",
    r"\bassignment deed\b",
    r"\bdistribution agreement\b",
    r"\bdistributorship agreement\b",
    r"\bfranchise agreement\b",
    r"\bco-?existence agreement\b",
    r"\bconsent agreement\b",
    r"\bsettlement agreement\b",
    r"\bdeed of assignment\b",
    r"\bletter of intent\b",
    r"\bsupply agreement\b",
    r"\bcollaboration agreement\b",
    r"\bjoint venture\b",
    r"\bsub-licen[sc]e\b",
    r"\bsub-licensee\b",
    r"\broyalty\b",
    r"\bpermitted use\b",
    r"\bentered into\b",
    r"\bcontractual\b",
]
_CONTRACT_RE = re.compile(
    "|".join(_CONTRACT_INDICATOR_KEYWORDS),
    flags=re.IGNORECASE,
)


def check_contract_narrative_mismatch(dispute: dict) -> dict:
    """Check whether has_contract=True is corroborated by dispute_description.

    Returns a dict with keys:
      - has_mismatch (bool)  — True when the flag says contract exists but
        description contains zero contractual language.
      - message (str)        — Human-readable explanation; empty when no mismatch.

    Conditions for mismatch:
      - has_contract must be explicitly True (False / missing → no check needed).
      - dispute_description must be non-empty.
      - None of the _CONTRACT_INDICATOR_KEYWORDS appear in the description
        (case-insensitive).

    This check is purely informational — is_arbitrable is never changed.
    """
    if not dispute.get("has_contract", False):
        return {"has_mismatch": False, "message": ""}

    description = dispute.get("dispute_description", "") or ""
    if not description.strip():
        return {"has_mismatch": False, "message": ""}

    description_lower = description.lower()
    found = bool(_CONTRACT_RE.search(description_lower))

    if found:
        return {"has_mismatch": False, "message": ""}

    message = (
        "\u2018Contract Between Parties\u2019 was marked YES, but no contractual "
        "language (e.g. agreement, license, clause, MOU, licensor/licensee, "
        "assignment deed) was found in the dispute description. "
        "Please verify this reflects the actual facts before proceeding "
        "\u2014 the generated report may incorrectly cite contractual provisions "
        "(e.g. Section 73, Indian Contract Act) for what appears to be a "
        "pure trademark infringement between unrelated parties."
    )
    return {"has_mismatch": True, "message": message}


def assess_narrative_contradiction_severity(
    narrative_warning: dict,
    dispute_type: str,
) -> tuple[bool, str]:
    """Assess whether a narrative disagreement rises to MANUAL REVIEW severity.

    Returns (requires_manual_review, review_reason).

    Severity is HIGH (requires_manual_review=True) only when ALL of:
      1. narrative_warning reports has_disagreement=True
      2. At least one conflicting keyword belongs to _SEVERE_IN_REM_KEYWORDS
         (i.e. the description explicitly mentions in rem statutory proceedings)
      3. The dispute_type is on the arbitrable / in-personam path, meaning the
         structured input would produce an ARBITRABLE verdict — making the
         contradiction materially misleading rather than redundant.

    The verdict is intentionally NOT changed here.  This function is purely
    diagnostic and is designed to be unit-tested independently of the core
    Booz Allen / Vidya Drolia logic.

    Args:
        narrative_warning: dict returned by check_narrative_disagreement().
        dispute_type:      lower-cased dispute_type string from the dispute.

    Returns:
        A (bool, str) tuple: (requires_manual_review, review_reason).
    """
    if not narrative_warning.get("has_disagreement", False):
        return False, ""

    conflicting = narrative_warning.get("conflicting_keywords", [])
    severe_hits = [
        kw for kw in conflicting
        if any(skw in kw or kw in skw for skw in _SEVERE_IN_REM_KEYWORDS)
    ]
    if not severe_hits:
        return False, ""

    # Only flag when the structured type would lead to an arbitrable verdict
    type_is_arbitrable_path = any(
        aw in dispute_type for aw in _ARBITRABLE_DISPUTE_TYPES
    )
    if not type_is_arbitrable_path:
        # Disagreement exists but the type already routes to NOT ARBITRABLE —
        # the amber narrative_warning footnote is sufficient.
        return False, ""

    severe_str = ", ".join(f'"{k}"' for k in severe_hits)
    review_reason = (
        f"The dispute description contains strong in rem statutory language "
        f"({severe_str}) that is associated with non-arbitrable proceedings "
        f"(e.g. cancellation / rectification before the Trade Marks Registry or "
        f"Intellectual Property Appellate Board). The structured dispute type "
        f"'{dispute_type}' routes this matter to an ARBITRABLE verdict, creating "
        f"a material contradiction. HUMAN REVIEW IS REQUIRED before relying on "
        f"this determination — the actual dispute may concern an in rem statutory "
        f"proceeding that cannot be referred to arbitration."
    )
    return True, review_reason


def check_arbitrability(dispute: dict) -> ArbitrabilityResult:
    """Main arbitrability determination. Returns ArbitrabilityResult."""
    booz_allen_result = apply_booz_allen_test(dispute)
    vidya_drolia_result = apply_vidya_drolia_test(dispute)
    narrative_warning = check_narrative_disagreement(dispute)

    # Severity assessment — isolated, verdict-neutral
    requires_manual_review, review_reason = assess_narrative_contradiction_severity(
        narrative_warning, dispute_type=dispute.get("dispute_type", "").lower()
    )

    # Contract-narrative mismatch — purely informational, no verdict impact
    contract_narrative_mismatch = check_contract_narrative_mismatch(dispute)

    has_arbitration_clause = dispute.get("has_arbitration_clause", False)
    dispute_type = dispute.get("dispute_type", "").lower()

    # -----------------------------------------------------------------------
    # TEXT-BASED OVERRIDE: check whether the clause text itself contains
    # exclusion language that contradicts the boolean flag.
    # -----------------------------------------------------------------------
    clause_contradicted, contradiction_snippet = _check_clause_contradiction(dispute)

    is_arbitrable = (
        booz_allen_result["passes"]
        and vidya_drolia_result["all_pass"]
        and has_arbitration_clause
        and not clause_contradicted   # override: contradictory text voids the clause
    )

    # Determine status and right type
    if is_arbitrable:
        status = "ARBITRABLE"
        right_type = "in_personam"
    else:
        status = "NOT ARBITRABLE"
        right_type = booz_allen_result["right_type"]

    # Determine applicable landmark
    if is_arbitrable:
        if "assignment" in dispute_type:
            applicable_landmark = "coca_cola_bisleri"
        elif any(kw in dispute_type for kw in ["license", "distribution", "licence"]):
            applicable_landmark = "hero_electric"
        else:
            applicable_landmark = "golden_tobie"
    else:
        if not booz_allen_result["passes"]:
            applicable_landmark = "booz_allen"
        else:
            applicable_landmark = "vidya_drolia"

    landmark_info = LANDMARK_CASES.get(applicable_landmark, {})
    primary_authority = (
        f"{landmark_info.get('name', '')} {landmark_info.get('citation', '')}"
    )

    # Build reason
    if is_arbitrable:
        reason = (
            f"The dispute between {dispute.get('party_a', 'Party A')} and "
            f"{dispute.get('party_b', 'Party B')} arises from a contractual "
            f"relationship and involves rights in personam. The Booz Allen test "
            f"confirms the dispute involves rights enforceable against a specific "
            f"party, not the world at large. The Vidya Drolia fourfold test is "
            f"satisfied — the dispute does not involve actions in rem, does not "
            f"affect third-party rights, does not require centralized adjudication, "
            f"and is not excluded by statute. An arbitration clause is present "
            f"in the agreement between the parties."
        )
        recommendation = (
            f"This dispute is ARBITRABLE. The arbitral tribunal has jurisdiction "
            f"to adjudicate the matter. Proceed with arbitration proceedings "
            f"in accordance with the arbitration clause in the agreement and "
            f"the Arbitration and Conciliation Act, 1996."
        )
    else:
        failed_tests = []
        if not booz_allen_result["passes"]:
            failed_tests.append("Booz Allen right in rem/in personam test")
        if not vidya_drolia_result["all_pass"]:
            failed_questions = [
                q["question"]
                for q in vidya_drolia_result["questions"]
                if not q["passes"]
            ]
            failed_tests.append(
                f"Vidya Drolia fourfold test (failed: {'; '.join(failed_questions)})"
            )
        if not has_arbitration_clause:
            failed_tests.append("No arbitration clause present")
        if clause_contradicted:
            failed_tests.append(
                f"Arbitration clause text contains exclusion language "
                f"(\u201c{contradiction_snippet}\u201d) that negates the clause"
            )

        reason = (
            f"The dispute between {dispute.get('party_a', 'Party A')} and "
            f"{dispute.get('party_b', 'Party B')} is NOT ARBITRABLE. "
            f"Failed determinations: {'; '.join(failed_tests)}. "
            f"The dispute involves rights in rem or otherwise fails the "
            f"established tests for arbitrability under Indian law."
        )
        recommendation = (
            f"This dispute is NOT ARBITRABLE. The appropriate remedy lies "
            f"before the competent civil court. The aggrieved party should "
            f"file a suit for trademark infringement and/or passing off "
            f"before the District Court or Commercial Court having jurisdiction, "
            f"or approach the High Court under its original jurisdiction where applicable."
        )

    return ArbitrabilityResult(
        is_arbitrable=is_arbitrable,
        status=status,
        right_type=right_type,
        booz_allen_test=booz_allen_result,
        vidya_drolia_test=vidya_drolia_result,
        primary_authority=primary_authority,
        reason=reason,
        recommendation=recommendation,
        applicable_landmark=applicable_landmark,
        narrative_warning=narrative_warning,
        clause_text_contradiction=clause_contradicted,
        requires_manual_review=requires_manual_review,
        review_reason=review_reason,
        contract_narrative_mismatch=contract_narrative_mismatch,
    )
