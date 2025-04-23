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

# Default RSS feeds from multiple domains
DEFAULT_RSS_FEEDS = [
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml"
    "http://www.espn.com/espn/rss/nfl/news",
    "https://www.espn.com/espn/rss/nfl/headlines",
    "https://www.billboard.com/feed",
    "http://rss.cnn.com/rss/cnn_topstories.rss",
    "http://feeds.nytimes.com/nyt/rss/HomePage",
    "http://www.washingtonpost.com/rss/",
    "http://rssfeeds.usatoday.com/usatoday-NewsTopStories",
    "http://www.npr.org/rss/rss.php?id=1001",
    "http://newsrss.bbc.co.uk/rss/newsonline_world_edition/americas/rss.xml",
    "http://www.npr.org/rss/rss.php?id=1013",
    "http://www.smartbrief.com/servlet/rss?b=ASCD",
    "http://feeds.nature.com/nature/rss/current",
    "http://feeds.sciencedaily.com/sciencedaily",
    "http://feeds.wired.com/wired/index",
    "http://www.npr.org/rss/rss.php?id=1019",
    "http://feeds.pcworld.com/pcworld/latestnews",
    "http://feeds1.nytimes.com/nyt/rss/Sports",
    "http://www.nba.com/jazz/rss.xml",
    "http://www.espn.in/football",
    "https://www.espn.com/nfl",
    "https://www.espn.com/espn/rss/nba/news",
    "https://www.espn.com/espn/rss/espnu/news",
]


def expand_topic(topic: str, max_terms: int = 5) -> list:
    """
    Uses OpenAI to generate related keywords for broader search.
    Returns a list of related terms.
    """
    prompt = (
        f"Generate {max_terms} synonyms or related terms for the topic '{topic}'. "
        "Return them as a comma-separated list with no extra text."
    )
    # Updated OpenAI API call
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=60
    )
    text = response.choices[0].message.content
    terms = [t.strip() for t in text.split(',') if t.strip()]
    return terms


def fetch_api_articles(query: str, page_size: int = 5) -> list:
    """
    Fetches articles from NewsAPI.org using a query string.
    """
    params = {
        "apiKey": NEWS_API_KEY,
        "q": query,
        "pageSize": page_size,
        "language": "en"
    }
    resp = requests.get(NEWS_API_ENDPOINT, params=params)
    resp.raise_for_status()
    return [
        {"title": art.get("title"), "link": art.get("url"), "source": "NewsAPI"}
        for art in resp.json().get("articles", [])
    ]


def fetch_rss_articles(feed_urls: list, filter_terms: list, max_items: int = 5) -> list:
    """
    Fetches and filters RSS feed entries by related terms.
    """
    filtered = []
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries[:max_items]:
            text_content = f"{entry.title} {getattr(entry, 'summary', '')}".lower()
            if any(term.lower() in text_content for term in filter_terms):
                filtered.append({"title": entry.title, "link": entry.link, "source": url})
    return filtered


def main():
    # Prompt user for topic and counts
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

    # Expand topic for broader coverage
    related_terms = expand_topic(topic)
    terms = [topic] + related_terms
    print(f"\nSearching for articles with terms: {', '.join(terms)}\n")

    # Build query string for NewsAPI
    query_str = " OR ".join(terms)
    api_articles = fetch_api_articles(query_str, page_size=api_count)

    # Fetch and filter RSS feeds
    rss_articles = fetch_rss_articles(DEFAULT_RSS_FEEDS, terms, max_items=rss_count)

    articles = api_articles + rss_articles
    if not articles:
        print(f"No articles found for '{topic}'.", file=sys.stderr)
        sys.exit(1)

    # Display results
    print(f"\nFetched {len(articles)} articles for topic '{topic}':\n")
    for idx, art in enumerate(articles, 1):
        print(f"{idx}. [{art['source']}] {art['title']}")
        print(f"   Link: {art['link']}\n")


if __name__ == "__main__":
    main()
