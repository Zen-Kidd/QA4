#!/usr/bin/env python3
import os
import sys
import asyncio
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

# Expanded list of reliable RSS feeds
RSS_FEEDS = [
    # General News
    "http://rss.cnn.com/rss/cnn_topstories.rss",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
    "https://www.npr.org/rss/rss.php?id=1001",
    "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
    # Technology
    "https://www.wired.com/feed/rss",
    "https://techcrunch.com/feed/",
    "https://feeds.arstechnica.com/arstechnica/index",
    "https://www.theverge.com/rss/index.xml",
    # Business & Finance
    "https://www.bloomberg.com/feed/podcast/etf-report.xml",
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    # Politics
    "https://www.politico.com/rss/politics08.xml",
    "https://feeds.npr.org/1014/rss.xml",
    # Science & Health
    "http://feeds.nature.com/nature/rss/current",
    "https://www.sciencedaily.com/rss/all.xml",
    # Entertainment
    "https://variety.com/feed/",
    "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
]

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

async def filter_rss_entries(feed_url, feed, topic, max_items):
    matched = []
    t = topic.lower()
    for entry in feed.entries:
        if len(matched) >= max_items:
            break
        text = " ".join([entry.get('title',''), entry.get('summary','')]).lower()
        if t in text:
            matched.append({
                "title": entry.get('title',''),
                "link": entry.get('link',''),
                "source": feed_url,
                "publishedAt": entry.get('published','')
            })
    return matched

async def fetch_rss(topic: str, max_items: int):
    feeds = await fetch_all_feeds(RSS_FEEDS)
    results = []
    for url, feed in feeds:
        results.extend(await filter_rss_entries(url, feed, topic, max_items))
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
    items = resp.json().get("articles", [])
    results = []
    for art in items:
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
