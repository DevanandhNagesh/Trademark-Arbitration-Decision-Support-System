"""FastAPI application — main API entry point."""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pydantic_v1_compat  # noqa: F401 — must be before chromadb

from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from config import OUTPUT_DIR
from agents.arbitrability_agent import check_arbitrability
from agents.landmark_retrieval_agent import retrieve_landmarks, analyze_landmark_applicability
from agents.gemini_agents import (
    extract_dispute_facts,
    frame_legal_issues,
    identify_legal_principles,
    generate_award_framework,
    master_legal_analysis,
)
from agents.adversarial_legal_agent import generate_adversarial_analysis
from agents.report_generator import generate_dss_report
from agents.lawyer_finder_agent import (
    find_nearby_lawyers,
    find_lawyers_by_coordinates,
)

app = FastAPI(
    title="Trademark Arbitration Decision Support System",
    description="DSS for arbitrators handling trademark disputes in India",
    version="1.0.0",
)

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML file."""
    frontend_path = os.path.join(PROJECT_ROOT, "frontend", "index.html")
    if not os.path.exists(frontend_path):
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(frontend_path, media_type="text/html")


@app.post("/analyze")
async def analyze_dispute(
    party_a: str = Form(...),
    party_b: str = Form(...),
    trademark_name: str = Form(...),
    dispute_type: str = Form(...),
    has_contract: str = Form(...),
    has_arbitration_clause: str = Form("false"),
    right_source: str = Form(...),
    affects_third_parties: str = Form(...),
    dispute_description: str = Form(...),
):
    """Analyze a trademark dispute and generate DSS report."""
    try:
        # Parse boolean fields (form sends strings)
        has_contract_bool = has_contract.lower() in ("true", "yes", "1")
        has_arb_clause_bool = has_arbitration_clause.lower() in ("true", "yes", "1")
        affects_third_bool = affects_third_parties.lower() in ("true", "yes", "1")

        # 1. Build dispute dict
        dispute = {
            "party_a": party_a,
            "party_b": party_b,
            "trademark_name": trademark_name,
            "dispute_type": dispute_type,
            "has_contract": has_contract_bool,
            "has_arbitration_clause": has_arb_clause_bool,
            "right_source": right_source,
            "affects_third_parties": affects_third_bool,
            "dispute_description": dispute_description,
        }

        # 2. Arbitrability determination (deterministic — no LLM)
        arbitrability_result = check_arbitrability(dispute)

        # 3. Retrieve landmark cases (ChromaDB — no LLM)
        landmark_matches = retrieve_landmarks(dispute_description, arbitrability_result)

        # 5. Analyze landmark applicability (no LLM)
        landmark_analyses = [
            analyze_landmark_applicability(dispute, lm)
            for lm in landmark_matches
        ]

        # 4. Master legal analysis (Gemini) — single call
        master_result = master_legal_analysis(
            dispute,
            arbitrability_result,
            landmark_matches,
        )
        extracted_facts = master_result.get("extracted_facts") or {}
        issues = master_result.get("legal_issues") or []
        legal_principles = master_result.get("statutory_provisions") or []
        award_framework = master_result.get("award_framework") or {}

        # 5. Adversarial legal analysis (Gemini)
        adversarial_analysis = generate_adversarial_analysis(
            dispute,
            extracted_facts,
            arbitrability_result,
            landmark_matches,
            legal_principles,
        )

        # 9. Generate Word document report
        filepath = generate_dss_report(
            dispute,
            extracted_facts,
            arbitrability_result,
            landmark_matches,
            landmark_analyses,
            issues,
            legal_principles,
            award_framework,
            adversarial_analysis,
        )

        filename = os.path.basename(filepath)

        adv = adversarial_analysis if isinstance(adversarial_analysis, dict) else {}
        overall_position = adv.get("overall_legal_position", "") or ""
        adversarial_summary = {
            "law_for_claimant_count": len(adv.get("law_for_claimant", []) or []),
            "law_against_claimant_count": len(adv.get("law_against_claimant", []) or []),
            "options_available_count": len(adv.get("options_if_law_against", []) or []),
            "overall_position": overall_position[:150],
        }

        adversarial_preview = {
            "law_for_claimant": [
                item.get("statute", "") for item in (adv.get("law_for_claimant", []) or [])
            ],
            "law_against_claimant": [
                item.get("statute", "") for item in (adv.get("law_against_claimant", []) or [])
            ],
            "options_available": [
                item.get("option_title", "") for item in (adv.get("options_if_law_against", []) or [])
            ],
        }

        return JSONResponse(
            content={
                "status": "success",
                "arbitrability": arbitrability_result.status,
                "report_filename": filename,
                "download_url": f"/download/{filename}",
                "landmarks_retrieved": [lm.case_name for lm in landmark_matches],
                "issues_count": len(issues),
                "adversarial_summary": adversarial_summary,
                "adversarial_preview": adversarial_preview,
            }
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)},
        )


@app.get("/find-lawyers")
async def find_lawyers_endpoint(
    city: str,
    dispute_type: str = "trademark",
):
    """
    Find nearby trademark advocates by city name.
    City is geocoded server-side.
    User never types or sees coordinates.
    """
    try:
        result = find_nearby_lawyers(city, dispute_type)
        return result
    except Exception as e:
        return {
            "success": False,
            "city": city,
            "lawyers": [],
            "count": 0,
            "message": f"Search failed: {str(e)}",
        }


@app.get("/find-lawyers-by-location")
async def find_lawyers_by_location_endpoint(
    lat: float,
    lng: float,
    dispute_type: str = "trademark",
):
    """
    Find nearby trademark advocates using coordinates.
    Coordinates come from browser geolocation API.
    User never types or sees these coordinates.
    """
    try:
        result = find_lawyers_by_coordinates(
            lat, lng, dispute_type
        )
        return result
    except Exception as e:
        return {
            "success": False,
            "lawyers": [],
            "count": 0,
            "message": f"Location search failed: {str(e)}",
        }


@app.get("/download/{filename}")
async def download_report(filename: str):
    """Download a generated DSS report."""
    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(filename)
    filepath = os.path.join(OUTPUT_DIR, safe_filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(
        path=filepath,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
