# -*- coding: utf-8 -*-
from __future__ import annotations

import time
from typing import List, Optional, Tuple
from urllib.parse import urljoin, urlsplit, urlunsplit, quote

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

BASE_URL = "https://www.econostream-media.com"
START_URL = f"{BASE_URL}/news"

def _encode_url(url: str) -> str:
    """Encode path & query (RFC 3986) pour gérer les ’ etc."""
    parts = urlsplit(url)
    encoded_path = quote(parts.path, safe="/:@&=+$,;~*()-_.")
    encoded_query = quote(parts.query, safe="=&%/:+~*()-_.")
    return urlunsplit((parts.scheme, parts.netloc, encoded_path, encoded_query, parts.fragment))

def _abs_and_encode(href: Optional[str], base: str = BASE_URL) -> Optional[str]:
    if not href:
        return None
    absolute = href if href.startswith("http") else urljoin(base, href)
    return _encode_url(absolute)

def _make_session(timeout: int = 15) -> requests.Session:
    """Session requests avec retries/backoff + UA propre."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "keep-alive",
    })
    retries = Retry(
        total=3,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        respect_retry_after_header=True,
    )
    s.mount("http://", HTTPAdapter(max_retries=retries))
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.request_timeout = timeout  # attribut perso pour porter l'info
    return s

def _fetch_html(session: requests.Session, url: str) -> str:
    r = session.get(url, timeout=getattr(session, "request_timeout", 15))
    r.raise_for_status()
    return r.text

def _parse_article_links_from_html(html: str) -> Tuple[List[str], Optional[str]]:
    """Renvoie (liste_urls_articles, url_next)."""
    soup = BeautifulSoup(html, "html.parser")

    anchors = soup.select(".site-list .article h3 a[href]")
    article_urls: List[str] = []
    for a in anchors:
        url = _abs_and_encode(a.get("href"))
        if url:
            article_urls.append(url)

    next_url = None
    for a in soup.select("nav a.button[href]"):
        text = (a.get_text() or "").strip()
        href = a.get("href") or ""
        if "Next" in text or "offset=" in href:
            maybe = _abs_and_encode(href)
            if maybe and maybe.startswith(f"{BASE_URL}/news"):
                next_url = maybe
                break

    return article_urls, next_url

def extract_all_news_links(
    start_url: str = START_URL,
    max_pages: Optional[int] = 1,
    delay_sec: float = 0.4,
) -> List[str]:
    """
    Scrape la liste News. max_pages=1 => page courante ; None => toutes les pages via 'Next'.
    """
    session = _make_session()
    collected: List[str] = []
    seen = set()

    current = start_url
    page_count = 0

    while True:
        page_count += 1
        html = _fetch_html(session, current)
        links, next_url = _parse_article_links_from_html(html)

        for url in links:
            if url.startswith(f"{BASE_URL}/news/") and url.endswith(".html") and url not in seen:
                seen.add(url)
                collected.append(url)

        if max_pages is not None and page_count >= max_pages:
            break

        if next_url:
            current = next_url
            time.sleep(delay_sec)
        else:
            break

    return collected
