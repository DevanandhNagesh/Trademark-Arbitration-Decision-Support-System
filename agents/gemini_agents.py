"""Gemini LLM agents — all LLM calls are isolated here with fallback to LM Studio."""

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import google.generativeai as genai
import openai as groq_client
from openai import OpenAI

from config import GEMINI_API_KEY, MODEL_CONFIG
from logging_config import logger

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)


def _strip_json_fences(text: str) -> str:
    """Strip ```json fences from LLM output before parsing."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _call_gemini_api(prompt: str) -> str:
    start_time = time.time()
    try:
        model = genai.GenerativeModel(MODEL_CONFIG["primary"])
        response = model.generate_content(prompt)
        latency = time.time() - start_time
        logger.info(f"LLM call succeeded - Provider: gemini - Latency: {latency:.3f}s")
        return response.text
    except Exception as e:
        latency = time.time() - start_time
        logger.error(f"LLM call failed - Provider: gemini - Latency: {latency:.3f}s - Error: {e}")
        raise


def _call_groq_fallback(prompt: str) -> str:
    """Call Groq API as secondary fallback."""
    start_time = time.time()
    try:
        client = groq_client.OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.getenv("GROQ_API_KEY"),
        )
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        latency = time.time() - start_time
        logger.info(f"LLM call succeeded - Provider: groq - Latency: {latency:.3f}s")
        return response.choices[0].message.content
    except Exception as e:
        latency = time.time() - start_time
        logger.error(f"LLM call failed - Provider: groq - Latency: {latency:.3f}s - Error: {e}")
        raise


def _call_lm_studio(prompt: str) -> str:
    """Call LM Studio local server as backup."""
    start_time = time.time()
    try:
        client = OpenAI(
            base_url=MODEL_CONFIG["backup_url"],
            api_key="lm-studio",
        )
        response = client.chat.completions.create(
            model=MODEL_CONFIG["backup_model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        latency = time.time() - start_time
        logger.info(f"LLM call succeeded - Provider: lm_studio - Latency: {latency:.3f}s")
        return response.choices[0].message.content
    except Exception as e:
        latency = time.time() - start_time
        logger.error(f"LLM call failed - Provider: lm_studio - Latency: {latency:.3f}s - Error: {e}")
        raise


def _call_gemini(prompt: str) -> str:
    """Call Gemini API, fall back to Groq then LM Studio on failure."""
    try:
        return _call_gemini_api(prompt)
    except Exception as e:
        logger.warning(f"Primary Gemini call failed: {e}. Falling back to Groq...")
        try:
            return _call_groq_fallback(prompt)
        except Exception as groq_error:
            logger.warning(f"Secondary Groq fallback failed: {groq_error}. Falling back to LM Studio...")
            return _call_lm_studio(prompt)


def extract_dispute_facts(dispute_description: str, form_data: dict) -> dict:
    """Extract structured legal facts from the dispute description using Gemini."""
    prompt = f"""LAW FIRST RULE — MANDATORY FOR ALL OUTPUT:
JURISDICTION: Indian law exclusively.
Do NOT apply English common law where Indian statute has specifically departed.
Key Indian-specific rule: Section 2(d) Indian Contract Act 1872 — consideration can move from promisee OR any other person. This differs from English law.
Every legal statement must follow this exact structure:
1. Cite statute section first: "Section [X] of [Act] [Year] provides that..."
2. Cite case that interpreted it second: "The [Court] in [Case Name] [Citation] held that..."
3. Apply to current facts third: "In the present dispute this means..."
NEVER cite a case without first citing the statute it interprets.
NEVER state a legal principle without anchoring it to the specific statutory provision it derives from.
The statute is always the primary authority.
The case is always the interpretation of the statute.
Do NOT use markdown formatting. No asterisks. No # headers. No - bullets. Plain text only.

You are an Indian trademark law expert. Analyze the following trademark dispute and extract structured legal facts.

DISPUTE DESCRIPTION:
{dispute_description}

FORM DATA:
- Claimant: {form_data.get('party_a', '')}
- Respondent: {form_data.get('party_b', '')}
- Trademark: {form_data.get('trademark_name', '')}
- Dispute Type: {form_data.get('dispute_type', '')}
- Has Contract: {form_data.get('has_contract', False)}
- Right Source: {form_data.get('right_source', '')}

Return ONLY a JSON object with these exact keys:
{{
  "trademark_nature": "description of the trademark and its distinctiveness",
  "dispute_summary": "2-3 sentence summary of the core dispute",
  "right_source": "contract or statute",
  "key_facts": ["fact 1", "fact 2", "fact 3"],
  "relief_sought": "description of relief being sought",
  "legal_relationship": "description of relationship between parties",
  "affects_third_parties": true or false,
  "dispute_category": "one of: infringement / licensing / assignment / passing_off / similarity"
}}

Return ONLY valid JSON, no explanation."""

    try:
        raw = _call_gemini(prompt)
        cleaned = _strip_json_fences(raw)
        res = json.loads(cleaned)
        if isinstance(res, dict):
            res["generation_method"] = "live"
            return res
        raise ValueError("Response is not dict")
    except Exception as e:
        logger.warning(f"extract_dispute_facts failed: {e}. Fallback triggered.")
        return {
            "trademark_nature": f"Registered trademark '{form_data.get('trademark_name', 'Unknown')}'",
            "dispute_summary": (
                f"Dispute between {form_data.get('party_a', 'Party A')} and "
                f"{form_data.get('party_b', 'Party B')} regarding the trademark "
                f"'{form_data.get('trademark_name', '')}'. "
                f"Type: {form_data.get('dispute_type', 'Unknown')}."
            ),
            "right_source": form_data.get("right_source", "statute"),
            "key_facts": [
                f"Dispute involves trademark '{form_data.get('trademark_name', '')}'",
                f"Dispute type: {form_data.get('dispute_type', 'Unknown')}",
                f"Contract between parties: {'Yes' if form_data.get('has_contract') else 'No'}",
            ],
            "relief_sought": "Injunction, damages, and costs as per dispute description",
            "legal_relationship": (
                "Contractual relationship" if form_data.get("has_contract")
                else "No prior contractual relationship"
            ),
            "affects_third_parties": form_data.get("affects_third_parties", False),
            "dispute_category": form_data.get("dispute_type", "infringement").lower().replace(" ", "_"),
            "generation_method": "fallback"
        }


def frame_legal_issues(
    dispute: dict,
    extracted_facts: dict,
    arbitrability_result,
    landmark_matches: list,
) -> list:
    """Frame exactly 4 legal issues starting with 'Whether...'"""
    landmark_names = ", ".join(
        [lm.case_name for lm in landmark_matches] if landmark_matches else ["N/A"]
    )

    arb_status = arbitrability_result.status if arbitrability_result else "Unknown"

    prompt = f"""LAW FIRST RULE — MANDATORY FOR ALL OUTPUT:
JURISDICTION: Indian law exclusively.
Do NOT apply English common law where Indian statute has specifically departed.
Key Indian-specific rule: Section 2(d) Indian Contract Act 1872 — consideration can move from promisee OR any other person. This differs from English law.
Every legal statement must follow this exact structure:
1. Cite statute section first: "Section [X] of [Act] [Year] provides that..."
2. Cite case that interpreted it second: "The [Court] in [Case Name] [Citation] held that..."
3. Apply to current facts third: "In the present dispute this means..."
NEVER cite a case without first citing the statute it interprets.
NEVER state a legal principle without anchoring it to the specific statutory provision it derives from.
The statute is always the primary authority.
The case is always the interpretation of the statute.
Do NOT use markdown formatting. No asterisks. No # headers. No - bullets. Plain text only.

You are an Indian legal expert. Frame exactly 4 legal issues for determination in this trademark dispute.

CRITICAL PATH RULE — READ FIRST:

Arbitrability Status: {arb_status}

PATH 1 — If Arbitrability Status = "NOT ARBITRABLE":
  Do NOT frame any issues about:
  - Whether the dispute is arbitrable
  - Whether the forum is civil court or arbitration
  - Whether the Booz Allen test is satisfied
  - Whether the Vidya Drolia test is satisfied
  These questions are already answered. Do not repeat them.

  Instead frame exactly 4 substantive trademark issues the CIVIL COURT must decide:

  Issue 1: Must be about trademark similarity or confusion
    Format: "Whether the mark [TRADEMARK B] is deceptively similar to the registered trademark [TRADEMARK A] of [Party A] under Section 29 of the Trade Marks Act 1999 so as to cause confusion in the minds of consumers?"

  Issue 2: Must be about infringement or passing off
    Format: "Whether [Party B] has infringed the registered trademark rights of [Party A] in the mark [TRADEMARK A] under Sections 29 and 30 of the Trade Marks Act 1999 and/or is passing off its goods as those of [Party A]?"

  Issue 3: Must be about injunctive relief
    Format: "Whether [Party A] is entitled to a permanent injunction restraining [Party B] from using the mark [TRADEMARK B] or any deceptively similar mark under Section 135 of the Trade Marks Act 1999?"

  Issue 4: Must be about damages
    Format: "Whether [Party A] is entitled to damages and/or account of profits from [Party B] and if so to what quantum?"

  Statute references for NOT ARBITRABLE path:
  - Trade Marks Act 1999 Section 29 (Infringement)
  - Trade Marks Act 1999 Section 30 (Limits on infringement)
  - Trade Marks Act 1999 Section 135 (Relief in suits)
  - Trade Marks Act 1999 Section 27 (No action for unregistered mark unless passing off)
  Do NOT reference Arbitration and Conciliation Act 1996
  Do NOT reference Section 48 or Section 49

PATH 2 — If Arbitrability Status = "ARBITRABLE":
  Frame 4 issues for the arbitral tribunal. Apply these instructions:
  1. Each issue MUST start with "Whether"
  2. Reference Trade Marks Act, 1999 and Arbitration and Conciliation Act, 1996
  3. Issues should cover: jurisdiction/arbitrability, infringement/violation, relief, and costs
  4. Frame issues specific to this dispute's facts

  STATUTE SELECTION RULES — apply based on Dispute Type:

  If Dispute Type is "License Dispute" or description contains "license" or "franchise" or "licensee":
    Primary statute references:
    - Trade Marks Act 1999, Section 48 (Registered User)
    - Trade Marks Act 1999, Section 49 (Registered User conditions)
    - Indian Contract Act 1872, Section 73 (Damages for breach)
    - Arbitration and Conciliation Act 1996, Section 7 (Agreement)
    DO NOT reference Sections 29/30 as primary authority.
    Sections 29/30 may only appear in Issue 2 if unauthorized post-expiry use is also claimed as infringement.

  If Dispute Type is "Assignment Dispute" or description contains "assignment" or "assign":
    Primary statute references:
    - Trade Marks Act 1999, Section 37 (Power to assign)
    - Trade Marks Act 1999, Section 38 (Assignment without goodwill)
    - Indian Contract Act 1872, Section 73 (Damages for breach)
    - Arbitration and Conciliation Act 1996, Section 7 (Agreement)

  If Dispute Type is "Trademark Infringement" or "Passing Off" or "Brand Similarity":
    Primary statute references:
    - Trade Marks Act 1999, Section 29 (Infringement)
    - Trade Marks Act 1999, Section 30 (Limits on effect)
    - Trade Marks Act 1999, Section 27 (No action for unregistered)
    - Arbitration and Conciliation Act 1996 only if contract exists

DISPUTE DETAILS:
- Claimant: {dispute.get('party_a', '')}
- Respondent: {dispute.get('party_b', '')}
- Trademark: {dispute.get('trademark_name', '')}
- Dispute Type: {dispute.get('dispute_type', '')}

EXTRACTED FACTS:
- Summary: {extracted_facts.get('dispute_summary', '')}
- Key Facts: {', '.join(extracted_facts.get('key_facts', []))}
- Relief Sought: {extracted_facts.get('relief_sought', '')}

RELEVANT LANDMARK CASES: {landmark_names}

Return ONLY a JSON array of exactly 4 strings. Each must start with "Whether". No explanation.
Example: ["Whether...", "Whether...", "Whether...", "Whether..."]"""

    try:
        raw = _call_gemini(prompt)
        cleaned = _strip_json_fences(raw)
        issues = json.loads(cleaned)
        if isinstance(issues, list) and len(issues) >= 4:
            return issues[:4], "live"
        raise ValueError("Invalid issues format")
    except Exception as e:
        logger.warning(f"frame_legal_issues failed: {e}. Fallback triggered.")
        party_a = dispute.get("party_a", "the Claimant")
        party_b = dispute.get("party_b", "the Respondent")
        trademark = dispute.get("trademark_name", "the trademark")
        status = arbitrability_result.status if arbitrability_result else "Unknown"

        if status == "ARBITRABLE":
            fallback_issues = [
                f"Whether the arbitral tribunal has jurisdiction to adjudicate the present dispute between {party_a} and {party_b} concerning the trademark '{trademark}' under the Arbitration and Conciliation Act, 1996?",
                f"Whether {party_b} has infringed and/or violated the trademark rights of {party_a} in the mark '{trademark}' under Sections 29 and 30 of the Trade Marks Act, 1999?",
                f"Whether {party_a} is entitled to injunctive relief, rendition of accounts, and/or damages against {party_b} for the alleged infringement of trademark '{trademark}'?",
                f"Whether {party_a} is entitled to costs of the arbitration proceedings?",
            ]
        else:
            fallback_issues = [
                f"Whether the mark used by {party_b} is deceptively similar to the registered trademark '{trademark}' of {party_a} under Section 29 of the Trade Marks Act, 1999 so as to cause confusion in the minds of consumers?",
                f"Whether {party_b} has infringed the registered trademark rights of {party_a} in the mark '{trademark}' under Sections 29 and 30 of the Trade Marks Act, 1999 and/or is passing off its goods as those of {party_a}?",
                f"Whether {party_a} is entitled to a permanent injunction restraining {party_b} from using the mark '{trademark}' or any deceptively similar mark under Section 135 of the Trade Marks Act, 1999?",
                f"Whether {party_a} is entitled to damages and/or account of profits from {party_b} and if so to what quantum?",
            ]
        return fallback_issues, "fallback"


def identify_legal_principles(
    dispute: dict,
    extracted_facts: dict,
    landmark_matches: list,
) -> list:
    """Identify 3-5 applicable legal principles."""
    landmarks_text = "\n".join(
        [
            f"- {lm.case_name} ({lm.citation}): {lm.principle}"
            for lm in landmark_matches
        ]
        if landmark_matches
        else ["No landmark cases retrieved"]
    )

    prompt = f"""LAW FIRST RULE — MANDATORY FOR ALL OUTPUT:
JURISDICTION: Indian law exclusively.
Do NOT apply English common law where Indian statute has specifically departed.
Key Indian-specific rule: Section 2(d) Indian Contract Act 1872 — consideration can move from promisee OR any other person. This differs from English law.
Every legal statement must follow this exact structure:
1. Cite statute section first: "Section [X] of [Act] [Year] provides that..."
2. Cite case that interpreted it second: "The [Court] in [Case Name] [Citation] held that..."
3. Apply to current facts third: "In the present dispute this means..."
NEVER cite a case without first citing the statute it interprets.
NEVER state a legal principle without anchoring it to the specific statutory provision it derives from.
The statute is always the primary authority.
The case is always the interpretation of the statute.
Do NOT use markdown formatting. No asterisks. No # headers. No - bullets. Plain text only.

You are an Indian trademark law expert. Identify 3-5 applicable statutory provisions and judicial interpretations for this dispute.

DISPUTE:
- Trademark: {dispute.get('trademark_name', '')}
- Type: {dispute.get('dispute_type', '')}
- Summary: {extracted_facts.get('dispute_summary', '')}
- Key Facts: {', '.join(extracted_facts.get('key_facts', []))}

RELEVANT LANDMARK CASES:
{landmarks_text}

Return ONLY a JSON array of objects with these exact keys:
[
    {{
        "statute": "Section X of [Act] [Year]",
        "statute_text": "the actual text or summary of the provision",
        "principle_name": "short name",
        "judicial_interpretation": "case name + citation + what court held about this section",
        "application": "how this statute and its interpretation applies to THIS dispute specifically"
    }}
]

Return 3-5 items. Return ONLY valid JSON, no explanation."""

    try:
        raw = _call_gemini(prompt)
        cleaned = _strip_json_fences(raw)
        principles = json.loads(cleaned)
        if isinstance(principles, list) and len(principles) >= 3:
            return principles[:5], "live"
        raise ValueError("Invalid principles format")
    except Exception as e:
        logger.warning(f"identify_legal_principles failed: {e}. Fallback triggered.")
        principles = [
            {
                "principle_name": "Right in Rem vs Right in Personam",
                "description": "Rights enforceable against the world at large (in rem) are not arbitrable, while rights against specific persons (in personam) are arbitrable.",
                "authority": "Booz Allen & Hamilton Inc. v. SBI Home Finance Ltd. (2011) 5 SCC 532",
                "application": f"Applied to determine whether the dispute over '{dispute.get('trademark_name', '')}' involves rights in rem or in personam.",
            },
            {
                "principle_name": "Fourfold Test for Arbitrability",
                "description": "A dispute is non-arbitrable if it involves (1) actions in rem, (2) third-party rights, (3) requires centralized adjudication, or (4) is excluded by statute.",
                "authority": "Vidya Drolia v. Durga Trading Corporation (2021) 2 SCC 1",
                "application": "Applied to test all four limbs of arbitrability for the present dispute.",
            },
            {
                "principle_name": "Deceptive Similarity and Consumer Confusion",
                "description": "The test for trademark infringement is whether an average consumer with imperfect recollection would be confused or deceived.",
                "authority": "Parle Products (P) Ltd. v. J.P. & Co., Mysore AIR 1972 SC 1359",
                "application": f"Applied to assess whether the use of '{dispute.get('trademark_name', '')}' causes consumer confusion.",
            },
        ]

        if dispute.get("has_contract"):
            principles.append({
                "principle_name": "Contractual Trademark Disputes are Arbitrable",
                "description": "Trademark disputes arising from contractual relationships are arbitrable as they involve rights in personam.",
                "authority": "Hero Electric Vehicles Pvt. Ltd. v. Lectro E-Mobility Pvt. Ltd. 2021 SCC OnLine Del 1058",
                "application": "The present dispute arises from a contractual relationship, making it amenable to arbitration.",
            })

        return principles, "fallback"


def generate_award_framework(
    dispute: dict,
    extracted_facts: dict,
    arbitrability_result,
    issues: list,
    principles: list,
) -> dict:
    """Generate the award framework structure."""
    issues_text = "\n".join([f"{i+1}. {issue}" for i, issue in enumerate(issues)])
    principles_text = "\n".join(
        [
            f"- {p.get('principle_name', '')}: {p.get('description', '')}"
            for p in principles
        ]
        if principles
        else ["No principles identified"]
    )

    arb_status = arbitrability_result.status if arbitrability_result else "Unknown"

    prompt = f"""LAW FIRST RULE — MANDATORY FOR ALL OUTPUT:
JURISDICTION: Indian law exclusively.
Do NOT apply English common law where Indian statute has specifically departed.
Key Indian-specific rule: Section 2(d) Indian Contract Act 1872 — consideration can move from promisee OR any other person. This differs from English law.
Every legal statement must follow this exact structure:
1. Cite statute section first: "Section [X] of [Act] [Year] provides that..."
2. Cite case that interpreted it second: "The [Court] in [Case Name] [Citation] held that..."
3. Apply to current facts third: "In the present dispute this means..."
NEVER cite a case without first citing the statute it interprets.
NEVER state a legal principle without anchoring it to the specific statutory provision it derives from.
The statute is always the primary authority.
The case is always the interpretation of the statute.
Do NOT use markdown formatting. No asterisks. No # headers. No - bullets. Plain text only.

You are an Indian legal expert drafting a decision framework for a trademark dispute.

CRITICAL PATH RULE — READ FIRST:

Arbitrability Status: {arb_status}

PATH 1 — If Arbitrability Status = "NOT ARBITRABLE":

  Return JSON with these exact keys:

  jurisdiction_finding:
    One paragraph stating clearly that this tribunal lacks jurisdiction.
    The dispute is referred to the competent civil court.
    State which court has jurisdiction (District Court / Commercial Court / High Court original side) based on the relief amount claimed.
    If damages claimed exceed Rs 3 lakhs reference the Commercial Courts Act 2015.
    Do NOT use arbitration language in this paragraph.

  findings_on_issues:
    For each of the {len(issues)} substantive trademark issues:
    - issue_number: sequential integer
    - issue: the issue text
    - applicable_law: correct TM Act sections only (Sections 29, 30, 135 — NOT Arbitration Act sections)
        - finding_options: exactly 2 options as follows:
            Option A must start with the statute:
                "Under Section [X] of [Act], [Respondent] HAS [finding] as interpreted in [Case Citation]."
            Option B must start with the statute:
                "Under Section [X] of [Act], [Respondent] has NOT [finding] and the claim fails."
      NEVER use: "It is held that the question of..."
      NEVER use: "is answered in the negative" as the entire option
      NEVER end with a question mark
      Each option is a complete declarative sentence only

  relief_section:
    injunction_applicable: true
    injunction_guidance: guidance for civil court on permanent injunction under Section 135 TM Act 1999
    damages_applicable: true
    damages_guidance: guidance on actual damages, account of profits, and statutory damages under TM Act 1999
    costs_guidance: costs to follow the event in civil court

  operative_portion_template:
    Must be titled "COURT REFERRAL DIRECTION" not "OPERATIVE PORTION"
    Content:
    "This matter is NOT ARBITRABLE and is referred to the competent [Commercial Court / High Court] for adjudication. The following issues are recommended for determination: [list issues]. The Claimant may seek the following interim reliefs pending final disposal:
    1. Ad-interim injunction restraining [Party B] from using [TRADEMARK B] — [GRANTED / REFUSED]
    2. [BLANK — any other interim relief]
    This referral is made on [BLANK] day of [BLANK] [YEAR]."
    Do NOT use "In the matter of arbitration between..."
    Do NOT use "costs of this arbitration"
    Do NOT use "Sole Arbitrator" in signature block

PATH 2 — If Arbitrability Status = "ARBITRABLE":

  Return JSON with the same structure but for the arbitral tribunal.

    finding_options for EVERY issue must follow this rule:
    Option A must start with the statute:
        "Under Section [X] of [Act], [Respondent] HAS [finding] as interpreted in [Case Citation]."
    Option B must start with the statute:
        "Under Section [X] of [Act], [Respondent] has NOT [finding] and the claim fails."
  NEVER use: "It is held that the question of..."
  NEVER use: "is answered in the negative" as the entire option
  NEVER end an option with a question mark
  NEVER repeat the issue text verbatim inside the option
  Maximum 2 sentences per option
  Each option must be a complete declarative sentence

DISPUTE:
- Claimant: {dispute.get('party_a', '')}
- Respondent: {dispute.get('party_b', '')}  
- Trademark: {dispute.get('trademark_name', '')}

ISSUES FOR DETERMINATION:
{issues_text}

APPLICABLE PRINCIPLES:
{principles_text}

Return ONLY a JSON object with this exact structure:
{{
  "jurisdiction_finding": "paragraph text",
  "findings_on_issues": [
    {{
      "issue_number": 1,
      "issue": "the issue text",
      "finding_options": ["Option A finding text", "Option B finding text"],
      "applicable_law": "relevant sections of applicable statutes"
    }}
  ],
  "relief_section": {{
    "injunction_applicable": true or false,
    "injunction_guidance": "guidance text for injunction",
    "damages_applicable": true or false,
    "damages_guidance": "guidance text for damages assessment",
    "costs_guidance": "guidance text for costs"
  }},
  "operative_portion_template": "Template text with placeholders"
}}

Create findings_on_issues for all {len(issues)} issues. Each must have exactly 2 finding_options.

Do NOT use markdown formatting anywhere in your response. Do NOT use **double asterisks** for bold text. Do NOT use any markdown symbols including *, **, #, -, _. Return plain text only in all string fields. The output will be inserted directly into a Word document which does not render markdown.

Return ONLY valid JSON, no explanation."""

    try:
        raw = _call_gemini(prompt)
        cleaned = _strip_json_fences(raw)
        framework = json.loads(cleaned)

        # Validate structure
        if "jurisdiction_finding" in framework and "findings_on_issues" in framework:
            framework["generation_method"] = "live"
            return framework
        raise ValueError("Invalid framework structure")
    except Exception as e:
        logger.warning(f"generate_award_framework failed: {e}. Fallback triggered.")
        party_a = dispute.get("party_a", "the Claimant")
        party_b = dispute.get("party_b", "the Respondent")
        trademark = dispute.get("trademark_name", "the trademark")
        status = arbitrability_result.status if arbitrability_result else "NOT ARBITRABLE"

        if status == "ARBITRABLE":
            jurisdiction_finding = (
                f"This Tribunal has jurisdiction to adjudicate the present dispute "
                f"between {party_a} and {party_b} concerning the trademark '{trademark}'. "
                f"The dispute arises from a contractual relationship between the parties "
                f"and involves rights in personam. The arbitration clause in the agreement "
                f"is valid and enforceable under the Arbitration and Conciliation Act, 1996."
            )
        else:
            jurisdiction_finding = (
                f"This dispute between {party_a} and {party_b} concerning the trademark "
                f"'{trademark}' is NOT ARBITRABLE. The dispute involves rights in rem "
                f"enforceable against the world at large and/or fails the fourfold test "
                f"established in Vidya Drolia v. Durga Trading Corporation (2021). "
                f"The appropriate forum is the competent civil court."
            )

        findings_on_issues = []
        for i, issue in enumerate(issues):
            if status == "ARBITRABLE":
                finding_options = [
                    f"{party_b} HAS committed the acts described in Issue {i + 1} and {party_a} is entitled to the relief claimed.",
                    f"{party_b} has NOT committed the acts described in Issue {i + 1} and the claim on this issue fails.",
                ]
                applicable_law = (
                    "Sections 29, 30 of the Trade Marks Act, 1999; "
                    "Sections 7, 11, 34 of the Arbitration and Conciliation Act, 1996"
                )
            else:
                finding_options = [
                    f"{party_b} IS liable for infringement of {party_a}'s trademark '{trademark}' under Section 29 of the Trade Marks Act, 19_99.",
                    f"{party_b} is NOT liable for infringement and no cause of action is established against {party_b}.",
                ]
                applicable_law = (
                    "Sections 29, 30, 135 of the Trade Marks Act, 1999"
                )
            findings_on_issues.append({
                "issue_number": i + 1,
                "issue": issue,
                "finding_options": finding_options,
                "applicable_law": applicable_law,
            })

        if status == "ARBITRABLE":
            operative_template = (
                f"OPERATIVE PORTION\n\n"
                f"In the matter of arbitration between {party_a} (Claimant) and "
                f"{party_b} (Respondent) concerning the trademark '{trademark}':\n\n"
                f"1. The Tribunal [HOLDS/DOES NOT HOLD] that it has jurisdiction.\n"
                f"2. The Respondent [HAS/HAS NOT] infringed the trademark rights of the Claimant.\n"
                f"3. The Claimant [IS/IS NOT] entitled to injunctive relief.\n"
                f"4. The Respondent shall pay [BLANK] as damages/compensation.\n"
                f"5. The costs of this arbitration shall be borne by [BLANK].\n\n"
                f"This award is made at [BLANK] on this [BLANK] day of [BLANK].\n\n"
                f"________________________\n"
                f"[Name of Arbitrator]\n"
                f"Sole Arbitrator"
            )
        else:
            operative_template = (
                f"COURT REFERRAL DIRECTION\n\n"
                f"This matter is NOT ARBITRABLE and is referred to the competent "
                f"Commercial Court / High Court for adjudication.\n\n"
                f"The following issues are recommended for determination:\n"
                + "\n".join([f"{i+1}. {issue}" for i, issue in enumerate(issues)])
                + f"\n\nThe Claimant {party_a} may seek the following interim reliefs "
                f"pending final disposal:\n"
                f"1. Ad-interim injunction restraining {party_b} from using the "
                f"mark '{trademark}' — [GRANTED / REFUSED]\n"
                f"2. [BLANK — any other interim relief]\n\n"
                f"This referral is made on [BLANK] day of [BLANK] [YEAR].\n\n"
                f"________________________\n"
                f"[Name of Presiding Officer]"
            )

        return {
            "jurisdiction_finding": jurisdiction_finding,
            "findings_on_issues": findings_on_issues,
            "relief_section": {
                "injunction_applicable": True,
                "injunction_guidance": (
                    "Consider granting permanent injunction restraining the Respondent "
                    "from using the trademark if infringement is established."
                    if status == "ARBITRABLE"
                    else "The civil court should consider granting permanent injunction "
                    "under Section 135 of the Trade Marks Act, 1999 restraining the "
                    "defendant from using the infringing mark."
                ),
                "damages_applicable": True,
                "damages_guidance": (
                    "Assess damages based on loss of goodwill, actual damages suffered, "
                    "and account of profits made by the Respondent through unauthorized use."
                    if status == "ARBITRABLE"
                    else "The civil court should assess actual damages, account of profits, "
                    "and statutory damages under the Trade Marks Act, 1999."
                ),
                "costs_guidance": (
                    "Costs to follow the event. The unsuccessful party shall bear "
                    "the costs of arbitration including tribunal fees and legal costs."
                    if status == "ARBITRABLE"
                    else "Costs to follow the event in the civil court proceedings."
                ),
            },
            "operative_portion_template": operative_template,
            "generation_method": "fallback"
        }


def master_legal_analysis(
    dispute: dict,
    arbitrability_result,
    landmark_matches: list,
) -> dict:
    """Run a single Gemini call to produce facts, issues, statutes, and award framework."""
    party_a = dispute.get("party_a", "Party A")
    party_b = dispute.get("party_b", "Party B")
    trademark = dispute.get("trademark_name", "the trademark")
    arbitrability_status = arbitrability_result.status if arbitrability_result else "Unknown"
    right_type = arbitrability_result.right_type if arbitrability_result else "Unknown"
    reason = arbitrability_result.reason if arbitrability_result else ""

    landmark_context = "\n".join([
        f"- {lm.case_name} ({lm.citation}): {lm.principle}"
        for lm in (landmark_matches or [])[:3]
    ])

    prompt = f"""You are a senior Indian trademark and arbitration law expert conducting a complete legal analysis.
JURISDICTION: Indian law exclusively.
LAW FIRST RULE: Statute first, case second, application third. Always.
Do NOT apply English common law where Indian statute has specifically departed.
Key Indian-specific rule: Section 2(d) Indian Contract Act 1872 allows consideration to move from promisee or any other person.
Every legal statement must follow this exact structure. First cite statute section. Second cite case that interpreted it. Third apply to current facts.
Never cite a case without first citing the statute it interprets. The statute is always the primary authority. The case is always the interpretation of the statute.
Do NOT use markdown formatting. No asterisks. No hash headers. No dashes. No underscores. Plain text only.

DISPUTE DETAILS:
Party A (Claimant): {party_a}
Party B (Respondent): {party_b}
Trademark: {dispute.get("trademark_name", "")}
Dispute Type: {dispute.get("dispute_type", "")}
Has Contract: {dispute.get("has_contract", False)}
Has Arbitration Clause: {dispute.get("has_arbitration_clause", False)}
Right Source: {dispute.get("right_source", "")}
Affects Third Parties: {dispute.get("affects_third_parties", False)}
Dispute Description: {dispute.get("dispute_description", "")}

ARBITRABILITY DETERMINATION (already computed):
Status: {arbitrability_status}
Right Type: {right_type}
Reason: {reason}

RELEVANT LANDMARK CASES (already retrieved):
{landmark_context}

Perform all four tasks and return a single unified JSON object with all four sections.

Task 1. Extract dispute facts. Task 2. Frame legal issues. Task 3. Identify statutory provisions. Task 4. Generate award framework.

If arbitrability_status is NOT ARBITRABLE, frame 4 substantive trademark issues for civil court and do NOT frame arbitrability issues.
Reference Sections 29, 30, 135 of Trade Marks Act 1999 in the legal issues.
If arbitrability_status is ARBITRABLE, frame 4 issues for the arbitral tribunal referencing the Trade Marks Act and Arbitration and Conciliation Act 1996.

Finding options must be clean declarative sentences anchored to statute. No markdown formatting.

FINDING OPTIONS FORMAT — MANDATORY:
Each option must be a single complete declarative sentence.
Do NOT include "Option A:" or "Option B:" text inside the sentence content itself.
Option A content:
"Under Section [X] of [Act], [Respondent] HAS [finding] as interpreted in [Case Citation]."
Option B content:
"Under Section [X] of [Act], [Respondent] has NOT [finding] and the claim on this issue fails."
Each option must be specific to the parties and trademark in this dispute — use actual names.
Maximum 2 sentences per option.

Return ONLY this exact JSON structure:
{{
  "extracted_facts": {{
    "trademark_nature": "string",
    "dispute_summary": "string",
    "right_source": "string",
    "key_facts": ["fact1", "fact2", "fact3"],
    "relief_sought": "string",
    "legal_relationship": "string",
    "affects_third_parties": false,
    "dispute_category": "string"
  }},
  "legal_issues": [
    "Whether...",
    "Whether...",
    "Whether...",
    "Whether..."
  ],
  "statutory_provisions": [
    {{
      "statute": "Section X of Act Year",
      "statute_text": "actual text of the provision",
      "principle_name": "short name",
      "judicial_interpretation": "case + citation + holding",
      "application": "specific application to this dispute"
    }}
  ],
  "award_framework": {{
    "jurisdiction_finding": "string",
    "findings_on_issues": [
      {{
        "issue_number": 1,
        "issue": "string",
        "finding_options": ["Option A: ...", "Option B: ..."],
        "applicable_law": "Section X of Act Year"
      }}
    ],
    "relief_section": {{
      "injunction_applicable": true,
      "injunction_guidance": "string",
      "damages_applicable": true,
      "damages_guidance": "string",
      "costs_guidance": "string"
    }},
    "operative_portion_template": "string"
  }}
}}

Return ONLY valid JSON. No markdown. No explanation. No json fences. Plain text only in all string values."""

    try:
        raw = _call_gemini(prompt)
        cleaned = _strip_json_fences(raw)
        result = json.loads(cleaned)
        if not isinstance(result, dict):
            raise ValueError("Master analysis returned non-dict")
        result["generation_method"] = "live"
        return result
    except Exception as e:
        logger.warning(f"master_legal_analysis failed: {e}. Fallback triggered.")
        fallback_facts = {
            "trademark_nature": f"Registered trademark '{trademark}'",
            "dispute_summary": (
                f"Dispute between {party_a} and {party_b} regarding trademark '{trademark}'. "
                f"Type: {dispute.get('dispute_type', 'Unknown')}."
            ),
            "right_source": dispute.get("right_source", "statute"),
            "key_facts": [
                f"Dispute involves trademark '{trademark}'",
                f"Dispute type: {dispute.get('dispute_type', 'Unknown')}",
                f"Contract between parties: {'Yes' if dispute.get('has_contract') else 'No'}",
            ],
            "relief_sought": "Injunction, damages, and costs as per dispute description",
            "legal_relationship": (
                "Contractual relationship" if dispute.get("has_contract") else "No prior contractual relationship"
            ),
            "affects_third_parties": dispute.get("affects_third_parties", False),
            "dispute_category": dispute.get("dispute_type", "infringement").lower().replace(" ", "_"),
        }

        if arbitrability_status == "ARBITRABLE":
            fallback_issues = [
                f"Whether the arbitral tribunal has jurisdiction to adjudicate the present dispute between {party_a} and {party_b} concerning the trademark '{trademark}' under the Arbitration and Conciliation Act, 1996?",
                f"Whether {party_b} has infringed and/or violated the trademark rights of {party_a} in the mark '{trademark}' under Sections 29 and 30 of the Trade Marks Act, 1999?",
                f"Whether {party_a} is entitled to injunctive relief, rendition of accounts, and/or damages against {party_b} for the alleged infringement of trademark '{trademark}'?",
                f"Whether {party_a} is entitled to costs of the arbitration proceedings?",
            ]
        else:
            fallback_issues = [
                f"Whether the mark used by {party_b} is deceptively similar to the registered trademark '{trademark}' of {party_a} under Section 29 of the Trade Marks Act, 1999 so as to cause confusion in the minds of consumers?",
                f"Whether {party_b} has infringed the registered trademark rights of {party_a} in the mark '{trademark}' under Sections 29 and 30 of the Trade Marks Act, 19_99 and/or is passing off its goods as those of {party_a}?",
                f"Whether {party_a} is entitled to a permanent injunction restraining {party_b} from using the mark '{trademark}' or any deceptively similar mark under Section 135 of the Trade Marks Act, 19_99?",
                f"Whether {party_a} is entitled to damages and/or account of profits from {party_b} and if so to what quantum?",
            ]

        fallback_statutes = [
            {
                "statute": "Section 29 of Trade Marks Act 1999",
                "statute_text": "Infringement of registered trademark for confusingly similar marks.",
                "principle_name": "Trademark infringement standard",
                "judicial_interpretation": "Parle Products v JP Co AIR 1972 SC 1359 — overall impression test.",
                "application": "Applies to assess similarity between the disputed marks.",
            },
            {
                "statute": "Section 30 of Trade Marks Act 1999",
                "statute_text": "Limits on effect of registered trademark and defenses.",
                "principle_name": "Statutory defenses",
                "judicial_interpretation": "Courts interpret statutory limits narrowly in confusing similarity cases.",
                "application": "Respondent may rely on statutory limits if applicable.",
            },
            {
                "statute": "Section 7 of Arbitration and Conciliation Act 1996",
                "statute_text": "Defines arbitration agreement and its scope.",
                "principle_name": "Arbitration agreement requirement",
                "judicial_interpretation": "Booz Allen (2011) — rights in rem are not arbitrable.",
                "application": "Determines if the dispute can proceed in arbitration.",
            },
        ]

        fallback_award = {
            "jurisdiction_finding": (
                f"This tribunal has jurisdiction over the dispute between {party_a} and {party_b} concerning the trademark '{trademark}'."
                if arbitrability_status == "ARBITRABLE"
                else f"This dispute between {party_a} and {party_b} concerning the trademark '{trademark}' is not arbitrable and must be referred to the competent civil court."
            ),
            "findings_on_issues": [
                {
                    "issue_number": idx + 1,
                    "issue": issue,
                    "finding_options": [
                        "Under Section 29 of the Trade Marks Act 1999, the respondent has infringed the claimant's trademark rights.",
                        "Under Section 29 of the Trade Marks Act 1999, the respondent has not infringed the claimant's trademark rights and the claim fails.",
                    ],
                    "applicable_law": "Section 29 of Trade Marks Act 1999",
                }
                for idx, issue in enumerate(fallback_issues)
            ],
            "relief_section": {
                "injunction_applicable": True,
                "injunction_guidance": "Consider permanent injunction if infringement is established.",
                "damages_applicable": True,
                "damages_guidance": "Assess actual damages and account of profits.",
                "costs_guidance": "Costs to follow the event.",
            },
            "operative_portion_template": "Template for operative portion or court referral direction.",
        }

        return {
            "extracted_facts": fallback_facts,
            "legal_issues": fallback_issues,
            "statutory_provisions": fallback_statutes,
            "award_framework": fallback_award,
            "generation_method": "fallback"
        }
