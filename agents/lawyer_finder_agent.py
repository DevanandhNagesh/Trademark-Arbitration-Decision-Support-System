import os
import requests
from dotenv import load_dotenv
from logging_config import logger

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

GOOGLE_PLACES_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
PLACES_BASE = "https://maps.googleapis.com/maps/api/place"


VALID_RADII = [5, 10, 25, 50]
DEFAULT_RADIUS_KM = 10


def validate_radius(radius: int | str) -> int:
    """Validate radius against allowed values: 5, 10, 25, 50 km."""
    try:
        r = int(radius)
        if r in VALID_RADII:
            return r
        raise ValueError(f"Invalid radius {r}. Must be one of {VALID_RADII} km.")
    except (ValueError, TypeError):
        raise ValueError(f"Invalid radius {radius}. Must be one of {VALID_RADII} km.")


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
    except Exception as e:
        logger.exception(f"Exception in geocode_city for {city}: {e}")
        return (None, None)


def search_trademark_lawyers(lat: float, lng: float, radius_km: int = DEFAULT_RADIUS_KM) -> list:
    """Search Google Places for trademark lawyers near given coordinates."""
    try:
        if not GOOGLE_PLACES_API_KEY:
            return []

        try:
            radius = validate_radius(radius_km)
        except ValueError:
            radius = DEFAULT_RADIUS_KM

        url = f"{PLACES_BASE}/nearbysearch/json"
        params = {
            "location": f"{lat},{lng}",
            "radius": radius * 1000,
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
        for place in results:
            place_id = place.get("place_id") or ""
            geometry = place.get("geometry", {})
            location = geometry.get("location", {})
            place_lat = float(location["lat"]) if "lat" in location and location["lat"] is not None else None
            place_lng = float(location["lng"]) if "lng" in location and location["lng"] is not None else None

            # Photo URL proxy server-side with HMAC token without exposing API key
            photos = place.get("photos", [])
            photo_url = None
            if photos and isinstance(photos, list) and len(photos) > 0:
                first_photo = photos[0]
                if isinstance(first_photo, dict) and first_photo.get("photo_reference"):
                    photo_ref = first_photo["photo_reference"]
                    try:
                        from auth import generate_signed_photo_url
                        photo_url = generate_signed_photo_url(photo_ref, maxwidth=400)
                    except Exception as err:
                        logger.warning(f"Failed to generate signed photo URL: {err}")
                        photo_url = f"/places/photo?photo_reference={photo_ref}&maxwidth=400"

            lawyers.append(
                {
                    "name": place.get("name") or "Unknown Advocate",
                    "address": place.get("vicinity") or place.get("formatted_address") or "Address not available",
                    "latitude": place_lat,
                    "longitude": place_lng,
                    "rating": float(place["rating"]) if place.get("rating") is not None else None,
                    "user_ratings_total": int(place["user_ratings_total"]) if place.get("user_ratings_total") is not None else (int(place["total_ratings"]) if place.get("total_ratings") is not None else None),
                    "phone": place.get("formatted_phone_number") or place.get("international_phone_number") or None,
                    "website": place.get("website") or None,
                    "maps_url": f"https://www.google.com/maps/place/?q=place_id:{place_id}" if place_id else None,
                    "photo_url": photo_url,
                    "place_id": place_id or None,
                    "open_now": place.get("opening_hours", {}).get("open_now") if isinstance(place.get("opening_hours"), dict) else None,
                }
            )

        return lawyers
    except Exception as e:
        logger.exception(f"Exception in search_trademark_lawyers at ({lat}, {lng}): {e}")
        return []


def find_nearby_lawyers(city: str, dispute_type: str = "trademark", radius_km: int = DEFAULT_RADIUS_KM) -> dict:
    """Find nearby trademark advocates by city name."""
    try:
        try:
            radius = validate_radius(radius_km)
        except ValueError as ve:
            return {
                "success": False,
                "city": city,
                "radius_km": radius_km,
                "lawyers": [],
                "count": 0,
                "message": str(ve),
            }

        if not GOOGLE_PLACES_API_KEY:
            return {
                "success": True,
                "city": city,
                "radius_km": radius,
                "lawyers": [
                    {
                        "name": "Bar Council of India Directory",
                        "address": "Visit bci.org.in to find registered trademark advocates",
                        "latitude": None,
                        "longitude": None,
                        "rating": None,
                        "user_ratings_total": None,
                        "phone": None,
                        "website": "https://www.barcouncilofindia.org/",
                        "maps_url": "https://www.google.com/maps/search/trademark+lawyer+"
                        + city.replace(" ", "+")
                        + "+India",
                        "photo_url": None,
                        "place_id": None,
                        "open_now": None,
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
                "radius_km": radius,
                "lawyers": [],
                "count": 0,
                "message": "Could not locate "
                + city
                + ". Please try a major city name like Mumbai, Delhi, or Chennai.",
            }

        lawyers = search_trademark_lawyers(lat, lng, radius_km=radius)
        if len(lawyers) > 0:
            message = f"Found {len(lawyers)} advocates within {radius} km of {city}"
        else:
            message = f"No advocates found within {radius} km of {city}. Try increasing search radius or contact your local Bar Council."

        return {
            "success": True,
            "city": city,
            "coordinates": {"lat": lat, "lng": lng},
            "radius_km": radius,
            "lawyers": lawyers,
            "count": len(lawyers),
            "fallback": False,
            "message": message,
        }
    except Exception as e:
        logger.exception(f"Exception in find_nearby_lawyers for {city}: {e}")
        return {
            "success": False,
            "city": city,
            "radius_km": radius_km,
            "lawyers": [],
            "count": 0,
            "message": f"Search failed: {str(e)}",
        }


def find_lawyers_by_coordinates(lat: float, lng: float, dispute_type: str = "trademark", radius_km: int = DEFAULT_RADIUS_KM) -> dict:
    """Find nearby trademark advocates using coordinates."""
    try:
        try:
            radius = validate_radius(radius_km)
        except ValueError as ve:
            return {
                "success": False,
                "coordinates": {"lat": lat, "lng": lng},
                "radius_km": radius_km,
                "lawyers": [],
                "count": 0,
                "message": str(ve),
            }

        lawyers = search_trademark_lawyers(lat, lng, radius_km=radius)
        if len(lawyers) > 0:
            message = f"Found {len(lawyers)} advocates within {radius} km of your location"
        else:
            message = f"No advocates found within {radius} km of your location. Try a larger radius or search by city name."

        return {
            "success": True,
            "coordinates": {"lat": lat, "lng": lng},
            "radius_km": radius,
            "lawyers": lawyers,
            "count": len(lawyers),
            "message": message,
        }
    except Exception as e:
        logger.exception(f"Exception in find_lawyers_by_coordinates at ({lat}, {lng}): {e}")
        return {
            "success": False,
            "coordinates": {"lat": lat, "lng": lng},
            "radius_km": radius_km,
            "lawyers": [],
            "count": 0,
            "message": f"Location search failed: {str(e)}",
        }
