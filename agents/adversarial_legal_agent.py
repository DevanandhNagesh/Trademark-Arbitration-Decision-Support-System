"""Adversarial legal analysis agent using Gemini."""

import json
import os
import sys

from dotenv import load_dotenv
import google.generativeai as genai

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import GEMINI_API_KEY, MODEL_CONFIG
from logging_config import logger

load_dotenv()

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


def _strip_json_fences(text: str) -> str:
    """Strip ```json fences from LLM output before parsing."""
    text = text.strip()
    if text.startswith("```"):
        text = text.replace("```json", "").replace("```", "")
    return text.strip()


def generate_adversarial_analysis(
    dispute: dict,
    extracted_facts: dict,
    arbitrability_result,
    landmark_matches: list,
    legal_principles: list,
) -> dict:
    """Generate adversarial legal analysis anchored in statutes first."""
    party_a = dispute.get("party_a", "Party A")
    party_b = dispute.get("party_b", "Party B")
    trademark_name = dispute.get("trademark_name", "")
    dispute_type = dispute.get("dispute_type", "")
    arbitrability_status = arbitrability_result.status if arbitrability_result else "Unknown"

    key_facts = extracted_facts.get("key_facts", [])
    key_facts_text = "; ".join(key_facts) if isinstance(key_facts, list) else str(key_facts)

    landmark_names = ", ".join(
        [lm.case_name for lm in landmark_matches] if landmark_matches else ["N/A"]
    )

    prompt = f"""You are a senior Indian trademark and arbitration law advocate conducting adversarial legal analysis.
This analysis must follow Indian law exclusively.
Do NOT apply English common law where Indian statute has specifically departed. Key example: Section 2(d) of the Indian Contract Act 1872 allows consideration to move from any person not just the promisee, which is different from English law.

JURISDICTION: Indian law exclusively.
All reasoning must be grounded in Indian statutes and Indian judicial interpretation only.

LAW FIRST RULE — MANDATORY:
Every legal statement must follow this structure:
1. Section [X] of [Act] [Year] provides that [text]
2. [Court] in [Case] [Citation] interpreted this as [holding]
3. In the present dispute this means [application]
Never cite a case without first citing the statute it interprets. The statute is always primary authority. The case is always the interpretation of the statute.

DISPUTE DETAILS:
Party A (Claimant): {party_a}
Party B (Respondent): {party_b}
Trademark: {trademark_name}
Dispute Type: {dispute_type}
Arbitrability: {arbitrability_status}
Key Facts: {key_facts_text}
Extracted Facts: {extracted_facts}
Relevant Landmark Cases: {landmark_names}

Conduct a complete adversarial analysis.

Return ONLY a JSON object with these exact keys:

{{
  "law_for_claimant": [
    {{
      "statute": "Section X of [Act] [Year]",
      "statute_text": "brief text of the provision",
      "case_interpretation": "case name + citation + what court held",
      "application": "how this specifically helps Party A in this dispute"
    }}
  ],
  "law_against_claimant": [
    {{
      "statute": "Section X of [Act] [Year]",
      "statute_text": "brief text of the provision",
      "case_interpretation": "case name + citation + what court held",
      "application": "how this specifically hurts Party A in this dispute"
    }}
  ],
  "options_if_law_against": [
    {{
      "option_title": "short name for this legal option",
      "strategy": "what legal argument Party A can make",
      "statute_basis": "Section X of [Act] which supports this argument",
      "case_support": "case name + citation that backs this strategy",
      "strength": "Strong / Moderate / Weak",
      "reasoning": "why this option has this strength"
    }}
  ],
  "overall_legal_position": "one paragraph honest assessment of Party A's overall legal position based on the balance of law for and against"
}}

Return ONLY valid JSON. No markdown. No explanation.

MANDATORY OUTPUT REQUIREMENTS:
You MUST return all four top-level keys.
You MUST return minimum 2 entries in law_for_claimant.
You MUST return minimum 2 entries in law_against_claimant.
You MUST return minimum 2 entries in options_if_law_against.
If you cannot identify real provisions use the most applicable ones from Trade Marks Act 1999 and Indian Contract Act 1872.
Return ONLY valid JSON. No markdown. No explanation. No ```json fences.

EXAMPLE OUTPUT FORMAT — follow this structure exactly for every entry in every array:

{{
  "law_for_claimant": [
    {{
      "statute": "Section 29(2)(b) of Trade Marks Act 1999",
      "statute_text": "A registered trademark is infringed by a person who uses in the course of trade a mark which because of its similarity to the registered trademark and the identity or similarity of the goods or services is likely to cause confusion on the part of the public",
      "case_interpretation": "Parle Products v JP Co AIR 1972 SC 1359 — held that the overall impression test applies and marks must be compared as a whole from perspective of average consumer with imperfect recollection",
      "application": "Claimant's mark is registered. Respondent's mark is phonetically similar. Use for identical services. This section directly supports claimant's infringement claim."
    }},
    {{
      "statute": "Section 48 of Trade Marks Act 1999",
      "statute_text": "A person other than the registered proprietor of a trademark may be registered as a registered user thereof in respect of any or all of the goods or services in respect of which the trademark is registered",
      "case_interpretation": "Hero Electric Vehicles v Lectro E-Mobility 2021 SCC OnLine Del 1058 — held that post-expiry use by former licensee is unauthorized and constitutes infringement",
      "application": "License expired on stated date. Respondent ceased to be permitted user. Continued use is infringement under this section."
    }}
  ],
  "law_against_claimant": [
    {{
      "statute": "Section 30(2)(a) of Trade Marks Act 1999",
      "statute_text": "A registered trademark is not infringed where the use of the mark is in accordance with honest practices in industrial or commercial matters",
      "case_interpretation": "Courts interpret honest practices narrowly when marks are clearly similar — no landmark case directly supports this defence on these facts",
      "application": "Respondent may argue cultural or personal identity basis for mark. Weak argument given similarity but represents available counter."
    }}
  ],
  "options_if_law_against": [
    {{
      "option_title": "Assert Well-Known Mark Status",
      "strategy": "Establish mark as well-known trademark under Section 2(1)(zg) for broader protection regardless of goods similarity",
      "statute_basis": "Section 2(1)(zg) and Section 11(6) of Trade Marks Act 1999",
      "case_support": "N R Dongre v Whirlpool Corporation (1996) 5 SCC 714 — transborder reputation entitles mark to protection",
      "strength": "Strong",
      "reasoning": "Global reputation and India registration since 2001 makes well-known mark status highly defensible"
    }}
  ],
  "overall_legal_position": "Single paragraph honest assessment of the overall legal position based on balance of provisions for and against the claimant."
}}
"""

    try:
        model = genai.GenerativeModel(MODEL_CONFIG["primary"])
        response = model.generate_content(prompt)
        logger.info(f"ADVERSARIAL RAW RESPONSE: {response.text[:500]}")
        cleaned = _strip_json_fences(response.text)
        result = json.loads(cleaned)
        if not result.get("law_for_claimant") or len(result.get("law_for_claimant", [])) == 0:
            logger.warning("WARNING: law_for_claimant empty — retrying once")
            response = model.generate_content(prompt)
            text = response.text.strip()
            text = text.replace("```json", "").replace("```", "").strip()
            result = json.loads(text)
        result["generation_method"] = "live"
        return result
    except Exception as e:
        logger.warning(f"generate_adversarial_analysis failed: {e}. Using fallback.")
        return {
            "law_for_claimant": [],
            "law_against_claimant": [],
            "options_if_law_against": [],
            "overall_legal_position": (
                "Adversarial analysis is unavailable. Please review applicable statutes and case law "
                "manually for the claimant's position in this dispute."
            ),
            "generation_method": "fallback"
        }
