#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests
import feedparser

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
if not NEWS_API_KEY:
    raise EnvironmentError("Please set NEWS_API_KEY in your .env file")

# NewsAPI 'everything' endpoint (no source filter for broad coverage)
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# Google News RSS base URL
GOOGLE_RSS_BASE = "https://news.google.com/rss/search"

# Defaults
DEFAULT_COUNT = 5


def fetch_newsapi(topic: str, max_items: int = DEFAULT_COUNT) -> list:
    """
    Fetches recent articles matching topic via NewsAPI.
    """
    params = {
        "q": topic,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": max_items,
        "sortBy": "publishedAt"
    }
    resp = requests.get(NEWSAPI_URL, params=params, timeout=10)
    resp.raise_for_status()
    results = []
    for art in resp.json().get("articles", []):
        results.append({
            "title": art.get("title"),
            "link": art.get("url"),
            "source": art.get("source", {}).get("name", "NewsAPI"),
            "publishedAt": art.get("publishedAt", "")
        })
    return results


def fetch_google_news_rss(topic: str, max_items: int = DEFAULT_COUNT) -> list:
    """
    Fetches recent items from Google News RSS search.
    """
    query = requests.utils.quote(topic)
    url = f"{GOOGLE_RSS_BASE}?q={query}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(url)
    results = []
    for entry in feed.entries[:max_items]:
        pp = entry.get("published_parsed")
        if pp:
            dt = datetime.fromtimestamp(time.mktime(pp), tz=timezone.utc)
            published = dt.isoformat()
        else:
            published = ""
        results.append({
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "source": "Google News RSS",
            "publishedAt": published
        })
    return results


def sort_articles(articles: list) -> list:
    """
    Sorts articles by publishedAt desc.
    """
    def parse_dt(a):
        s = a.get("publishedAt", "")
        try:
            # ISO8601 parse
            return datetime.fromisoformat(s.replace('Z', '+00:00')).replace(tzinfo=None)
        except Exception:
            return datetime.min
    return sorted(articles, key=parse_dt, reverse=True)


def main():
    topic = input("Enter a topic keyword: ").strip()
    if not topic:
        print("No topic provided. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Fetch from NewsAPI and Google News RSS
    api_articles = fetch_newsapi(topic)
    rss_articles = fetch_google_news_rss(topic)

    combined = sort_articles(api_articles + rss_articles)
    if not combined:
        print(f"No articles found for '{topic}'.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetched {len(combined)} articles for topic '{topic}':\n")
    for i, art in enumerate(combined, 1):
        print(f"{i}. [{art['source']}] {art['title']}")
        print(f"   Link: {art['link']}")
        if art.get('publishedAt'):
            print(f"   Published: {art['publishedAt']}")
        print()

if __name__ == "__main__":
    main()
