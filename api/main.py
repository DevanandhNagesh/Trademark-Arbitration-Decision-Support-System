"""FastAPI application — main API entry point."""

import os
import sys

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pydantic_v1_compat  # noqa: F401 — must be before chromadb

from fastapi import FastAPI, Form, HTTPException, Depends, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import time

from config import OUTPUT_DIR, ALLOWED_ORIGINS
from logging_config import logger
from db import init_db, get_db, User
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    require_admin,
    VALID_ROLES,
)
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
from agents.citation_verifier import verify_citations
from agents.report_generator import generate_dss_report
from agents.lawyer_finder_agent import (
    find_nearby_lawyers,
    find_lawyers_by_coordinates,
)
from sqlalchemy.orm import Session

# Initialize database schema
init_db()

app = FastAPI(
    title="Trademark Arbitration Decision Support System",
    description="DSS for arbitrators handling trademark disputes in India",
    version="1.0.0",
)

# Enable CORS for allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        formatted_process_time = f"{process_time:.2f}ms"
        logger.info(
            f"Request - Method: {request.method} - Path: {request.url.path} - "
            f"Status: {response.status_code} - Latency: {formatted_process_time}"
        )
        return response
    except Exception as e:
        process_time = (time.time() - start_time) * 1000
        formatted_process_time = f"{process_time:.2f}ms"
        logger.exception(
            f"Request Failed - Method: {request.method} - Path: {request.url.path} - "
            f"Error: {str(e)} - Latency: {formatted_process_time}"
        )
        raise

@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML file."""
    frontend_path = os.path.join(PROJECT_ROOT, "frontend", "index.html")
    if not os.path.exists(frontend_path):
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(frontend_path, media_type="text/html")


@app.get("/auth")
@app.get("/auth.html")
async def serve_auth_page():
    """Serve the authentication login/signup page."""
    auth_page = os.path.join(PROJECT_ROOT, "frontend", "auth.html")
    if not os.path.exists(auth_page):
        raise HTTPException(status_code=404, detail="Auth page not found")
    return FileResponse(auth_page, media_type="text/html")


# ── Authentication Endpoints ──────────────────────────────────────────

@app.post("/auth/signup")
async def signup(
    request: Request,
    db: Session = Depends(get_db),
):
    """Register a new user account with role (lawyer, company, admin)."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))
        role = str(body.get("role", "lawyer")).strip().lower()
    else:
        form_data = await request.form()
        email = str(form_data.get("email", "")).strip().lower()
        password = str(form_data.get("password", ""))
        role = str(form_data.get("role", "lawyer")).strip().lower()

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")
    if not password or len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{role}'. Allowed roles: {list(VALID_ROLES)}",
        )

    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    hashed_password = get_password_hash(password)
    new_user = User(email=email, hashed_password=hashed_password, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.email, "role": new_user.role})

    return {
        "status": "success",
        "message": "User registered successfully.",
        "access_token": access_token,
        "token_type": "bearer",
        "user": new_user.to_dict(),
    }


@app.post("/auth/login")
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate user credentials and issue JWT token."""
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        email = str(body.get("email", "")).strip().lower()
        password = str(body.get("password", ""))
    else:
        form_data = await request.form()
        email = str(form_data.get("email", "")).strip().lower()
        password = str(form_data.get("password", ""))

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email, "role": user.role})

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": user.to_dict(),
    }


@app.get("/auth/me")
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Get profile of current authenticated user."""
    return {"status": "success", "user": current_user.to_dict()}


@app.get("/admin/users")
async def list_users_admin(
    admin_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only endpoint: list all registered users."""
    users = db.query(User).all()
    return {
        "status": "success",
        "admin": admin_user.email,
        "count": len(users),
        "users": [u.to_dict() for u in users],
    }


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
    current_user: User = Depends(get_current_user),
):
    """Analyze a trademark dispute and generate DSS report (Requires Authentication)."""
    try:
        logger.info(f"Analysis initiated by user: {current_user.email} (Role: {current_user.role})")
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
        landmark_matches = retrieve_landmarks(
            dispute_description,
            arbitrability_result,
            dispute_type_label=dispute_type,
        )

        # 5. Analyze landmark applicability (no LLM)
        landmark_analyses = [
            analyze_landmark_applicability(dispute, lm)
            for lm in landmark_matches
        ]

        master_result = master_legal_analysis(
            dispute,
            arbitrability_result,
            landmark_matches,
        )
        master_method = master_result.get("generation_method", "live")
        generation_methods = {
            "facts": master_method,
            "issues": master_method,
            "principles": master_method,
            "framework": master_method,
        }
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
        adv_method = adversarial_analysis.get("generation_method", "live")
        generation_methods["adversarial"] = adv_method

        # 6. Verify case citations against landmark matches and registry
        citation_verifications = verify_citations(
            statutory_provisions=legal_principles,
            adversarial_analysis=adversarial_analysis,
            landmark_matches=landmark_matches,
        )

        # 7. Generate Word document report
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
            generation_methods=generation_methods,
            citation_verifications=citation_verifications,
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
                "citation_verifications": citation_verifications,
                "narrative_warning": arbitrability_result.narrative_warning,
                "requires_manual_review": arbitrability_result.requires_manual_review,
                "review_reason": arbitrability_result.review_reason,
                "contract_narrative_mismatch": arbitrability_result.contract_narrative_mismatch,
                "generation_method": "fallback" if (master_method == "fallback" or adv_method == "fallback") else "live",
            }
        )

    except Exception as e:
        logger.exception(f"Unhandled exception in /analyze: {e}")
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


app.mount("/", StaticFiles(directory=os.path.join(PROJECT_ROOT, "frontend")), name="frontend")


if __name__ == "__main__":
    reload_flag = os.getenv("ENV", "development") == "development"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload_flag)
