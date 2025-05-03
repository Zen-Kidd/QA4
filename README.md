# AI-Powered News Newsletter Generator

A Python-based tool that fetches the latest news on any topic, generates concise summaries using OpenAI, and emails a polished digest—all fully automated.

## Features
- **Search & Fetch**: Retrieves articles from:
  - NewsAPI’s **Everything** endpoint for broad coverage.
  - Google News RSS search for real-time, popular results.
- **Summarization**: Uses OpenAI’s GPT-3.5-turbo to filter relevance and produce 2–3 sentence summaries.
- **Email Delivery**: Sends a clean, spaced HTML/plain-text email via SMTP, with:
  - A bold header and summary list.
  - A separate section of clickable links.

## Requirements
- Python 3.8+
- An OpenAI API key (`OPENAI_API_KEY`)
- A NewsAPI key (`NEWS_API_KEY`)
- SMTP credentials (e.g., Gmail App Password)
  - Host (`SMTP_HOST`)
  - Port (`SMTP_PORT`, usually 587)
  - Username (`EMAIL_ADDRESS`)
  - Password (`EMAIL_PASSWORD`)
  - Recipient address (`RECIPIENT_EMAIL`)

## Installation
1. Clone this repository:
   ```bash
   git clone <repo-url>
   cd <repo-directory>
   ```
2. Create and activate a virtual environment (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # on macOS/Linux
   venv\Scripts\activate    # on Windows
   ```
3. Install dependencies:
   ```bash
   pip install --upgrade openai python-dotenv requests feedparser
   ```

## Configuration
1. Create a file named `.env` in the project root.
2. Add the following variables:
   ```dotenv
   NEWS_API_KEY=your_newsapi_key
   OPENAI_API_KEY=your_openai_key

   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   EMAIL_ADDRESS=your.address@example.com
   EMAIL_PASSWORD=your_app_password
   RECIPIENT_EMAIL=recipient@example.com
   ```
3. If using Gmail, generate an **App Password** (see Google Account → Security → App passwords).

## Usage
Run the script and enter a topic when prompted:
```bash
python main.py
```
It will:
1. Fetch up to 5 articles from NewsAPI and Google News RSS.
2. Display the headlines, sources, links, and publish dates in the console.
3. Generate and display summaries for relevant articles.
4. Send an HTML/plain-text email digest to `RECIPIENT_EMAIL`.

## How It Works

### 1. Fetching Articles
- **NewsAPI** (`fetch_newsapi`) calls the `everything` endpoint with your topic, sorted by date.
- **Google News RSS** (`fetch_google_rss`) parses the RSS search feed for near-instant, popular results.

### 2. Summarization & Relevance
- **OpenAI** (`summarize_if_relevant`) receives the topic, title, and snippet.
- The model returns either “NOT RELEVANT” or a short, email-friendly summary (2–3 sentences).

### 3. Email Composition
- **HTML version**: A bold `<h1>` header, spaced `<li>` summaries, and a separate “Links” section.
- **Plain-text fallback**: Summaries and links spaced by blank lines.
- Sent via `smtplib` with TLS.

## Troubleshooting
- **Authentication errors**: Ensure `.env` variables are correct and valid (especially App Passwords).
- **Rate limits**: NewsAPI and OpenAI have daily or per-minute caps.
- **Network issues**: Check connectivity and RSS feed availability.

## Customization
- Adjust `DEFAULT_COUNT` to fetch more/fewer articles.
- Modify HTML/CSS in `send_email` for your own styling.
- Integrate with other email providers by changing SMTP settings.

---

**Enjoy staying on top of any topic — fully automated!**
