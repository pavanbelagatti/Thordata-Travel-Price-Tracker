import pandas as pd
import streamlit as st
from sqlalchemy import text

from db import get_engine
from config import OPENAI_API_KEY, TRAVEL_DATE_STR
from langchain_openai import ChatOpenAI


# ---------- Data loaders ----------


@st.cache_data(ttl=60)
def load_flight_data() -> pd.DataFrame:
    engine = get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(
            text(
                "SELECT * FROM flight_prices "
                "ORDER BY scraped_at_utc ASC, route_code ASC"
            ),
            conn,
        )
    return df


@st.cache_data(ttl=60)
def load_hotel_data() -> pd.DataFrame:
    engine = get_engine()
    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                text(
                    "SELECT * FROM hotel_rates "
                    "ORDER BY scraped_at_utc ASC, hotel_code ASC"
                ),
                conn,
            )
        return df
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=60)
def load_rental_data() -> pd.DataFrame:
    engine = get_engine()
    try:
        with engine.connect() as conn:
            df = pd.read_sql(
                text(
                    "SELECT * FROM rental_car_prices "
                    "ORDER BY scraped_at_utc ASC, rental_code ASC"
                ),
                conn,
            )
        return df
    except Exception:
        return pd.DataFrame()


# ---------- Flight helpers ----------


def build_flight_summary(df: pd.DataFrame) -> str:
    df = df.copy()
    df["scraped_at_utc"] = pd.to_datetime(df["scraped_at_utc"])
    lines = []
    for (route, tdate), group in df.groupby(["route_code", "travel_date"]):
        latest = group.sort_values("scraped_at_utc").iloc[-1]
        min_price = group["price"].min()
        max_price = group["price"].max()
        avg_price = group["price"].mean()
        lines.append(
            f"Route {route} ({latest['route_name']}) on {tdate} via {latest['provider_name']} "
            f"in {latest['currency']}: latest={latest['price']}, "
            f"min={min_price}, max={max_price}, avg={avg_price:.2f}."
        )
    return "\n".join(lines)


def get_cheapest_route(df: pd.DataFrame) -> str:
    df_valid = df.dropna(subset=["price"]).copy()
    if df_valid.empty:
        return "No valid flight prices yet."
    row = df_valid.sort_values("price").iloc[0]
    return (
        f"{row['route_code']} ({row['route_name']}) — "
        f"{row['price']} {row['currency']} for {row['travel_date']}."
    )


# ---------- Hotel helpers ----------


def get_cheapest_hotel(df: pd.DataFrame) -> str:
    df_valid = df.dropna(subset=["price"]).copy()
    if df_valid.empty:
        return "No valid hotel prices yet."
    row = df_valid.sort_values("price").iloc[0]
    return (
        f"{row['hotel_name']} ({row['hotel_code']}) in {row['city']} — "
        f"{row['price']} {row['currency']} starting price."
    )


# ---------- Rental car helpers ----------


def get_cheapest_rental_car(df: pd.DataFrame) -> str:
    df_valid = df.dropna(subset=["price"]).copy()
    if df_valid.empty:
        return "No valid rental car prices yet."
    if "scraped_at_utc" in df_valid.columns:
        df_valid["scraped_at_utc"] = pd.to_datetime(df_valid["scraped_at_utc"])
        latest = (
            df_valid.sort_values("scraped_at_utc")
            .groupby("rental_code")
            .tail(1)
        )
    else:
        latest = df_valid

    row = latest.sort_values("price").iloc[0]
    return (
        f"{row['rental_code']} ({row['route_name']}) — "
        f"{row['price']} {row['currency']} from {row['pickup_city']} to {row['dropoff_city']}."
    )


# ---------- LLM QA ----------


def build_global_summary(
    df_flights: pd.DataFrame, df_hotels: pd.DataFrame, df_rentals: pd.DataFrame
) -> str:
    parts = []

    if not df_flights.empty:
        parts.append("FLIGHTS:\n" + build_flight_summary(df_flights))

    if not df_hotels.empty:
        dfh = df_hotels.copy()
        dfh["scraped_at_utc"] = pd.to_datetime(dfh["scraped_at_utc"])
        lines = []
        for (code, city), group in dfh.groupby(["hotel_code", "city"]):
            latest = group.sort_values("scraped_at_utc").iloc[-1]
            min_price = group["price"].min()
            max_price = group["price"].max()
            avg_price = group["price"].mean()
            lines.append(
                f"Hotel bucket {latest['hotel_name']} ({code}) in {city}: "
                f"latest={latest['price']}, min={min_price}, "
                f"max={max_price}, avg={avg_price:.2f} {latest['currency']}."
            )
        parts.append("HOTELS:\n" + "\n".join(lines))

    if not df_rentals.empty:
        dfr = df_rentals.copy()
        if "scraped_at_utc" in dfr.columns:
            dfr["scraped_at_utc"] = pd.to_datetime(dfr["scraped_at_utc"])
        lines = []
        for code, group in dfr.groupby("rental_code"):
            latest = (
                group.sort_values("scraped_at_utc").iloc[-1]
                if "scraped_at_utc" in group.columns
                else group.iloc[-1]
            )
            min_price = group["price"].min()
            max_price = group["price"].max()
            avg_price = group["price"].mean()
            lines.append(
                f"Rental {code} ({latest['route_name']}): "
                f"latest={latest['price']}, min={min_price}, "
                f"max={max_price}, avg={avg_price:.2f} {latest['currency']}."
            )
        parts.append("RENTAL_CARS:\n" + "\n".join(lines))

    return "\n\n".join(parts)


def answer_question(
    question: str,
    df_flights: pd.DataFrame,
    df_hotels: pd.DataFrame,
    df_rentals: pd.DataFrame,
) -> str:
    q_lower = question.lower()

    if "rental" in q_lower and ("cheapest" in q_lower or "lowest" in q_lower):
        return get_cheapest_rental_car(df_rentals)

    if ("flight" in q_lower or "route" in q_lower) and (
        "cheapest" in q_lower or "lowest" in q_lower
    ):
        return get_cheapest_route(df_flights)

    if "hotel" in q_lower and ("cheapest" in q_lower or "lowest" in q_lower):
        return get_cheapest_hotel(df_hotels)

    if not OPENAI_API_KEY:
        return (
            "OPENAI_API_KEY is not configured. I cannot use the LLM for "
            "free-form analysis, but you can still inspect the tables."
        )

    summary = build_global_summary(df_flights, df_hotels, df_rentals)

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )
    prompt = (
        "You are an assistant analyzing travel prices from flights, hotels, "
        "and rental cars. You will get a structured summary of the data and "
        "must answer the user's question using ONLY that information. "
        "If the data doesn't support an answer, say you don't know.\n\n"
        f"Data summary:\n{summary}\n\n"
        f"User question: {question}\n\n"
        "Answer clearly and concisely."
    )
    resp = llm.invoke(prompt)
    return getattr(resp, "content", resp)


# ---------- Streamlit main ----------


def main():
    st.set_page_config(page_title="Thordata-Powered Travel Price Tracker", layout="wide")
    st.title("🌍 Thordata-Powered Travel Price Tracker")

    st.markdown(
        "Tracking Skyscanner (and similar) pages via Thordata residential proxies, "
        "storing results in SingleStore, and exploring prices for flights, hotels, "
        "and rental cars in a Streamlit + LLM dashboard."
    )

    df_flights = load_flight_data()
    df_hotels = load_hotel_data()
    df_rentals = load_rental_data()

    # ---------- Top banner: 3-way cheapest snapshot ----------
    st.subheader("🔥 Current Lowest Prices Snapshot")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Flights**")
        st.write(get_cheapest_route(df_flights) if not df_flights.empty else "No data yet.")

    with col2:
        st.markdown("**Hotels (OYO buckets)**")
        st.write(get_cheapest_hotel(df_hotels) if not df_hotels.empty else "No data yet.")

    with col3:
        st.markdown("**Rental Cars**")
        st.write(get_cheapest_rental_car(df_rentals) if not df_rentals.empty else "No data yet.")

    st.markdown("---")

    tab_flights, tab_hotels, tab_rentals, tab_assistant = st.tabs(
        ["Flights", "Hotels (OYO buckets)", "Rental Cars", "Ask the Assistant"]
    )

    # Flights tab
    with tab_flights:
        if df_flights.empty:
            st.warning("No flight data found yet. Run `python run_scraper.py` first.")
        else:
            st.subheader("Flight Prices (Latest Snapshot)")
            latest = (
                df_flights.sort_values("scraped_at_utc")
                .groupby(["route_code", "provider_name", "travel_date"])
                .tail(1)
            )
            st.dataframe(
                latest[
                    [
                        "route_code",
                        "route_name",
                        "travel_date",
                        "provider_name",
                        "currency",
                        "price",
                        "price_raw",
                        "scraped_at_utc",
                        "url",
                    ]
                ].reset_index(drop=True)
            )

            st.subheader("Price History Over Time")
            chart_df = df_flights[["scraped_at_utc", "route_code", "price"]].dropna()
            if not chart_df.empty:
                chart_df = chart_df.rename(columns={"scraped_at_utc": "time"})
                st.line_chart(
                    chart_df,
                    x="time",
                    y="price",
                    color="route_code",
                )
            else:
                st.info("No flight price history data to plot yet.")

    # Hotels tab
    with tab_hotels:
        if df_hotels.empty:
            st.info("No hotel data found yet.")
        else:
            st.subheader("Hotel Buckets (Latest Snapshot)")
            dfh = df_hotels.copy()
            dfh["scraped_at_utc"] = pd.to_datetime(dfh["scraped_at_utc"])
            latest_h = (
                dfh.sort_values("scraped_at_utc")
                .groupby(["hotel_code", "city"])
                .tail(1)
            )
            cols = [
                "hotel_code",
                "hotel_name",
                "city",
                "provider_name",
                "currency",
                "price",
                "price_raw",
                "scraped_at_utc",
                "url",
            ]
            cols = [c for c in cols if c in latest_h.columns]
            st.dataframe(latest_h[cols].reset_index(drop=True))

    # Rentals tab
    with tab_rentals:
        if df_rentals.empty:
            st.info("No rental car data found yet.")
        else:
            st.subheader("Rental Cars Prices (Latest Snapshot)")
            dfr = df_rentals.copy()
            if "scraped_at_utc" in dfr.columns:
                dfr["scraped_at_utc"] = pd.to_datetime(dfr["scraped_at_utc"])

            if "scraped_at_utc" in dfr.columns:
                latest_r = (
                    dfr.sort_values("scraped_at_utc")
                    .groupby("rental_code")
                    .tail(1)
                )
            else:
                latest_r = dfr

            cols = [
                "rental_code",
                "pickup_city",
                "dropoff_city",
                "pickup_date",
                "dropoff_date",
                "provider_name",
                "currency",
                "price",
                "price_raw",
                "scraped_at_utc",
                "url",
            ]
            cols = [c for c in cols if c in latest_r.columns]
            st.dataframe(latest_r[cols].reset_index(drop=True))

    # Assistant tab
    with tab_assistant:
        st.subheader("Ask the Travel Price Assistant")
        st.markdown(
            "All entries are scraped snapshots around the target travel date "
            f"**{TRAVEL_DATE_STR}** where applicable.\n\n"
            "Example questions:\n"
            "- Which flight route is currently cheapest?\n"
            "- How do OYO buckets compare by starting price?\n"
            "- Are rental cabs cheaper than flights for nearby cities?\n"
        )
        user_q = st.text_area("Your question", height=140)
        if st.button("Ask", key="ask_assistant"):
            if not user_q.strip():
                st.warning("Please type a question first.")
            else:
                with st.spinner("Thinking..."):
                    answer = answer_question(
                        user_q, df_flights, df_hotels, df_rentals
                    )
                st.markdown("**Answer:**")
                st.write(answer)


if __name__ == "__main__":
    main()