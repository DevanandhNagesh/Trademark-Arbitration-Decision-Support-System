"""tests/test_auth.py

Comprehensive tests for authentication, JWT issuance, password hashing,
database user model, and protected FastAPI endpoints in api/main.py.
"""

import os
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import Base, User, get_db
from auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    get_current_user,
    require_role,
    require_admin,
)
from api.main import app

# Test database setup (in-memory SQLite with StaticPool so all threads share the memory db)
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_database():
    """Create fresh database tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Password Hashing & JWT Unit Tests
# ---------------------------------------------------------------------------

def test_password_hashing_and_verification():
    raw_password = "SecureArbitrationPassword2026!"
    hashed = get_password_hash(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_creation_and_decoding():
    payload_data = {"sub": "lawyer@chambers.in", "role": "lawyer"}
    token = create_access_token(payload_data)

    decoded = decode_access_token(token)
    assert decoded.get("sub") == "lawyer@chambers.in"
    assert decoded.get("role") == "lawyer"
    assert "exp" in decoded


# ---------------------------------------------------------------------------
# FastAPI Endpoints Tests: /auth/signup & /auth/login
# ---------------------------------------------------------------------------

def test_signup_successful(client):
    response = client.post(
        "/auth/signup",
        json={"email": "advocate@delhihc.in", "password": "Password123!", "role": "lawyer"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["user"]["email"] == "advocate@delhihc.in"
    assert data["user"]["role"] == "lawyer"


def test_signup_duplicate_email_fails(client):
    client.post(
        "/auth/signup",
        json={"email": "same@firm.in", "password": "Password123!", "role": "company"},
    )
    response = client.post(
        "/auth/signup",
        json={"email": "same@firm.in", "password": "AnotherPassword123!", "role": "company"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_signup_invalid_role_fails(client):
    response = client.post(
        "/auth/signup",
        json={"email": "user@firm.in", "password": "Password123!", "role": "invalid_role"},
    )
    assert response.status_code == 400
    assert "invalid role" in response.json()["detail"].lower()


def test_login_successful(client):
    # Register user first
    client.post(
        "/auth/signup",
        json={"email": "arbitrator@odr.in", "password": "ArbitratorPass123", "role": "admin"},
    )

    # Login
    response = client.post(
        "/auth/login",
        json={"email": "arbitrator@odr.in", "password": "ArbitratorPass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["user"]["role"] == "admin"


def test_login_wrong_password_fails(client):
    client.post(
        "/auth/signup",
        json={"email": "counsel@firm.in", "password": "CorrectPass123", "role": "lawyer"},
    )
    response = client.post(
        "/auth/login",
        json={"email": "counsel@firm.in", "password": "WrongPassword"},
    )
    assert response.status_code == 401
    assert "invalid email or password" in response.json()["detail"].lower()


def test_login_nonexistent_user_fails(client):
    response = client.post(
        "/auth/login",
        json={"email": "ghost@nonexistent.in", "password": "AnyPassword"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Profile & Role Enforcement Tests
# ---------------------------------------------------------------------------

def test_get_current_user_profile(client):
    signup_res = client.post(
        "/auth/signup",
        json={"email": "counsel@delhi.in", "password": "SecurePass123", "role": "lawyer"},
    )
    token = signup_res.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["user"]["email"] == "counsel@delhi.in"


def test_admin_endpoint_role_enforcement(client):
    # Register regular lawyer
    lawyer_res = client.post(
        "/auth/signup",
        json={"email": "lawyer@court.in", "password": "LawyerPass123", "role": "lawyer"},
    )
    lawyer_token = lawyer_res.json()["access_token"]

    # Register admin
    admin_res = client.post(
        "/auth/signup",
        json={"email": "admin@dss.in", "password": "AdminPass123", "role": "admin"},
    )
    admin_token = admin_res.json()["access_token"]

    # Lawyer accessing admin endpoint should get 403 Forbidden
    forbidden_res = client.get("/admin/users", headers={"Authorization": f"Bearer {lawyer_token}"})
    assert forbidden_res.status_code == 403

    # Admin accessing admin endpoint should succeed
    success_res = client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert success_res.status_code == 200
    assert success_res.json()["count"] >= 2


# ---------------------------------------------------------------------------
# Protection of /analyze Endpoint
# ---------------------------------------------------------------------------

def test_analyze_requires_authentication_fails_without_token(client):
    form_data = {
        "party_a": "Brand A",
        "party_b": "Brand B",
        "trademark_name": "TESTMARK",
        "dispute_type": "Trademark Infringement",
        "has_contract": "true",
        "has_arbitration_clause": "true",
        "right_source": "contract",
        "affects_third_parties": "false",
        "dispute_description": "A" * 150,
    }

    # Request without Authorization header
    response = client.post("/analyze", data=form_data)
    assert response.status_code == 401
    assert "authentication required" in response.json()["detail"].lower()


def test_analyze_with_valid_token_authenticates_properly(client):
    signup_res = client.post(
        "/auth/signup",
        json={"email": "authorized@counsel.in", "password": "AuthPassword123", "role": "lawyer"},
    )
    token = signup_res.json()["access_token"]

    form_data = {
        "party_a": "Brand A",
        "party_b": "Brand B",
        "trademark_name": "TESTMARK",
        "dispute_type": "Trademark Infringement",
        "has_contract": "true",
        "has_arbitration_clause": "true",
        "right_source": "contract",
        "affects_third_parties": "false",
        "dispute_description": "Valid dispute description with sufficient length over 100 characters detailing contractual brand usage and arbitration clause between the parties.",
    }

    # Mock external LLM calls so the test runs fast and deterministically
    with patch("agents.gemini_agents._call_gemini", side_effect=Exception("forced mock fallback")):
        with patch("agents.adversarial_legal_agent.generate_adversarial_analysis", return_value={"generation_method": "fallback"}):
            response = client.post(
                "/analyze",
                data=form_data,
                headers={"Authorization": f"Bearer {token}"},
            )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
