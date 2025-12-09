# scraper.py

import time
import random
import re
import datetime
from typing import List, Dict, Any
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from requests.exceptions import RequestException

from config import (
    get_proxy_dict,
    FLIGHT_ROUTES,
    HOTEL_STAYS,
    RENTAL_CAR_OFFERS,
    PROVIDER_NAME,
    DEFAULT_CURRENCY,
    TRAVEL_DATE_STR,
)

# A couple of realistic desktop headers to rotate
HEADERS_LIST = [
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-IN,en;q=0.9",
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Safari/605.1.15"
        ),
        "Accept-Language": "en-IN,en;q=0.9",
    },
]


def fetch_page(url: str, timeout: int = 40) -> str:
    """
    Fetch an HTML page via Thordata residential proxy.
    """
    proxies = get_proxy_dict()
    headers = random.choice(HEADERS_LIST)

    resp = requests.get(
        url,
        headers=headers,
        proxies=proxies,
        timeout=timeout,
    )
    resp.raise_for_status()
    if not resp.encoding:
        resp.encoding = "utf-8"
    return resp.text


# ---------------------------------------------------------------------------
# Skyscanner (Flights)
# ---------------------------------------------------------------------------

def parse_skyscanner_page(html: str) -> Dict[str, Any]:
    """
    Parse a Skyscanner route page.

    Strategy:
      1. Look specifically for the 'Cheapest deal' text block and grab
         the first '₹ <number>' that appears near it.
      2. If that fails, fall back to 'min of all ₹ amounts' as backup.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title from <h1>, if present
    h1 = soup.find("h1")
    title = h1.get_text(strip=True) if h1 else ""

    full_text = soup.get_text(" ", strip=True)

    # --- Step 1: try to extract price near "Cheapest deal" label ---
    cheapest_price = None
    cheapest_raw = ""

    m = re.search(r"Cheapest deal[^₹]*₹\s*([\d,]+)", full_text, flags=re.IGNORECASE)
    if m:
        numeric_str = m.group(1)
        try:
            cheapest_price = float(numeric_str.replace(",", ""))
            cheapest_raw = f"₹ {numeric_str}"
        except ValueError:
            cheapest_price = None

    # --- Step 2: fallback – min of all ₹ amounts on page ---
    if cheapest_price is None:
        matches = re.findall(r"₹\s*([\d,]+)", full_text)
        if matches:
            values = []
            for val in matches:
                try:
                    values.append(int(val.replace(",", "")))
                except ValueError:
                    continue
            if values:
                v = min(values)
                cheapest_price = float(v)
                cheapest_raw = f"₹ {v:,}"

    return {
        "page_title": title,
        "currency": DEFAULT_CURRENCY,
        "price": cheapest_price,
        "price_raw": cheapest_raw,
    }


def scrape_flight_prices() -> List[Dict[str, Any]]:
    """
    Scrape all configured flight routes from Skyscanner via Thordata.
    Returns a list of dicts ready for DB insertion (without timestamp).
    """
    results: List[Dict[str, Any]] = []

    for route in FLIGHT_ROUTES:
        url = route["url"]
        print(
            f"\n[INFO] Scraping flight {route['route_name']} "
            f"({route['route_code']}) – {PROVIDER_NAME} – {url}"
        )

        try:
            html = fetch_page(url)
            parsed = parse_skyscanner_page(html)

            if parsed["price"] is None:
                print(
                    f"[WARN] No price found on page for {route['route_code']}. "
                    f"Check if Skyscanner changed the layout."
                )
            else:
                print(
                    f"[OK] Cheapest visible flight price for {route['route_code']}: "
                    f"{parsed['price_raw']} ({parsed['price']})"
                )

            row = {
                "route_code": route["route_code"],
                "origin": route["origin"],
                "destination": route["destination"],
                "route_name": route["route_name"],
                "provider_name": PROVIDER_NAME,
                "currency": parsed["currency"],
                "price": parsed["price"],
                "price_raw": parsed["price_raw"],
                "url": url,
                "travel_date": route.get("travel_date"),
            }
            results.append(row)

            # be polite, avoid hammering
            time.sleep(random.uniform(1.0, 2.5))

        except RequestException as e:
            print(
                f"[WARN] Skipping flight {route['route_code']} due to HTTP/network error: {e}"
            )
        except Exception as e:
            print(
                f"[WARN] Skipping flight {route['route_code']} due to unexpected error: {e}"
            )

    return results


# ---------------------------------------------------------------------------
# OYO (Hotels)
# ---------------------------------------------------------------------------

def _build_oyo_url_with_dates(base_url: str) -> str:
    """
    Take a base city URL like:
        https://www.oyorooms.com/hotels-in-chennai/
    and attach date + sort=price ascending for TRAVEL_DATE_STR
    so that the first card is truly the cheapest for that date.
    """
    travel_dt = datetime.datetime.strptime(TRAVEL_DATE_STR, "%Y-%m-%d").date()
    checkin_dt = travel_dt
    checkout_dt = travel_dt + datetime.timedelta(days=1)

    checkin_str = checkin_dt.strftime("%d/%m/%Y")
    checkout_str = checkout_dt.strftime("%d/%m/%Y")

    params = {
        "checkin": checkin_str,
        "checkout": checkout_str,
        "guests": "1",
        "rooms": "1",
        "sort": "price",
        "sortOrder": "ascending",
    }

    query = urlencode(params)
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}{query}"


def parse_oyo_page(html: str) -> Dict[str, Any]:
    """
    Parse an OYO city/bucket page that is already:
      - filtered to a city, and
      - sorted by price ascending for a given date.

    Heuristic:
      - Find all '₹ <number>' patterns in the text IN ORDER.
      - Only look at the first N matches (e.g. 20), trusting the sort=price asc.
      - Ignore obviously bogus tiny numbers (< 300).
      - Take the minimum of what remains as the "starting from" price.
    """
    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(" ", strip=True)

    price = None
    price_raw = ""

    # Get matches IN ORDER
    ordered_values: List[int] = []
    for m in re.finditer(r"₹\s*([\d,]+)", full_text):
        num_str = m.group(1)
        try:
            ordered_values.append(int(num_str.replace(",", "")))
        except ValueError:
            continue

    # Consider only the first N values (top part of page/cards)
    N = 20
    top_values = ordered_values[:N]

    if top_values:
        # Filter out silly small numbers (fees, etc.)
        filtered = [v for v in top_values if v >= 300]

        chosen = None
        if filtered:
            chosen = min(filtered)
        else:
            # Fallback: if, for some weird reason, everything < 300
            chosen = min(top_values) if top_values else None

        if chosen is not None:
            price = float(chosen)
            price_raw = f"₹ {chosen:,}"

    return {
        "currency": "INR",
        "price": price,
        "price_raw": price_raw,
    }


def scrape_hotel_rates() -> List[Dict[str, Any]]:
    """
    Scrape hotel "buckets" from OYO via Thordata.

    For each city:
      - Start from a base URL in HOTEL_STAYS (e.g. hotels-in-chennai/).
      - Build a date-specific, price-sorted URL for TRAVEL_DATE_STR:
            ?checkin=07/12/2025&checkout=08/12/2025&sort=price&sortOrder=ascending
      - If the config url is a list (like Mumbai), apply that to each candidate.
      - Parse only the first block of prices to get a realistic "starting from" rate.
    """
    results: List[Dict[str, Any]] = []

    for stay in HOTEL_STAYS:
        raw_url_value = stay["url"]
        base_urls = (
            raw_url_value if isinstance(raw_url_value, list) else [raw_url_value]
        )

        # Build dated + sorted URLs for each base
        candidate_urls = [_build_oyo_url_with_dates(bu) for bu in base_urls]

        print(
            f"\n[INFO] Scraping OYO bucket {stay['hotel_name']} "
            f"in {stay['city']} – {candidate_urls[0]}"
        )

        chosen_url = None
        html = None

        # Try each URL until one works
        for candidate in candidate_urls:
            try:
                html = fetch_page(candidate, timeout=40)
                chosen_url = candidate
                break
            except RequestException as e:
                print(
                    f"[WARN] OYO attempt failed for {stay['hotel_code']} at "
                    f"{candidate}: {e}"
                )
            except Exception as e:
                print(
                    f"[WARN] Unexpected error fetching {candidate} for "
                    f"{stay['hotel_code']}: {e}"
                )

        if html is None:
            print(
                f"[WARN] Could not fetch any URL for {stay['hotel_code']}. "
                f"Skipping this OYO bucket."
            )
            continue

        try:
            parsed = parse_oyo_page(html)
            if parsed["price"] is None:
                print(
                    f"[WARN] No OYO price found on page for {stay['hotel_code']}. "
                    f"Check if layout/selector needs updating."
                )
            else:
                print(
                    f"[OK] Parsed OYO price for {stay['hotel_code']}: "
                    f"{parsed['price_raw']} ({parsed['price']})"
                )

            # Use the actual check-in/checkout we used in the URL, for clarity
            travel_dt = datetime.datetime.strptime(TRAVEL_DATE_STR, "%Y-%m-%d").date()
            checkin_dt = travel_dt
            checkout_dt = travel_dt + datetime.timedelta(days=1)
            checkin_str = checkin_dt.strftime("%Y-%m-%d")
            checkout_str = checkout_dt.strftime("%Y-%m-%d")

            # IMPORTANT: url must be a plain string for DB insert
            row = {
                "hotel_code": stay["hotel_code"],
                "city": stay["city"],
                "hotel_name": stay["hotel_name"],
                "provider_name": "OYO",
                "currency": parsed["currency"],
                "price": parsed["price"],
                "price_raw": parsed["price_raw"],
                "url": chosen_url,
                "checkin_date": checkin_str,
                "checkout_date": checkout_str,
            }
            results.append(row)

            time.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            print(
                f"[WARN] Error parsing hotel {stay['hotel_code']}: {e}"
            )

    return results


# ---------------------------------------------------------------------------
# Gozo Cabs (Rental cars)
# ---------------------------------------------------------------------------

def parse_gozo_page(html: str) -> Dict[str, Any]:
    """
    Parse a Gozo Cabs route page.

    Strategy:
      - Find all '₹ <number>' patterns.
      - Ignore obviously wrong values like 0 or very tiny numbers (< 100),
        since these are usually "₹ 0 cancellation fee", etc.
      - Take the minimum of the remaining values as a reasonable "starting from" price.
    """
    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text(" ", strip=True)

    matches = re.findall(r"₹\s*([\d,]+)", full_text)
    price = None
    price_raw = ""

    if matches:
        values: List[int] = []
        for val in matches:
            try:
                values.append(int(val.replace(",", "")))
            except ValueError:
                continue

        # Filter out garbage like 0 / < 100
        filtered = [v for v in values if v >= 100]

        chosen = None
        if filtered:
            chosen = min(filtered)
        elif values:
            # fallback if everything was < 100 for some reason
            chosen = min(values)

        if chosen is not None:
            price = float(chosen)
            price_raw = f"₹ {chosen:,}"

    return {
        "currency": "INR",
        "price": price,
        "price_raw": price_raw,
    }


def scrape_rental_car_prices() -> List[Dict[str, Any]]:
    """
    Scrape configured rental cab routes (Gozo Cabs) via Thordata.
    Returns a list of dicts ready for DB insertion (without timestamp).
    """
    results: List[Dict[str, Any]] = []

    for offer in RENTAL_CAR_OFFERS:
        url = offer["url"]
        print(
            f"\n[INFO] Scraping rental cab {offer['route_name']} "
            f"({offer['rental_code']}) – Gozo Cabs – {url}"
        )

        try:
            html = fetch_page(url, timeout=40)
            parsed = parse_gozo_page(html)

            if parsed["price"] is None:
                print(
                    f"[WARN] No rental price found on page for {offer['rental_code']}. "
                    f"Check if layout/selector needs updating."
                )
            else:
                print(
                    f"[OK] Lowest visible cab price for {offer['rental_code']}: "
                    f"{parsed['price_raw']} ({parsed['price']})"
                )

            row = {
                "rental_code": offer["rental_code"],
                "pickup_city": offer["pickup_city"],
                "dropoff_city": offer["dropoff_city"],
                "pickup_date": offer.get("travel_date"),
                "dropoff_date": None,
                "route_name": offer["route_name"],
                "provider_name": "Gozo Cabs",
                "currency": parsed["currency"],
                "price": parsed["price"],
                "price_raw": parsed["price_raw"],
                "url": url,
                "travel_date": offer.get("travel_date"),
            }
            results.append(row)

            time.sleep(random.uniform(1.0, 2.0))

        except RequestException as e:
            print(
                f"[WARN] Skipping rental {offer['rental_code']} due to HTTP/network error: {e}"
            )
        except Exception as e:
            print(
                f"[WARN] Skipping rental {offer['rental_code']} due to unexpected error: {e}"
            )

    return results