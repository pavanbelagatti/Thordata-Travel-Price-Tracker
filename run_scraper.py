import datetime
from datetime import timezone

from db import (
    get_engine,
    create_tables_if_not_exists,
    insert_flight_prices,
    insert_hotel_rates,
    insert_rental_car_prices,
)
from scraper import (
    scrape_flight_prices,
    scrape_hotel_rates,
    scrape_rental_car_prices,
)
from config import TRAVEL_DATE_STR


def main():
    print("=== Thordata-Powered Travel Price Scraper ===")
    print(f"[INFO] Target travel date label: {TRAVEL_DATE_STR}")

    # Ensure all tables exist
    create_tables_if_not_exists()

    engine = get_engine()
    scraped_at = datetime.datetime.now(timezone.utc)

    # -------- Flights --------
    flight_rows = scrape_flight_prices()
    rows_for_db = []
    for r in flight_rows:
        rows_for_db.append(
            {
                "route_code": r["route_code"],
                "origin": r["origin"],
                "destination": r["destination"],
                "route_name": r["route_name"],
                "provider_name": r["provider_name"],
                "currency": r["currency"],
                "price": r["price"],
                "price_raw": r["price_raw"],
                "url": r["url"],
                "travel_date": r.get("travel_date"),
                "scraped_at_utc": scraped_at,
            }
        )

    insert_flight_prices(engine, rows_for_db)
    print(f"[OK] Inserted {len(rows_for_db)} flight rows into flight_prices.")

    # -------- Hotels (OYO buckets) --------
    hotel_rows = scrape_hotel_rates()
    hotel_rows_for_db = []
    for h in hotel_rows:
        hotel_rows_for_db.append(
            {
                "hotel_code": h["hotel_code"],
                "city": h["city"],
                "hotel_name": h["hotel_name"],
                "provider_name": h["provider_name"],
                "currency": h["currency"],
                "price": h["price"],
                "price_raw": h["price_raw"],
                "url": h["url"],
                "checkin_date": h.get("checkin_date"),
                "checkout_date": h.get("checkout_date"),
                "scraped_at_utc": scraped_at,
            }
        )

    insert_hotel_rates(engine, hotel_rows_for_db)
    print(f"[OK] Inserted {len(hotel_rows_for_db)} hotel rows into hotel_rates.")

    # -------- Rental cars (Gozo) --------
    rental_rows = scrape_rental_car_prices()
    rental_rows_for_db = []
    for r in rental_rows:
        rental_rows_for_db.append(
            {
                "rental_code": r["rental_code"],
                "pickup_city": r["pickup_city"],
                "dropoff_city": r["dropoff_city"],
                "pickup_date": TRAVEL_DATE_STR,  # or keep None if you prefer
                "dropoff_date": None,
                "route_name": r["route_name"],
                "provider_name": r["provider_name"],
                "currency": r["currency"],
                "price": r["price"],
                "price_raw": r["price_raw"],
                "url": r["url"],
                "travel_date": r.get("travel_date"),
                "scraped_at_utc": scraped_at,
            }
        )

    insert_rental_car_prices(engine, rental_rows_for_db)
    print(f"[OK] Inserted {len(rental_rows_for_db)} rental rows into rental_car_prices.")

    print("\n[DONE] Scraping + ingestion complete.")


if __name__ == "__main__":
    main()