# db.py
from sqlalchemy import create_engine, text
from config import SINGLESTORE_URI


def get_engine():
    return create_engine(SINGLESTORE_URI, pool_pre_ping=True)


def create_tables_if_not_exists():
    """
    Create tables for flights, hotels, and rental cars in SingleStore if they don't exist.
    Also ensure newer columns (like route_name and travel_date for rentals) exist via ALTER TABLE.
    """
    ddl_flights = """
    CREATE TABLE IF NOT EXISTS flight_prices (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        route_code VARCHAR(32),
        origin VARCHAR(8),
        destination VARCHAR(8),
        route_name VARCHAR(255),
        provider_name VARCHAR(64),
        currency VARCHAR(8),
        price DECIMAL(12,2),
        price_raw VARCHAR(64),
        url TEXT,
        travel_date DATE,
        scraped_at_utc TIMESTAMP(6)
    );
    """

    ddl_hotels = """
    CREATE TABLE IF NOT EXISTS hotel_rates (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        hotel_code VARCHAR(64),
        city VARCHAR(128),
        hotel_name VARCHAR(255),
        provider_name VARCHAR(64),
        currency VARCHAR(8),
        price DECIMAL(12,2),
        price_raw VARCHAR(64),
        url TEXT,
        checkin_date DATE,
        checkout_date DATE,
        scraped_at_utc TIMESTAMP(6)
    );
    """

    ddl_rentals = """
    CREATE TABLE IF NOT EXISTS rental_car_prices (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        rental_code VARCHAR(64),
        pickup_city VARCHAR(128),
        dropoff_city VARCHAR(128),
        pickup_date DATE,
        dropoff_date DATE,
        -- route_name & travel_date may be missing on older tables; we add via ALTER TABLE.
        provider_name VARCHAR(64),
        currency VARCHAR(8),
        price DECIMAL(12,2),
        price_raw VARCHAR(64),
        url TEXT,
        scraped_at_utc TIMESTAMP(6)
    );
    """

    engine = get_engine()
    with engine.connect() as conn:
        # Create base tables if missing (no-op if already there)
        conn.execute(text(ddl_flights))
        conn.execute(text(ddl_hotels))
        conn.execute(text(ddl_rentals))

        # ---- Migration 1: ensure rental_car_prices.route_name exists ----
        try:
            conn.execute(
                text(
                    """
                    ALTER TABLE rental_car_prices
                    ADD COLUMN route_name VARCHAR(255) AFTER dropoff_date;
                    """
                )
            )
        except Exception as e:
            # Ignore "duplicate column" error; re-raise anything else.
            if "Duplicate column name" not in str(e):
                raise

        # ---- Migration 2: ensure rental_car_prices.travel_date exists ----
        try:
            conn.execute(
                text(
                    """
                    ALTER TABLE rental_car_prices
                    ADD COLUMN travel_date DATE AFTER url;
                    """
                )
            )
        except Exception as e:
            if "Duplicate column name" not in str(e):
                raise

        conn.commit()


def insert_flight_prices(engine, rows):
    """
    Insert a list of rows into flight_prices.
    Each row is a dict with fields matching the INSERT below.
    """
    if not rows:
        return

    insert_sql = text(
        """
        INSERT INTO flight_prices (
            route_code,
            origin,
            destination,
            route_name,
            provider_name,
            currency,
            price,
            price_raw,
            url,
            travel_date,
            scraped_at_utc
        ) VALUES (
            :route_code,
            :origin,
            :destination,
            :route_name,
            :provider_name,
            :currency,
            :price,
            :price_raw,
            :url,
            :travel_date,
            :scraped_at_utc
        )
        """
    )

    with engine.begin() as conn:
        conn.execute(insert_sql, rows)


def insert_hotel_rates(engine, rows):
    """
    Insert a list of rows into hotel_rates.
    Each row is a dict with fields matching the INSERT below.
    """
    if not rows:
        return

    insert_sql = text(
        """
        INSERT INTO hotel_rates (
            hotel_code,
            city,
            hotel_name,
            provider_name,
            currency,
            price,
            price_raw,
            url,
            checkin_date,
            checkout_date,
            scraped_at_utc
        ) VALUES (
            :hotel_code,
            :city,
            :hotel_name,
            :provider_name,
            :currency,
            :price,
            :price_raw,
            :url,
            :checkin_date,
            :checkout_date,
            :scraped_at_utc
        )
        """
    )

    with engine.begin() as conn:
        conn.execute(insert_sql, rows)


def insert_rental_car_prices(engine, rows):
    """
    Insert a list of rows into rental_car_prices.
    Each row is a dict with fields matching the INSERT below.
    """
    if not rows:
        return

    insert_sql = text(
        """
        INSERT INTO rental_car_prices (
            rental_code,
            pickup_city,
            dropoff_city,
            pickup_date,
            dropoff_date,
            route_name,
            provider_name,
            currency,
            price,
            price_raw,
            url,
            travel_date,
            scraped_at_utc
        ) VALUES (
            :rental_code,
            :pickup_city,
            :dropoff_city,
            :pickup_date,
            :dropoff_date,
            :route_name,
            :provider_name,
            :currency,
            :price,
            :price_raw,
            :url,
            :travel_date,
            :scraped_at_utc
        )
        """
    )

    with engine.begin() as conn:
        conn.execute(insert_sql, rows)