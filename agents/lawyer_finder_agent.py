import os
import requests
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
PLACES_BASE = "https://maps.googleapis.com/maps/api/place"


def geocode_city(city: str) -> tuple:
    """Convert a city name string to lat/lng coordinates."""
    try:
        if not GOOGLE_PLACES_API_KEY:
            return (None, None)

        url = f"{PLACES_BASE}/textsearch/json"
        params = {
            "query": f"{city} India",
            "key": GOOGLE_PLACES_API_KEY,
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return (None, None)

        data = response.json()
        if data.get("status") != "OK":
            return (None, None)
        results = data.get("results", [])
        if not results:
            return (None, None)

        location = results[0].get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lng = location.get("lng")
        if lat is None or lng is None:
            return (None, None)

        return (float(lat), float(lng))
    except Exception:
        return (None, None)


def search_trademark_lawyers(lat: float, lng: float, radius_km: int = 10) -> list:
    """Search Google Places for trademark lawyers near given coordinates."""
    try:
        if not GOOGLE_PLACES_API_KEY:
            return []

        url = f"{PLACES_BASE}/nearbysearch/json"
        params = {
            "location": f"{lat},{lng}",
            "radius": radius_km * 1000,
            "keyword": "trademark lawyer advocate intellectual property",
            "type": "lawyer",
            "key": GOOGLE_PLACES_API_KEY,
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
            return []

        data = response.json()
        if data.get("status") != "OK":
            return []
        results = data.get("results", [])
        lawyers = []
        for place in results[:5]:
            place_id = place.get("place_id", "")
            lawyers.append(
                {
                    "name": place.get("name", "Unknown"),
                    "address": place.get("vicinity", "Address not available"),
                    "rating": place.get("rating", None),
                    "total_ratings": place.get("user_ratings_total", 0),
                    "place_id": place_id,
                    "open_now": place.get("opening_hours", {}).get("open_now", None),
                    "maps_url": "https://www.google.com/maps/place/?q=place_id:" + place_id,
                }
            )

        return lawyers
    except Exception:
        return []


def find_nearby_lawyers(city: str, dispute_type: str = "trademark") -> dict:
    """Find nearby trademark advocates by city name."""
    try:
        if not GOOGLE_PLACES_API_KEY:
            return {
                "success": True,
                "city": city,
                "lawyers": [
                    {
                        "name": "Bar Council of India Directory",
                        "address": "Visit bci.org.in to find registered trademark advocates",
                        "rating": None,
                        "total_ratings": 0,
                        "place_id": None,
                        "open_now": None,
                        "maps_url": "https://www.google.com/maps/search/trademark+lawyer+"
                        + city.replace(" ", "+")
                        + "+India",
                    }
                ],
                "count": 1,
                "fallback": True,
                "message": "Configure GOOGLE_PLACES_API_KEY for live results.",
            }

        lat, lng = geocode_city(city)
        if lat is None:
            return {
                "success": False,
                "city": city,
                "lawyers": [],
                "count": 0,
                "message": "Could not locate "
                + city
                + ". Please try a major city name like Mumbai, Delhi, or Chennai.",
            }

        lawyers = search_trademark_lawyers(lat, lng)
        if len(lawyers) > 0:
            message = "Found " + str(len(lawyers)) + " advocates near " + city
        else:
            message = (
                "No advocates found near "
                + city
                + ". Try the nearest major city or contact your local Bar Council."
            )

        return {
            "success": True,
            "city": city,
            "lawyers": lawyers,
            "count": len(lawyers),
            "fallback": False,
            "message": message,
        }
    except Exception:
        return {
            "success": False,
            "city": city,
            "lawyers": [],
            "count": 0,
            "message": "Search failed. Please try again.",
        }


def find_lawyers_by_coordinates(lat: float, lng: float, dispute_type: str = "trademark") -> dict:
    """Find nearby trademark advocates using coordinates."""
    try:
        lawyers = search_trademark_lawyers(lat, lng)
        if len(lawyers) > 0:
            message = "Found " + str(len(lawyers)) + " advocates near your location"
        else:
            message = (
                "No advocates found near your location. Try searching by city name instead."
            )

        return {
            "success": True,
            "lawyers": lawyers,
            "count": len(lawyers),
            "message": message,
        }
    except Exception:
        return {
            "success": False,
            "lawyers": [],
            "count": 0,
            "message": "Location search failed. Please enter your city below.",
        }
