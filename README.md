# 🌍 [Thordata](https://www.thordata.com/) Travel Price Tracker

A real-world travel price tracking pipeline that scrapes:

- ✈️ Flight prices (Skyscanner routes)

- 🏨 Hotel prices (OYO city buckets)

- 🚗 Rental cab prices (Gozo Cabs routes)

…using [Thordata residential proxies](https://www.thordata.com/products/residential-proxies), stores everything in SingleStore, and visualises it in a Streamlit dashboard with a small LLM-powered assistant.

This project is designed to showcase how robust scraping + a modern data platform + a simple UI can form the backbone for future Agentic AI / travel automation workflows.

## ✨ Features

- Scrapes live prices from trusted public travel providers

- Uses Thordata rotating residential proxies for reliable, CAPTCHA-free scraping

- Stores normalized data in SingleStore tables

- Streamlit-powered dashboard:

  - 📌 Current price snapshot

  - 📊 Price history charts

  - 🔍 Latest scraped entries

  - 🤖 LLM-powered Q&A panel for price insights

- Modular architecture — easy to extend to new cities, routes, or providers

## 🧰 Prerequisites

- Python 3.11+

- [Thordata proxy credentials](https://www.thordata.com/products/residential-proxies)

- SingleStore database (Helios free tier is enough)

- OpenAI API key (optional, for LLM Q&A panel)

- Git

## 📦 Project Structure
.

├─ config.py

├─ db.py

├─ scraper.py

├─ run_scraper.py

├─ dashboard_app.py

├─ requirements.txt

└─ .env   # not committed

## 🚀 Getting Started
### 1. Clone the repository

```
git clone https://github.com/pavanbelagatti/Thordata-Travel-Price-Tracker.git
```

```
cd Thordata-Travel-Price-Tracker
```

### 2. Create & activate a virtual environment

```
python -m venv myenv
```

```
source myenv/bin/activate   # macOS/Linux
```

OR

```
myenv\Scripts\activate      # Windows
```

### 3. Install dependencies
```
pip install --upgrade pip
pip install -r requirements.txt
```

### 🔑 Environment Configuration

Create a .env file:

```
PROXY_HOST=your-proxy-url.pr.thordata.net
PROXY_PORT=9999
PROXY_USER=td-customer-xxxx
PROXY_PASS=xxxxxxxx

SINGLESTORE_URI=mysql+pymysql://user:password@host:3306/price_tracker

OPENAI_API_KEY=sk-xxxx   # optional
```

Make sure .env is not committed to GitHub.

### 🕸️ Running the Scraper
```
python run_scraper.py
```

#### What happens:

- Ensures all SingleStore tables exist

Scrapes:

 - Flight prices

 - OYO hotel prices (sorted low → high for your selected date)

 - Gozo cab prices

Inserts results into:

- flight_prices

- hotel_rates

- rental_car_prices

### 📊 Running the Dashboard
```
streamlit run dashboard_app.py
```

Dashboard includes:

- Lowest Price Snapshot

- Latest scraped data tables

- Price trends

- LLM-powered question answering (optional)

### 🌩️ Why Thordata is Critical

Travel websites use:

- Bot detection

- Rate limiting

- Anti-scraping JavaScript

- IP blocking

Thordata provides:

- Clean residential IP rotation

- Far fewer 403/429 errors

- Smooth rendering of dynamic pages

- Stable scraping sessions

This ensures consistent, production-grade data ingestion, enabling future Agentic AI use cases such as:

- Autonomous travel agents

- Price-monitoring bots

- Automated deal alerts

- Multi-agent itinerary planners

[Sign up to Thordata](https://dashboard.thordata.com/register) and start using their powerful proxies. 
