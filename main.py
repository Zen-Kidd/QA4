#!/usr/bin/env python3
import os
import sys
import asyncio
import time
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import requests
import feedparser
import openai

# Load environment variables from .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# API keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not NEWS_API_KEY:
    raise EnvironmentError("Please set NEWS_API_KEY in your .env file")
if not OPENAI_API_KEY:
    raise EnvironmentError("Please set OPENAI_API_KEY in your .env file")
openai.api_key = OPENAI_API_KEY

# Endpoints & defaults
NEWSAPI_URL     = "https://newsapi.org/v2/everything"
GOOGLE_RSS_BASE = "https://news.google.com/rss/search"
DEFAULT_COUNT   = 5

def fetch_newsapi(topic: str, max_items: int = DEFAULT_COUNT) -> list:
    """Fetch recent articles from NewsAPI."""
    params = {
        "q": topic,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": max_items,
        "sortBy": "publishedAt"
    }
    resp = requests.get(NEWSAPI_URL, params=params, timeout=10)
    resp.raise_for_status()
    out = []
    for art in resp.json().get("articles", []):
        out.append({
            "title":       art.get("title"),
            "link":        art.get("url"),
            "source":      art.get("source", {}).get("name", "NewsAPI"),
            "publishedAt": art.get("publishedAt", ""),
            "summary":     art.get("description", "")
        })
    return out

async def fetch_google_rss(topic: str, max_items: int = DEFAULT_COUNT) -> list:
    """Fetch recent items from Google News RSS."""
    query = requests.utils.quote(topic)
    url   = f"{GOOGLE_RSS_BASE}?q={query}&hl=en-US&gl=US&ceid=US:en"
    feed  = feedparser.parse(url)
    out   = []
    for entry in feed.entries[:max_items]:
        pp = entry.get("published_parsed")
        if pp:
            ts = time.mktime(pp)
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            published = dt.isoformat()
        else:
            published = ""
        out.append({
            "title":       entry.get("title", ""),
            "link":        entry.get("link", ""),
            "source":      "Google News RSS",
            "publishedAt": published,
            "summary":     entry.get("summary", "")
        })
    return out

def summarize_if_relevant(topic: str, article: dict) -> str | None:
    """Use OpenAI to summarize only if article is relevant."""
    prompt = f"""Topic: {topic}
Title: {article['title']}
Summary: {article.get('summary','')}

If this article is relevant to the topic, provide a concise email-friendly summary in 2–3 sentences.
If not relevant, respond with 'NOT RELEVANT'."""
    resp = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=150,
    )
    text = resp.choices[0].message.content.strip()
    if text.upper().startswith("NOT RELEVANT"):
        return None
    return text

def sort_by_date(articles: list) -> list:
    """Sort articles by their publishedAt timestamp (newest first)."""
    def parse_date(a):
        s = a.get("publishedAt", "")
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        except:
            return datetime.min
    return sorted(articles, key=parse_date, reverse=True)

def main():
    topic = input("Enter a topic keyword: ").strip()
    if not topic:
        sys.exit("No topic provided.")

    # Fetch
    api_articles = fetch_newsapi(topic)
    rss_articles = asyncio.run(fetch_google_rss(topic))
    combined = sort_by_date(api_articles + rss_articles)

    # Print articles
    print(f"Fetched {len(combined)} articles for topic '{topic}':\n")
    for i, art in enumerate(combined, 1):
        print(f"{i}. [{art['source']}] {art['title']}")
        print(f"   Link: {art['link']}")
        if art.get("publishedAt"):
            print(f"   Published: {art['publishedAt']}")
        print()

    # Print summaries
    print("Summaries of relevant articles:\n")
    for art in combined:
        summary = summarize_if_relevant(topic, art)
        if summary:
            print(f"- {art['title']}: {summary}\n")

if __name__ == "__main__":
    main()
