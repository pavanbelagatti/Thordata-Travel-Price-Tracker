# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# ============ Thordata proxy settings ============
PROXY_HOST = os.getenv("PROXY_HOST")
PROXY_PORT = os.getenv("PROXY_PORT")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASS = os.getenv("PROXY_PASS")

# Set USE_PROXY=0 in .env if you want to temporarily disable Thordata
USE_PROXY = os.getenv("USE_PROXY", "1") == "1"


def get_proxy_dict():
    """
    Build a requests-compatible proxies dict using your Thordata
    residential proxy credentials. If USE_PROXY=0, returns {}.
    """
    if not USE_PROXY:
        return {}
    if not all([PROXY_HOST, PROXY_PORT, PROXY_USER, PROXY_PASS]):
        raise ValueError("Proxy credentials are not fully set in .env")

    proxy_url = f"http://{PROXY_USER}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}"
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


# ============ SingleStore settings ============
SINGLESTORE_URI = os.getenv("SINGLESTORE_URI")
if not SINGLESTORE_URI:
    raise ValueError("SINGLESTORE_URI is not set in .env")


# ============ OpenAI (for LangChain chat) ============
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# ============ Global Travel Date ============
TRAVEL_DATE_STR = "2025-12-07"  # 7 Dec 2025


# ============ Flight routes (Skyscanner) ============
PROVIDER_NAME = "Skyscanner"
DEFAULT_CURRENCY = "INR"

FLIGHT_ROUTES = [
    {
        "route_code": "BLR-DEL",
        "origin": "BLR",
        "destination": "DEL",
        "route_name": "Bengaluru → Delhi (Indira Gandhi)",
        "url": "https://www.skyscanner.co.in/routes/blr/del/bengaluru-to-delhi-indira-gandhi-international.html",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "route_code": "DEL-BLR",
        "origin": "DEL",
        "destination": "BLR",
        "route_name": "Delhi (Indira Gandhi) → Bengaluru",
        "url": "https://www.skyscanner.co.in/routes/del/blr/delhi-indira-gandhi-international-to-bengaluru.html",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "route_code": "BLR-BOM",
        "origin": "BLR",
        "destination": "BOM",
        "route_name": "Bengaluru → Mumbai",
        "url": "https://www.skyscanner.co.in/routes/blr/bom/bengaluru-to-mumbai.html",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "route_code": "BOM-BLR",
        "origin": "BOM",
        "destination": "BLR",
        "route_name": "Mumbai → Bengaluru",
        "url": "https://www.skyscanner.co.in/routes/bom/blr/mumbai-to-bengaluru.html",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "route_code": "DEL-BOM",
        "origin": "DEL",
        "destination": "BOM",
        "route_name": "Delhi (Indira Gandhi) → Mumbai",
        "url": "https://www.skyscanner.co.in/routes/del/bom/delhi-indira-gandhi-international-to-mumbai.html",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "route_code": "BOM-DEL",
        "origin": "BOM",
        "destination": "DEL",
        "route_name": "Mumbai → Delhi (Indira Gandhi)",
        "url": "https://www.skyscanner.co.in/routes/bom/del/mumbai-to-indira-gandhi-international.html",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "route_code": "BLR-DXB",
        "origin": "BLR",
        "destination": "DXB",
        "route_name": "Bengaluru → Dubai",
        "url": "https://www.skyscanner.co.in/routes/blr/dxb/bengaluru-to-dubai.html",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "route_code": "DXB-BLR",
        "origin": "DXB",
        "destination": "BLR",
        "route_name": "Dubai → Bengaluru",
        "url": "https://www.skyscanner.co.in/routes/dxb/blr/dubai-to-bengaluru.html",
        "travel_date": TRAVEL_DATE_STR,
    },
]


# ============ Hotels (OYO city buckets with Mumbai fallback) ============
HOTEL_STAYS = [
    {
        "hotel_code": "OYO-BLR-ALL",
        "city": "Bengaluru",
        "hotel_name": "All OYO Hotels in Bangalore",
        "url": "https://www.oyorooms.com/hotels-in-bangalore/",
        "checkin_date": TRAVEL_DATE_STR,
        "checkout_date": TRAVEL_DATE_STR,
    },
    {
        "hotel_code": "OYO-MAA-ALL",
        "city": "Chennai",
        "hotel_name": "All OYO Hotels in Chennai",
        "url": "https://www.oyorooms.com/hotels-in-chennai/",
        "checkin_date": TRAVEL_DATE_STR,
        "checkout_date": TRAVEL_DATE_STR,
    },

    # ✔ MUMBAI – Now using 3 fallback URLs
    {
        "hotel_code": "OYO-BOM-ALL",
        "city": "Mumbai",
        "hotel_name": "All OYO Hotels in Mumbai",
        "url": [
            "https://www.oyorooms.com/oyos-in-mumbai/",
            "https://www.oyorooms.com/hotels-in-in-mumbai/",
            "https://www.oyorooms.com/budget-hotels-in-mumbai/",
        ],
        "checkin_date": TRAVEL_DATE_STR,
        "checkout_date": TRAVEL_DATE_STR,
    },

    {
        "hotel_code": "OYO-HYD-ALL",
        "city": "Hyderabad",
        "hotel_name": "All OYO Hotels in Hyderabad",
        "url": "https://www.oyorooms.com/hotels-in-hyderabad/",
        "checkin_date": TRAVEL_DATE_STR,
        "checkout_date": TRAVEL_DATE_STR,
    },
    {
        "hotel_code": "OYO-CCU-ALL",
        "city": "Kolkata",
        "hotel_name": "All OYO Hotels in Kolkata",
        "url": "https://www.oyorooms.com/hotels-in-kolkata/",
        "checkin_date": TRAVEL_DATE_STR,
        "checkout_date": TRAVEL_DATE_STR,
    },
    {
        "hotel_code": "OYO-DEL-ALL",
        "city": "Delhi",
        "hotel_name": "All OYO Hotels in Delhi",
        "url": "https://www.oyorooms.com/hotels-in-delhi/",
        "checkin_date": TRAVEL_DATE_STR,
        "checkout_date": TRAVEL_DATE_STR,
    },
]


# ============ Rental cab pages (Gozo Cabs) ============
RENTAL_CAR_OFFERS = [
    {
        "rental_code": "BLR-LOCAL-GOZO",
        "pickup_city": "Bengaluru",
        "dropoff_city": "Bengaluru",
        "route_name": "Bengaluru Local Day Rental (Gozo Cabs)",
        "url": "https://www.gozocabs.com/car-rental/bangalore",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "rental_code": "BLR-MYS-GOZO",
        "pickup_city": "Bengaluru",
        "dropoff_city": "Mysuru",
        "route_name": "Bengaluru → Mysuru One-way (Gozo Cabs)",
        "url": "https://www.gozocabs.com/book-taxi/bangalore-mysore",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "rental_code": "BLR-CHENNAI-GOZO",
        "pickup_city": "Bengaluru",
        "dropoff_city": "Chennai",
        "route_name": "Bengaluru → Chennai One-way (Gozo Cabs)",
        "url": "https://www.gozocabs.com/book-taxi/bangalore-chennai",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "rental_code": "BLR-AIRPORT-GOZO",
        "pickup_city": "Bengaluru",
        "dropoff_city": "BLR Airport",
        "route_name": "Bengaluru → Kempegowda Airport (Gozo Cabs)",
        "url": "https://www.gozocabs.com/book-taxi/bangalore-bangalore_airport",
        "travel_date": TRAVEL_DATE_STR,
    },
    {
        "rental_code": "BLR-COORG-GOZO",
        "pickup_city": "Bengaluru",
        "dropoff_city": "Coorg",
        "route_name": "Bengaluru → Coorg One-way (Gozo Cabs)",
        "url": "https://www.gozocabs.com/book-taxi/bangalore-coorgmadikeri",
        "travel_date": TRAVEL_DATE_STR,
    },
]