# -*- coding: utf-8 -*-
"""
Scraper Econostream (liste + article complet) sans Selenium.
Compatible Render Free (requests + BeautifulSoup uniquement).

Exposé par main.py via FastAPI :
- /scrape        -> liste d'URLs
- /scrape_full   -> URLs + titre, date, auteur, lieu, lede, corps, image, caption
"""
from __future__ import annotations

import re
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlsplit, urlunsplit, quote

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dateutil import parser as dateparser

BASE_URL = "https://www.econostream-media.com"
START_URL = f"{BASE_URL}/news"

# --------------------------- utils généraux --------------------------- #
def _encode_url(url: str) -> str:
    """Encode path & query (RFC 3986) pour gérer les ’ etc."""
    parts = urlsplit(url)
    encoded_path = quote(parts.path, safe="/:@&=+$,;~*()-_.")
    encoded_query = quote(parts.query, safe="=&%/:+~*()-_.")
    return urlunsplit((parts.scheme, parts.netloc, encoded_path, encoded_query, parts.fragment))


def _abs_and_encode(href: Optional[str], base: str = BASE_URL) -> Optional[str]:
    """href -> URL absolue encodée, ou None si invalide."""
    if not href:
        return None
    absolute = href if href.startswith("http") else urljoin(base, href)
    return _encode_url(absolute)


def _clean(s: str) -> str:
    """Nettoyage léger d'espaces et NBSP."""
    if s is None:
        return ""
    s = s.replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\s+\n", "\n", s)
    return s.strip()


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
    s.request_timeout = timeout  # attribut informel pour porter le timeout
    return s


def _fetch_html(session: requests.Session, url: str) -> str:
    r = session.get(url, timeout=getattr(session, "request_timeout", 15))
    r.raise_for_status()
    return r.text


# --------------------------- parsing de la liste --------------------------- #
def _parse_article_links_from_html(html: str) -> Tuple[List[str], Optional[str]]:
    """Renvoie (liste_urls_articles, url_next) depuis la page /news."""
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

    session.close()
    return collected


# --------------------------- parsing d'un article --------------------------- #
_META_DATE_KEYS = [
    ("meta", {"property": "article:published_time"}),
    ("meta", {"name": "article:published_time"}),
    ("meta", {"name": "pubdate"}),
    ("meta", {"name": "date"}),
    ("meta", {"itemprop": "datePublished"}),
]

BODY_SELECTORS = [
    "article .content p",
    "article .entry-content p",
    "article .post-content p",
    "article p",
    ".article p",
    "div[itemprop='articleBody'] p",
]

TITLE_SELECTORS = [
    "article h1", "article h2",
    ".article h1", ".article h2",
    "h1", "h2",
]

_AUTHOR_RE = re.compile(r"^\s*By\s+([^–—\-]+)\s+[–—\-]\s*", re.IGNORECASE)


def _extract_meta_published(soup: BeautifulSoup) -> Optional[str]:
    for tag, attrs in _META_DATE_KEYS:
        node = soup.find(tag, attrs=attrs)
        if node:
            content = node.get("content") or node.get("value")
            if content:
                try:
                    dt = dateparser.parse(content)
                    return dt.isoformat()
                except Exception:
                    return _clean(content)
    return None


def _extract_visible_date(soup: BeautifulSoup) -> Optional[str]:
    """Date dans <article><h3>29 August 2025</h3> → ISO si possible."""
    node = soup.select_one("article h3, .article h3")
    if node:
        txt = _clean(node.get_text())
        if txt:
            try:
                return dateparser.parse(txt).date().isoformat()
            except Exception:
                return txt
    return None


def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    for sel in TITLE_SELECTORS:
        node = soup.select_one(sel)
        if node and _clean(node.get_text()):
            return _clean(node.get_text())

    # Fallbacks via métas et <title>
    meta = soup.find("meta", {"property": "og:title"}) or soup.find("meta", {"name": "twitter:title"})
    if meta and (meta.get("content") or "").strip():
        return _clean(meta["content"])
    if soup.title and soup.title.string:
        return _clean(soup.title.string)
    return None


def _first_meaningful_paragraph(paragraphs: List[str]) -> Optional[str]:
    for p in paragraphs:
        txt = _clean(p)
        if len(txt) >= 20:
            return txt
    return paragraphs[0] if paragraphs else None


def _extract_author_and_location(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Cherche un motif 'By <Author> – CITY (Econostream) –' dans les premières lignes.
    Retourne (author, location) si trouvé.
    """
    head = text[:300]
    author = None
    location = None

    m = _AUTHOR_RE.search(head)
    if m:
        author = _clean(m.group(1))
        loc_m = re.search(r"[–—\-]\s*([A-Za-zÀ-ÖØ-öø-ÿ\.\s]+?)\s*\(Econostream\)\s*[–—\-]", head)
        if loc_m:
            location = _clean(loc_m.group(1))

    return author, location


def parse_article_html(html: str, url: str) -> Dict[str, Optional[str]]:
    """
    Parse une page article et renvoie un dict:
      url, title, published, author, location, lede, text, word_count, image, caption
    """
    soup = BeautifulSoup(html, "html.parser")

    title = _extract_title(soup)
    published_iso = _extract_meta_published(soup) or _extract_visible_date(soup)

    # Collecte des paragraphes
    paragraphs: List[str] = []
    for sel in BODY_SELECTORS:
        parts = [p.get_text(separator=" ", strip=True) for p in soup.select(sel)]
        if parts:
            paragraphs = parts
            break
    if not paragraphs:
        parts = [p.get_text(separator=" ", strip=True) for p in soup.find_all("p")]
        paragraphs = parts

    paragraphs = [_clean(p) for p in paragraphs if _clean(p)]
    lede = _first_meaningful_paragraph(paragraphs)
    body_text = "\n\n".join(paragraphs) if paragraphs else None

    # Auteur / lieu depuis la 1re phrase
    author, location = _extract_author_and_location(
        (lede or "") + " " + (paragraphs[1] if len(paragraphs) > 1 else "")
    )

    # Fallback date visible par regex générale si rien trouvé
    if not published_iso:
        vis_date = None
        m = re.search(r"\b(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b", soup.get_text(" ", strip=True))
        if m:
            vis_date = m.group(1)
            try:
                published_iso = dateparser.parse(vis_date).date().isoformat()
            except Exception:
                published_iso = vis_date

    # Image + légende (si présentes)
    img_node = soup.select_one("figure.article-image img")
    image_url = _abs_and_encode(img_node.get("src")) if img_node and img_node.get("src") else None
    cap_node = soup.select_one("figcaption.article-image-caption")
    caption = _clean(cap_node.get_text()) if cap_node else None

    word_count = len(body_text.split()) if body_text else 0

    return {
        "url": url,
        "title": title,
        "published": published_iso,
        "author": author,
        "location": location,
        "lede": lede,
        "text": body_text,
        "word_count": word_count,
        "image": image_url,
        "caption": caption,
    }


def fetch_article(url: str, session: Optional[requests.Session] = None) -> Dict[str, Optional[str]]:
    """Télécharge et parse un article unique."""
    owns = session is None
    session = session or _make_session()
    try:
        html = _fetch_html(session, url)
        return parse_article_html(html, url)
    finally:
        if owns:
            session.close()


def scrape_full(
    start_url: str = START_URL,
    max_pages: Optional[int] = 1,
    limit: Optional[int] = None,
    delay_sec: float = 0.4,
) -> List[Dict[str, Optional[str]]]:
    """
    Récupère les URLs, puis télécharge et parse chaque article.

    Paramètres:
      - max_pages : pagination /news (None = toutes)
      - limit     : nombre max d’articles détaillés (sur l’ensemble)
      - delay_sec : temporisation entre requêtes
    """
    session = _make_session()
    try:
        urls = extract_all_news_links(start_url=start_url, max_pages=max_pages, delay_sec=delay_sec)
        if limit is not None:
            urls = urls[:max(0, int(limit))]
        results: List[Dict[str, Optional[str]]] = []
        for u in urls:
            html = _fetch_html(session, u)
            results.append(parse_article_html(html, u))
            time.sleep(delay_sec)
        return results
    finally:
        session.close()
