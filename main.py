#!/usr/bin/env python3
import os
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests
import aiohttp
import feedparser

# Load environment variables from .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
if not NEWS_API_KEY:
    raise EnvironmentError("Please set NEWS_API_KEY in your .env file")

# Reliable NewsAPI sources
NEWSAPI_SOURCES = [
    "bbc-news", "cnn", "the-verge", "techcrunch", "engadget",
    "ars-technica", "reuters", "associated-press", "the-washington-post"
]

# Path to external RSS feed definitions
FEEDS_FILE = Path(__file__).parent / "rss_feeds.json"

async def fetch_feed(session: aiohttp.ClientSession, url: str):
    try:
        async with session.get(url, timeout=10) as resp:
            resp.raise_for_status()
            data = await resp.read()
            feed = feedparser.parse(data)
            return url, feed
    except Exception as e:
        print(f"Warning: could not fetch RSS feed {url}: {e}", file=sys.stderr)
        return url, None

async def fetch_all_feeds(urls):
    results = []
    headers = {"User-Agent": "NewsFetcher/1.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [fetch_feed(session, url) for url in urls]
        for coro in asyncio.as_completed(tasks):
            url, feed = await coro
            if feed:
                results.append((url, feed))
    return results

async def fetch_rss(topic: str, max_items: int):
    # Load feed definitions with tags
    try:
        feeds_data = json.loads(FEEDS_FILE.read_text())
    except Exception as e:
        print(f"Error loading feeds file: {e}", file=sys.stderr)
        sys.exit(1)

    # Select feeds tagged for this topic or fall back to all
    topic_lower = topic.lower()
    selected_urls = [f['url'] for f in feeds_data if topic_lower in [t.lower() for t in f.get('tags', [])]]
    if not selected_urls:
        selected_urls = [f['url'] for f in feeds_data]

    feeds = await fetch_all_feeds(selected_urls)
    results = []
    for url, feed in feeds:
        count = 0
        for entry in feed.entries:
            if count >= max_items:
                break
            text = " ".join([entry.get('title',''), entry.get('summary','')]).lower()
            if topic_lower in text:
                results.append({
                    "title": entry.get('title',''),
                    "link": entry.get('link',''),
                    "source": url,
                    "publishedAt": entry.get('published','')
                })
                count += 1
    return results

def fetch_newsapi(topic: str, max_items: int):
    params = {
        "q": topic,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": max_items,
        "sources": ",".join(NEWSAPI_SOURCES)
    }
    resp = requests.get("https://newsapi.org/v2/everything", params=params)
    resp.raise_for_status()
    results = []
    for art in resp.json().get("articles", []):
        results.append({
            "title": art.get("title"),
            "link": art.get("url"),
            "source": art.get("source", {}).get("name","NewsAPI"),
            "publishedAt": art.get("publishedAt","")
        })
    return results

def sort_articles(articles):
    def parse_date(a):
        date_str = a.get("publishedAt") or a.get("published")
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace('Z','+00:00'))
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                pass
        return datetime.min
    return sorted(articles, key=parse_date, reverse=True)

def main():
    topic = input("Enter a topic keyword: ").strip()
    if not topic:
        print("No topic provided. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Fixed defaults
    api_count = 5
    rss_count = 5

    api_articles = fetch_newsapi(topic, api_count)
    rss_articles = asyncio.run(fetch_rss(topic, rss_count))

    combined = sort_articles(api_articles + rss_articles)
    if not combined:
        print(f"No articles found for '{topic}'.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetched {len(combined)} articles for topic '{topic}':\n")
    for idx, art in enumerate(combined, 1):
        print(f"{idx}. [{art['source']}] {art['title']}")
        print(f"   Link: {art['link']}")
        if art.get('publishedAt'):
            print(f"   Published: {art['publishedAt']}")
        print()

if __name__ == "__main__":
    main()
