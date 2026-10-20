"""tests/test_lawyer_finder.py

Unit and integration tests for Lawyer Finder agent and Google Maps API endpoints:
- Radius validation (5, 10, 25, 50 km)
- Field mapping with mocked Google Places response (handling missing optional fields)
- /config/maps authentication requirement, browser_key & map_id return, and absence of Places API key
- Hardened photo proxy security: rejection of missing/invalid/expired tokens, rejection of bad references
- Server-side signed photo URL proxy generation
- Verification that GOOGLE_PLACES_API_KEY is NEVER exposed in any response payload
"""

import json
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.lawyer_finder_agent import (
    DEFAULT_RADIUS_KM,
    VALID_RADII,
    find_lawyers_by_coordinates,
    find_nearby_lawyers,
    search_trademark_lawyers,
    validate_radius,
)
from api.main import app
from auth import create_access_token, generate_signed_photo_url

client = TestClient(app)

MOCK_SECRET_KEY = "AIzaSy_SUPER_SECRET_PLACES_API_KEY_9999"


# ── 1. Radius Validation Tests ─────────────────────────────────────────

def test_validate_radius_valid_values():
    for r in [5, 10, 25, 50]:
        assert validate_radius(r) == r
        assert validate_radius(str(r)) == r


def test_validate_radius_invalid_values():
    invalid_cases = [0, 1, 15, 30, 100, -10, "invalid", None]
    for inv in invalid_cases:
        with pytest.raises(ValueError):
            validate_radius(inv)


# ── 2. Field Mapping with Mocked Places Response ────────────────────────

MOCK_PLACES_RESULTS = [
    {
        "name": "Apex IP Law Chambers",
        "vicinity": "Barakhamba Road, Connaught Place, New Delhi",
        "geometry": {
            "location": {"lat": 28.6315, "lng": 77.2245}
        },
        "rating": 4.9,
        "user_ratings_total": 87,
        "place_id": "ChIJ_apex_law_12345",
        "photos": [
            {
                "photo_reference": "Aap_photo_reference_token_xyz_888",
                "width": 1200,
                "height": 800,
            }
        ],
        "opening_hours": {"open_now": True},
        "formatted_phone_number": "+91 11 2345 6789",
        "website": "https://www.apexiplaw.in",
    },
    {
        "name": "Minimalist Advocate Practice",
        # Missing vicinity, geometry, rating, total_ratings, photos, phone, website
        "place_id": "ChIJ_minimal_67890",
    },
]


def test_field_mapping_complete_and_missing_fields():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "OK",
        "results": MOCK_PLACES_RESULTS,
    }

    with patch("agents.lawyer_finder_agent.GOOGLE_PLACES_API_KEY", MOCK_SECRET_KEY):
        with patch("requests.get", return_value=mock_resp):
            lawyers = search_trademark_lawyers(28.63, 77.22, radius_km=10)

    assert len(lawyers) == 2

    # Case 1: Complete fields
    l1 = lawyers[0]
    assert l1["name"] == "Apex IP Law Chambers"
    assert l1["address"] == "Barakhamba Road, Connaught Place, New Delhi"
    assert l1["latitude"] == 28.6315
    assert l1["longitude"] == 77.2245
    assert l1["rating"] == 4.9
    assert l1["user_ratings_total"] == 87
    assert l1["phone"] == "+91 11 2345 6789"
    assert l1["website"] == "https://www.apexiplaw.in"
    assert l1["open_now"] is True
    assert l1["maps_url"] == "https://www.google.com/maps/place/?q=place_id:ChIJ_apex_law_12345"
    # Signed URL contains photo_reference, maxwidth, expires, and sig
    assert l1["photo_url"].startswith("/places/photo?photo_reference=Aap_photo_reference_token_xyz_888")
    assert "&expires=" in l1["photo_url"]
    assert "&sig=" in l1["photo_url"]
    assert MOCK_SECRET_KEY not in l1["photo_url"]

    # Case 2: Missing optional fields must be None / null, never invented
    l2 = lawyers[1]
    assert l2["name"] == "Minimalist Advocate Practice"
    assert l2["address"] == "Address not available"
    assert l2["latitude"] is None
    assert l2["longitude"] is None
    assert l2["rating"] is None
    assert l2["user_ratings_total"] is None
    assert l2["phone"] is None
    assert l2["website"] is None
    assert l2["open_now"] is None
    assert l2["photo_url"] is None
    assert l2["maps_url"] == "https://www.google.com/maps/place/?q=place_id:ChIJ_minimal_67890"


# ── 3. /config/maps Endpoint Tests ─────────────────────────────────────

def test_config_maps_requires_authentication():
    # Calling without Authorization header must return 401
    resp = client.get("/config/maps")
    assert resp.status_code == 401


def test_config_maps_returns_keys_and_never_leaks_places_key():
    from db import User
    from auth import get_current_user

    mock_user = User(id=1, email="lawyer@chambers.in", role="lawyer")
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        with patch.dict(os.environ, {
            "GOOGLE_PLACES_API_KEY": MOCK_SECRET_KEY,
            "GOOGLE_MAPS_BROWSER_KEY": "AIzaSy_BROWSER_MAPS_KEY_PUBLIC_1234",
            "GOOGLE_MAPS_MAP_ID": "dss_dark_map_id_5678",
        }):
            resp = client.get("/config/maps", headers={"Authorization": "Bearer mock_token"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "success"
            assert data["browser_key"] == "AIzaSy_BROWSER_MAPS_KEY_PUBLIC_1234"
            assert data["map_id"] == "dss_dark_map_id_5678"
            # Crucial: Places secret key MUST NOT be present
            assert MOCK_SECRET_KEY not in resp.text
            assert "AIzaSy_SUPER_SECRET" not in resp.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ── 4. Photo Proxy Hardening Tests ─────────────────────────────────────

def test_photo_proxy_rejects_bad_photo_reference():
    # Bad references (path traversal, non-alphanumeric, special characters) must fail with 400
    bad_refs = [
        "../../etc/passwd",
        "bad ref with spaces",
        "bad$char!",
        "<script>alert(1)</script>",
    ]
    for bad in bad_refs:
        res = client.get(f"/places/photo?photo_reference={bad}&expires=9999999999&sig=fakesig")
        assert res.status_code == 400
        assert "Invalid photo_reference" in res.json()["detail"]


def test_photo_proxy_rejects_missing_or_invalid_signature():
    valid_ref = "Aap_photo_reference_token_xyz_888"

    # Missing signature or expires
    res_no_sig = client.get(f"/places/photo?photo_reference={valid_ref}")
    assert res_no_sig.status_code == 403

    # Tampered signature
    res_tampered = client.get(f"/places/photo?photo_reference={valid_ref}&expires=9999999999&sig=invalid_sig_abc123")
    assert res_tampered.status_code == 403


def test_photo_proxy_rejects_expired_signature():
    valid_ref = "Aap_photo_reference_token_xyz_888"
    # Generate URL with negative expiry (already expired)
    expired_url = generate_signed_photo_url(valid_ref, maxwidth=400, expires_in_sec=-30)
    res_expired = client.get(expired_url)
    assert res_expired.status_code == 403
    assert "expired" in res_expired.json()["detail"].lower()


def test_photo_proxy_valid_request_success():
    valid_ref = "Aap_photo_reference_token_xyz_888"
    valid_url = generate_signed_photo_url(valid_ref, maxwidth=400, expires_in_sec=600)

    mock_photo_resp = MagicMock()
    mock_photo_resp.status_code = 200
    mock_photo_resp.content = b"\xFF\xD8\xFF\xE0JPEG_MOCK_IMAGE_BYTES"
    mock_photo_resp.headers = {"content-type": "image/jpeg"}

    with patch("os.getenv", return_value=MOCK_SECRET_KEY):
        with patch("requests.get", return_value=mock_photo_resp) as mock_get:
            res = client.get(valid_url)
            assert res.status_code == 200
            assert res.content == b"\xFF\xD8\xFF\xE0JPEG_MOCK_IMAGE_BYTES"
            assert res.headers["content-type"] == "image/jpeg"
            # Verify Places API key was used upstream only
            upstream_call_url = mock_get.call_args[0][0]
            assert MOCK_SECRET_KEY in upstream_call_url
            # Response must NOT leak the secret key
            assert MOCK_SECRET_KEY.encode() not in res.content


# ── 5. Places Key Absent from All Search Payloads ──────────────────────

def test_api_key_never_leaked_in_agent_payloads():
    """Ensure that the Google Places API key is NEVER present in any returned payload."""
    mock_places_resp = MagicMock()
    mock_places_resp.status_code = 200
    mock_places_resp.json.return_value = {
        "status": "OK",
        "results": MOCK_PLACES_RESULTS,
    }

    mock_geocode_resp = MagicMock()
    mock_geocode_resp.status_code = 200
    mock_geocode_resp.json.return_value = {
        "status": "OK",
        "results": [{"geometry": {"location": {"lat": 28.6139, "lng": 77.2090}}}],
    }

    def mock_requests_get(url, *args, **kwargs):
        if "textsearch" in url:
            return mock_geocode_resp
        return mock_places_resp

    with patch("agents.lawyer_finder_agent.GOOGLE_PLACES_API_KEY", MOCK_SECRET_KEY):
        with patch("requests.get", side_effect=mock_requests_get):
            # 1. By city
            city_res = find_nearby_lawyers("New Delhi", radius_km=25)
            city_json = json.dumps(city_res)
            assert MOCK_SECRET_KEY not in city_json
            assert city_res["success"] is True
            assert city_res["radius_km"] == 25
            assert len(city_res["lawyers"]) == 2
            # Verify photo_url is signed relative proxy format
            assert city_res["lawyers"][0]["photo_url"].startswith("/places/photo?photo_reference=")
            assert "&sig=" in city_res["lawyers"][0]["photo_url"]
            assert MOCK_SECRET_KEY not in city_res["lawyers"][0]["photo_url"]

            # 2. By coordinates
            coord_res = find_lawyers_by_coordinates(28.61, 77.20, radius_km=50)
            coord_json = json.dumps(coord_res)
            assert MOCK_SECRET_KEY not in coord_json
            assert coord_res["success"] is True
            assert coord_res["radius_km"] == 50


def test_api_endpoints_radius_and_key_protection():
    """Test FastAPI GET /find-lawyers and /find-lawyers-by-location."""
    mock_places_resp = MagicMock()
    mock_places_resp.status_code = 200
    mock_places_resp.json.return_value = {
        "status": "OK",
        "results": MOCK_PLACES_RESULTS,
    }

    mock_geocode_resp = MagicMock()
    mock_geocode_resp.status_code = 200
    mock_geocode_resp.json.return_value = {
        "status": "OK",
        "results": [{"geometry": {"location": {"lat": 19.0760, "lng": 72.8777}}}],
    }

    def mock_requests_get(url, *args, **kwargs):
        if "textsearch" in url:
            return mock_geocode_resp
        return mock_places_resp

    with patch("agents.lawyer_finder_agent.GOOGLE_PLACES_API_KEY", MOCK_SECRET_KEY):
        with patch("requests.get", side_effect=mock_requests_get):
            # Valid radius 25
            r1 = client.get("/find-lawyers?city=Mumbai&radius_km=25")
            assert r1.status_code == 200
            data1 = r1.json()
            assert data1["success"] is True
            assert data1["radius_km"] == 25
            assert MOCK_SECRET_KEY not in r1.text

            # Invalid radius returns failure or message
            r_inv = client.get("/find-lawyers?city=Mumbai&radius_km=99")
            assert r_inv.status_code == 200
            data_inv = r_inv.json()
            assert data_inv["success"] is False
            assert "Invalid radius" in data_inv["message"]

            # Valid by coordinates
            r2 = client.get("/find-lawyers-by-location?lat=19.07&lng=72.87&radius_km=5")
            assert r2.status_code == 200
            data2 = r2.json()
            assert data2["success"] is True
            assert data2["radius_km"] == 5
            assert MOCK_SECRET_KEY not in r2.text
