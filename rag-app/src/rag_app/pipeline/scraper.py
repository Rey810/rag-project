"""
AllanClear — Article Scraper
Scrapes investment insight articles from allangray.co.za

Usage:
    python scraper.py

Output:
    Creates a /data directory with one JSON file per article.
    Each JSON file contains: title, author, date, category, url, body
"""

import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from xml.etree import ElementTree

BASE_URL = "https://www.allangray.co.za"
SITEMAP_URL = f"{BASE_URL}/sitemap.xml"
OUTPUT_DIR = "data/articles"
DELAY_BETWEEN_REQUESTS = 2  # seconds — be respectful
HEADERS = {"User-Agent": "AllanClear-Scraper/1.0 (student project)"}

# Categories to skip (not text articles)
SKIP_PATTERNS = [
    "/quarterly-commentary/",  # these are PDF-based, not HTML articles
    "/event-hub",
]

# Only scrape articles under /latest-insights/
REQUIRED_PREFIX = "/latest-insights/"


def fetch_article_urls_from_sitemap():
    """Parse the sitemap XML and return article URLs under /latest-insights/, sorted by lastmod."""
    print("Fetching sitemap...")
    response = requests.get(SITEMAP_URL, headers=HEADERS)
    response.raise_for_status()

    root = ElementTree.fromstring(response.content)
    namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    articles = []
    for url_element in root.findall("ns:url", namespace):
        loc = url_element.find("ns:loc", namespace).text
        lastmod_el = url_element.find("ns:lastmod", namespace)
        lastmod = lastmod_el.text if lastmod_el else "1970-01-01"

        path = loc.replace(BASE_URL, "")

        if not path.startswith(REQUIRED_PREFIX):
            continue
        if any(skip in path for skip in SKIP_PATTERNS):
            continue

        articles.append((loc, lastmod))

    # Sort by lastmod descending (most recent first)
    articles.sort(key=lambda x: x[1], reverse=True)
    urls = [url for url, _ in articles]

    print(f"Found {len(urls)} article URLs in sitemap (sorted by most recent)")
    return urls


def scrape_article(url):
    """Fetch a single article page and extract its content."""
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # -- Check content type: only scrape Articles --
    sub_heading = soup.find("div", class_="sub-heading")
    if not sub_heading or sub_heading.get_text(strip=True).lower() != "article":
        return None

    # -- Title: first h1 on the page --
    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else None

    # -- Author --
    author = None
    author_link = soup.find("a", href=lambda h: h and "/authors-listing/" in h)
    if author_link:
        author = author_link.get_text(strip=True)

    # -- Date: extract from the timestamp div --
    date = None
    timestamp_div = soup.find("div", class_="timestamp")
    if timestamp_div:
        date = timestamp_div.get_text(strip=True).lstrip("- ").strip()

    # -- Category: extract from URL path --
    # e.g. /latest-insights/personal-investing/article-slug/ → "personal-investing"
    path = url.replace(BASE_URL, "")
    path_parts = [p for p in path.strip("/").split("/") if p]
    category = path_parts[1] if len(path_parts) > 1 else None

    # -- Body text: scoped to <article>, stops at <aside> --
    article_tag = soup.find("article")
    if not article_tag:
        return None

    content_tags = article_tag.find_all(["p", "h2", "h3", "h4", "blockquote", "li", "aside"])

    body_parts = []
    for tag in content_tags:
        if tag.name == "aside":
            break

        text = tag.get_text(strip=True)
        if not text:
            continue

        if tag.name in ["h2", "h3", "h4"]:
            body_parts.append(f"\n## {text}\n")
        elif tag.name == "blockquote":
            body_parts.append(f"> {text}")
        else:
            body_parts.append(text)

    body = "\n\n".join(body_parts)

    return {
        "title": title,
        "author": author,
        "date": date,
        "category": category,
        "url": url,
        "body": body,
    }


def save_article(article, index):
    """Save an article dict as a JSON file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Create a filename from the URL slug
    slug = article["url"].rstrip("/").split("/")[-1]
    filename = f"{index:03d}_{slug}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(article, f, indent=2, ensure_ascii=False)

    return filepath


def main():
    urls = fetch_article_urls_from_sitemap()

    MAX_ARTICLES = None  # Stop after scraping this many articles, None for all

    print(f"\nScraping articles (target: {MAX_ARTICLES or 'all'})...\n")

    scraped = 0
    failed = 0
    skipped = 0

    for i, url in enumerate(urls):
        if MAX_ARTICLES and scraped >= MAX_ARTICLES:
            break

        try:
            print(f"[{i+1}] Scraping: {url}")
            article = scrape_article(url)

            if article is None:
                print(f"  ⚠ Skipped (not an Article — likely Video or Podcast)")
                skipped += 1
                continue

            if not article["body"] or len(article["body"]) < 200:
                print(f"  ⚠ Skipped (no/short body text)")
                skipped += 1
                continue

            filepath = save_article(article, scraped)
            print(f"  ✓ Saved: {filepath} ({len(article['body'])} chars)")
            scraped += 1

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed += 1

        # Rate limiting
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n--- Done ---")
    print(f"Scraped: {scraped}")
    print(f"Skipped: {skipped}")
    print(f"Failed:  {failed}")
    print(f"Output:  {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()