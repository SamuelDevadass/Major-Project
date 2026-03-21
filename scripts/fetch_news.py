# scripts/fetch_news.py
# Run ONCE before the first demo.
# Scrapes ESG-related news articles for each company from:
#   - ESG Today (esgtoday.com)
#   - Yahoo Finance News
#   - Reuters Sustainability
# Saves one JSON file per company to data/news/news_{ticker}.json
#
# Usage:
#   cd PROJECT/
#   python scripts/fetch_news.py
#
#   # Fetch only specific tickers (faster for demo prep):
#   python scripts/fetch_news.py --tickers AAPL MSFT TSLA AMZN GOOGL
#
# Output: data/news/news_{ticker}.json per company

import argparse
import json
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── PATHS ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
DATA_DIR   = BASE_DIR / "data"
KAGGLE_CSV = DATA_DIR / "kaggle_snapshot.csv"
NEWS_DIR   = DATA_DIR / "news"

# ── CONFIG ────────────────────────────────────────────────────────────────────
DELAY_SECONDS   = 2.0   # delay between requests per ticker
MAX_ARTICLES    = 10    # max articles per source per ticker
REQUEST_TIMEOUT = 15    # seconds

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ── SCRAPERS ──────────────────────────────────────────────────────────────────

def scrape_yahoo_finance(ticker: str, company_name: str) -> list[dict]:
    """Scrape Yahoo Finance news for a ticker."""
    articles = []
    url = f"https://finance.yahoo.com/quote/{ticker}/news/"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return articles

        soup = BeautifulSoup(resp.text, "html.parser")

        # Yahoo Finance news items
        items = soup.select("li.js-stream-content, div[data-testid='storyitem']")
        if not items:
            items = soup.select("div.Ov\\(h\\)")

        for item in items[:MAX_ARTICLES]:
            try:
                title_el = item.select_one("h3, h4, a[data-ylk]")
                link_el  = item.select_one("a[href]")
                date_el  = item.select_one("time, span[data-timestamp]")

                title = title_el.get_text(strip=True) if title_el else ""
                link  = link_el.get("href", "") if link_el else ""
                if link and link.startswith("/"):
                    link = "https://finance.yahoo.com" + link

                date_str = ""
                if date_el:
                    date_str = date_el.get("datetime") or date_el.get("data-timestamp") or date_el.get_text(strip=True)

                # Fetch article content
                content = _fetch_article_content(link) if link.startswith("http") else ""

                if title and (content or link):
                    articles.append({
                        "title":   title,
                        "source":  "Yahoo Finance",
                        "date":    _normalise_date(date_str),
                        "url":     link,
                        "content": content or title,
                    })
            except Exception:
                continue

    except Exception:
        pass

    return articles


def scrape_esg_today(ticker: str, company_name: str) -> list[dict]:
    """Scrape ESG Today for company-related articles."""
    articles = []
    # Search ESG Today for company name
    search_name = company_name.split()[0] if company_name else ticker
    url = f"https://www.esgtoday.com/?s={requests.utils.quote(search_name)}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return articles

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("article.post, div.post-item, h2.entry-title")

        for item in items[:MAX_ARTICLES]:
            try:
                title_el = item.select_one("h2.entry-title a, h3.entry-title a, a")
                date_el  = item.select_one("time.entry-date, span.posted-on time")

                title = title_el.get_text(strip=True) if title_el else ""
                link  = title_el.get("href", "") if title_el else ""
                date_str = date_el.get("datetime", "") if date_el else ""

                # Only include if article mentions company name or ticker
                if not title:
                    continue
                title_lower = title.lower()
                if company_name.split()[0].lower() not in title_lower and ticker.lower() not in title_lower:
                    continue

                content = _fetch_article_content(link) if link.startswith("http") else ""

                articles.append({
                    "title":   title,
                    "source":  "ESG Today",
                    "date":    _normalise_date(date_str),
                    "url":     link,
                    "content": content or title,
                })
            except Exception:
                continue

    except Exception:
        pass

    return articles


def scrape_reuters(ticker: str, company_name: str) -> list[dict]:
    """Scrape Reuters for ESG-related company news."""
    articles = []
    search_name = company_name.split()[0] if company_name else ticker
    url = f"https://www.reuters.com/search/news?blob={requests.utils.quote(search_name + ' ESG sustainability')}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return articles

        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select("div.search-result-content, article.story")

        for item in items[:MAX_ARTICLES]:
            try:
                title_el = item.select_one("h3.story-title a, h4 a, a.story-link")
                date_el  = item.select_one("time, span.timestamp")

                title = title_el.get_text(strip=True) if title_el else ""
                link  = title_el.get("href", "") if title_el else ""
                if link and link.startswith("/"):
                    link = "https://www.reuters.com" + link

                date_str = date_el.get("datetime", "") if date_el else ""

                if not title:
                    continue

                content = _fetch_article_content(link) if link.startswith("http") else ""

                articles.append({
                    "title":   title,
                    "source":  "Reuters",
                    "date":    _normalise_date(date_str),
                    "url":     link,
                    "content": content or title,
                })
            except Exception:
                continue

    except Exception:
        pass

    return articles


def _fetch_article_content(url: str) -> str:
    """Fetch and extract main text content from an article URL."""
    if not url or not url.startswith("http"):
        return ""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            return ""
        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove nav, footer, ads
        for tag in soup(["nav", "footer", "script", "style", "aside", "header"]):
            tag.decompose()

        # Try common article body selectors
        for selector in ["article", "div.article-body", "div.story-body",
                         "div.entry-content", "div.post-content", "main"]:
            el = soup.select_one(selector)
            if el:
                text = el.get_text(separator=" ", strip=True)
                if len(text) > 100:
                    return text[:3000]  # cap at 3000 chars

        return soup.get_text(separator=" ", strip=True)[:2000]
    except Exception:
        return ""


def _normalise_date(date_str: str) -> str:
    """Try to return an ISO 8601 date string, fallback to today."""
    if not date_str:
        return datetime.now(timezone.utc).date().isoformat()
    try:
        from dateutil import parser as dateparser
        dt = dateparser.parse(date_str)
        return dt.date().isoformat() if dt else datetime.now(timezone.utc).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


# ── MAIN ──────────────────────────────────────────────────────────────────────

def fetch_company_news(ticker: str, company_name: str) -> dict:
    """Fetch news from all three sources for one company."""
    print(f"  Yahoo Finance ...", end=" ", flush=True)
    yahoo = scrape_yahoo_finance(ticker, company_name)
    print(f"{len(yahoo)} articles", end=" | ", flush=True)
    time.sleep(DELAY_SECONDS)

    print(f"ESG Today ...", end=" ", flush=True)
    esg_today = scrape_esg_today(ticker, company_name)
    print(f"{len(esg_today)} articles", end=" | ", flush=True)
    time.sleep(DELAY_SECONDS)

    print(f"Reuters ...", end=" ", flush=True)
    reuters = scrape_reuters(ticker, company_name)
    print(f"{len(reuters)} articles")
    time.sleep(DELAY_SECONDS)

    all_articles = yahoo + esg_today + reuters

    return {
        "ticker":       ticker,
        "company_name": company_name,
        "fetch_date":   datetime.now(timezone.utc).isoformat(),
        "source_sites": ["finance.yahoo.com", "esgtoday.com", "reuters.com"],
        "articles":     all_articles,
    }


def main():
    parser = argparse.ArgumentParser(description="Pre-fetch ESG news per company.")
    parser.add_argument("--tickers", nargs="*", help="Specific tickers to fetch (default: all from Kaggle CSV)")
    args = parser.parse_args()

    # Load Kaggle CSV for company names
    if not KAGGLE_CSV.exists():
        print(f"ERROR: {KAGGLE_CSV} not found.")
        sys.exit(1)

    import pandas as pd
    kaggle_df = pd.read_csv(KAGGLE_CSV)
    kaggle_df["ticker"] = kaggle_df["ticker"].str.upper().str.strip()

    if args.tickers:
        tickers_to_fetch = [t.upper() for t in args.tickers]
    else:
        tickers_to_fetch = kaggle_df["ticker"].dropna().unique().tolist()

    NEWS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"News Pre-Fetch Script — {len(tickers_to_fetch)} tickers")
    print("=" * 60)

    success = 0
    skipped = 0

    for i, ticker in enumerate(tickers_to_fetch, 1):
        out_path = NEWS_DIR / f"news_{ticker}.json"

        # Skip if already fetched
        if out_path.exists():
            print(f"[{i}/{len(tickers_to_fetch)}] {ticker} — already exists, skipping")
            skipped += 1
            continue

        # Get company name from Kaggle CSV
        row = kaggle_df[kaggle_df["ticker"] == ticker]
        company_name = row.iloc[0]["company_name"] if not row.empty else ticker

        print(f"[{i}/{len(tickers_to_fetch)}] {ticker} ({company_name})")
        data = fetch_company_news(ticker, company_name)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        success += 1
        print(f"  → Saved {len(data['articles'])} articles to {out_path.name}")

    print("\n" + "=" * 60)
    print(f"Done. Fetched: {success} | Skipped (existing): {skipped}")
    print(f"News files saved to: {NEWS_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()