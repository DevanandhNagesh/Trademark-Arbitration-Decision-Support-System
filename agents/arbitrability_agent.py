"""Arbitrability determination agent — ZERO LLM calls, pure deterministic logic."""

import os
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

        message = (
            f"The dispute description contains language suggesting {concepts_str} "
            f"(specifically: {', '.join(f'"{k}"' for k in conflicting_keywords)}), "
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


def check_arbitrability(dispute: dict) -> ArbitrabilityResult:
    """Main arbitrability determination. Returns ArbitrabilityResult."""
    booz_allen_result = apply_booz_allen_test(dispute)
    vidya_drolia_result = apply_vidya_drolia_test(dispute)
    narrative_warning = check_narrative_disagreement(dispute)

    has_arbitration_clause = dispute.get("has_arbitration_clause", False)
    dispute_type = dispute.get("dispute_type", "").lower()

    is_arbitrable = (
        booz_allen_result["passes"]
        and vidya_drolia_result["all_pass"]
        and has_arbitration_clause
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
    )
