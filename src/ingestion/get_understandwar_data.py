"""Generate article candidates and incrementally ingest Understanding War articles."""
import calendar
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
import json
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://understandingwar.org/research"
ARTICLE_FAMILIES = (
    "middle-east/iran-update-",
    "russia-ukraine/russian-offensive-campaign-assessment-",
    "russia-ukraine/russian-occupation-update-",
    "china-taiwan/china-taiwan-update-",
    "china-taiwan/korean-peninsula-update-",
)
MONTH_NAMES = ("june", "july", "august", "september", "october", "november")
SCRIPT_DIRECTORY = Path(__file__).resolve().parent
OUTPUT_PATH = SCRIPT_DIRECTORY.parents[1] / "data/outputs/understanding_war_articles/isw_articles.json"
URLS_PATH = SCRIPT_DIRECTORY / "understandwar_articles_to_parse.txt"


def normalize_url(value):
    """Normalize plain or Markdown URLs for stable article deduplication."""
    match = re.fullmatch(r"\[[^\]]+\]\((https?://[^)]+)\)", value.strip())
    parts = urlsplit(match.group(1) if match else value.strip())
    path = re.sub(r"-(0[1-9])-(\d{4})(?=/|$)", lambda m: f"-{int(m[1])}-{m[2]}", parts.path)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path.rstrip("/") + "/", "", ""))


def retrieve_understanding_war_links(year=2026, today=None):
    """Yield valid, nonfuture date candidates for the configured article families."""
    today = today if today is not None else date.today()
    for family in ARTICLE_FAMILIES:
        for month, name in enumerate(MONTH_NAMES, start=6):
            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                if date(year, month, day) <= today:
                    yield f"{BASE_URL}/{family}{name}-{day}-{year}/"


def limit_sources(article):
    """Retain at most three distinct source URLs per article, in original order."""
    return {**article, "sources": list(dict.fromkeys(article.get("sources", [])))[:3]}


def save_articles(output_path, articles, errors):
    """Checkpoint results after each attempt using an atomic file replacement."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"articles": [limit_sources(article) for article in articles.values()],
                                    "errors": list(errors.values())},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(output_path)


def retry_after_seconds(value):
    """Read Retry-After as seconds or an HTTP date; return zero if invalid."""
    if not value:
        return 0
    try:
        return max(0, int(value))
    except (ValueError, TypeError):
        try:
            timestamp = parsedate_to_datetime(value)
            return max(0, (timestamp - datetime.now(timezone.utc)).total_seconds())
        except (ValueError, TypeError, OverflowError):
            return 0


class RateLimitExceeded(requests.RequestException):
    """Signal that collection must stop after repeated rate limiting."""


def ingest_articles(urls=None, output_path=OUTPUT_PATH, session=None,
                    request_interval=5, max_retries=3, sleep=time.sleep):
    """Fetch unrecorded candidates; retain successful articles and retry prior errors."""
    if request_interval < 0 or max_retries < 0:
        raise ValueError("Request interval and retry count must be nonnegative.")
    output_path = Path(output_path)
    # Invalid existing JSON must fail rather than overwrite previously collected data.
    stored = json.loads(output_path.read_text(encoding="utf-8")) if output_path.exists() else {"articles": [], "errors": []}
    articles = {normalize_url(item["url"]): limit_sources({**item, "url": normalize_url(item["url"])})
                for item in stored["articles"]}
    errors = {normalize_url(item["url"]): {**item, "url": normalize_url(item["url"])}
              for item in stored.get("errors", [])}
    if urls is None:
        urls = list(retrieve_understanding_war_links())
        # Keep manually selected articles, including reports without date-based slugs.
        if URLS_PATH.exists():
            urls.extend(line.strip() for line in URLS_PATH.read_text(encoding="utf-8").splitlines()
                        if line.strip() and not line.lstrip().startswith("#"))
    owns_session = session is None
    session = session if session is not None else requests.Session()
    session.headers.update({"User-Agent": "research-parser/1.0"})
    attempted = set()
    request_sent = False
    try:
        for value in urls:
            url = normalize_url(value)
            if url in articles:
                errors.pop(url, None)
                continue
            if url in attempted:
                continue
            attempted.add(url)
            response_is_rate_limited = False
            try:
                for attempt in range(max_retries + 1):
                    if request_sent:
                        sleep(request_interval)
                    request_sent = True
                    response = session.get(url, timeout=30)
                    if response.status_code != 429:
                        response.raise_for_status()
                        break
                    if attempt == max_retries:
                        raise RateLimitExceeded("Repeated HTTP 429; collection stopped. Retry in a later run.")
                    delay = max(60 * 2 ** attempt,
                                retry_after_seconds(response.headers.get("Retry-After")))
                    response.close()
                    print(f"Rate limited: waiting {delay:.0f}s before retrying {url}")
                    sleep(delay)
                soup = BeautifulSoup(response.text, "html.parser")
                article = soup.select_one("article")
                if article is None:
                    raise ValueError("No article element found")
                title = article.find("h1") or soup.find("h1")
                paragraphs = [p.get_text(" ", strip=True) for p in article.select("p")]
                text = "\n".join(p for p in paragraphs if p)
                if not text:
                    raise ValueError("Article contains no paragraph text")
                articles[url] = {"url": url, "title": title.get_text(" ", strip=True) if title else None,
                                 "text": text,
                                 "sources": list(dict.fromkeys(
                                     urljoin(response.url or url, anchor["href"])
                                     for anchor in article.select("a[href]")
                                     if urlsplit(urljoin(response.url or url, anchor["href"])).scheme in {"http", "https"}
                                 ))[:3]}
                errors.pop(url, None)
                print(f"Processed: {url}")
            except (requests.RequestException, ValueError) as error:
                response_is_rate_limited = isinstance(error, RateLimitExceeded)
                errors[url] = {"url": url, "error": str(error)}
                print(f"Failed: {url} — {error}")
            save_articles(output_path, articles, errors)
            if response_is_rate_limited:
                break
        save_articles(output_path, articles, errors)
    finally:
        if owns_session:
            session.close()
    return {"articles": [limit_sources(article) for article in articles.values()], "errors": list(errors.values())}


if __name__ == "__main__":
    payload = ingest_articles()
    print(f"Total saved articles: {len(payload['articles'])}")
    print(f"Remaining errors: {len(payload['errors'])}")
    print(f"Results saved to: {OUTPUT_PATH}")
