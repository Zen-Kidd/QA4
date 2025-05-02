#!/usr/bin/env python3
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests
import feedparser
import openai

# Load environment variables from .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Retrieve API keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not NEWS_API_KEY:
    raise EnvironmentError("Please set NEWS_API_KEY in your .env file")
if not OPENAI_API_KEY:
    raise EnvironmentError("Please set OPENAI_API_KEY in your .env file")
openai.api_key = OPENAI_API_KEY

# NewsAPI endpoint
NEWS_API_ENDPOINT = "https://newsapi.org/v2/top-headlines"

# Verified, active RSS feeds (broad coverage)
DEFAULT_RSS_FEEDS = [
    # General News
    "http://rss.cnn.com/rss/cnn_topstories.rss",
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "http://feeds.reuters.com/reuters/topNews",
    "http://www.npr.org/rss/rss.php?id=1001",
    # Sports
    "https://www.espn.com/espn/rss/news",
    "https://feeds.bbci.co.uk/sport/rss.xml",
    # Technology
    "https://www.wired.com/feed/rss",
    "https://techcrunch.com/feed/",
    "https://www.cnet.com/rss/news/",
    # Science
    "http://feeds.sciencedaily.com/sciencedaily",
    "https://www.nasa.gov/news-release/feed/",
    # Business
    "http://feeds.reuters.com/reuters/businessNews",
    "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    # Entertainment & Culture
    "https://variety.com/feed/",
    "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    # Health & Medicine
    "https://www.medicinenet.com/rss/dailyhealth.xml",
    "https://feeds.bbci.co.uk/news/health/rss.xml",
]


def expand_topic(topic: str, max_terms: int = 5) -> list:
    """
    Uses OpenAI to generate related keywords for broader NewsAPI queries.
    Returns a list of related terms including the original topic.
    """
    prompt = (
        f"Generate {max_terms} synonyms or related terms for the topic '{topic}', in plain comma-separated format."
    )
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=60
    )
    terms = [t.strip() for t in response.choices[0].message.content.split(",") if t.strip()]
    return [topic] + terms


def is_relevant(text: str, topic: str) -> bool:
    """
    Uses the LLM to semantically check if the text is directly about the topic.
    Returns True if the model answers 'yes'.
    """
    prompt = (
        f"Is the following article text directly about '{topic}'? "
        "Answer yes or no, without explanation.\n\n" + text
    )
    try:
        resp = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=5
        )
        return resp.choices[0].message.content.strip().lower().startswith("yes")
    except Exception:
        return False


def fetch_api_articles(query: str, page_size: int = 5) -> list:
    """
    Fetches relevant articles from NewsAPI.org using a query string.
    Returns a list of dicts with 'title', 'link', and 'source'.
    """
    params = {"apiKey": NEWS_API_KEY, "q": query, "pageSize": page_size, "language": "en"}
    resp = requests.get(NEWS_API_ENDPOINT, params=params)
    resp.raise_for_status()
    return [
        {"title": art.get("title"), "link": art.get("url"), "source": "NewsAPI"}
        for art in resp.json().get("articles", [])
    ]


def fetch_rss_articles(feed_urls: list, topic: str, max_items: int = 5) -> list:
    """
    Fetches top entries from RSS feeds, filtering by direct relevance via substring or LLM.
    """
    results = []
    for url in feed_urls:
        count = 0
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            print(f"Warning: could not retrieve feed {url}: {e}", file=sys.stderr)
            continue

        for entry in feed.entries:
            if count >= max_items:
                break

            # Combine text fields
            text_content = " ".join([
                entry.get('title', ''),
                entry.get('summary', ''),
                entry.get('description', ''),
                *[c.get('value', '') for c in entry.get('content', [])]
            ])

            # Check substring first
            if topic.lower() in text_content.lower():
                results.append({"title": entry.get('title', ''), "link": entry.get('link', ''), "source": url})
                count += 1
                continue

            # Semantic relevance fallback
            if is_relevant(text_content, topic):
                results.append({"title": entry.get('title', ''), "link": entry.get('link', ''), "source": url})
                count += 1

    return results


def main():
    topic = input("Enter a topic keyword: ").strip()
    if not topic:
        print("No topic provided. Exiting.", file=sys.stderr)
        sys.exit(1)

    try:
        api_count = int(input("Number of NewsAPI articles to fetch (default 5): ") or 5)
    except ValueError:
        api_count = 5

    try:
        rss_count = int(input("RSS items per feed to fetch (default 5): ") or 5)
    except ValueError:
        rss_count = 5

    # Expand topic for NewsAPI queries
    terms = expand_topic(topic)
    print(f"\nSearching NewsAPI for: {', '.join(terms)}")
    query_str = " OR ".join(terms)
    api_articles = fetch_api_articles(query_str, page_size=api_count)

    # Fetch and filter RSS articles by direct topic relevance
    print(f"\nFiltering RSS feeds for topic: {topic}\n")
    rss_articles = fetch_rss_articles(DEFAULT_RSS_FEEDS, topic, max_items=rss_count)

    # Combine and display
    articles = api_articles + rss_articles
    if not articles:
        print(f"No articles found for '{topic}'.", file=sys.stderr)
        sys.exit(1)

    print(f"\nFetched {len(articles)} articles for topic '{topic}':\n")
    for idx, art in enumerate(articles, 1):
        print(f"{idx}. [{art['source']}] {art['title']}")
        print(f"   Link: {art['link']}\n")


if __name__ == "__main__":
    main()
