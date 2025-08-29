# -*- coding: utf-8 -*-
"""
FastAPI pour exposer le scraper Econostream sur Render.
Endpoints:
- /healthz
- /scrape        -> liens d'articles
- /scrape_full   -> articles détaillés (titre, date, auteur, lieu, lede, texte, image, caption)
"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from econostream_requests import (
    extract_all_news_links,
    scrape_full as scrape_full_impl,
    START_URL,
)

app = FastAPI(title="Econostream Scraper API", version="1.2.0")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/scrape")
def scrape(
    max_pages: int | None = Query(1, ge=1, description="Nombre de pages à parcourir (None = toutes)"),
    all_pages: bool = Query(False, description="Si true, ignore max_pages et parcourt toutes les pages"),
    delay_sec: float = Query(0.4, ge=0.0, le=5.0, description="Délai (s) entre pages"),
):
    """Retourne {"status","count","links":[...]}."""
    try:
        effective_max = None if all_pages else max_pages
        links = extract_all_news_links(start_url=START_URL, max_pages=effective_max, delay_sec=delay_sec)
        return JSONResponse(content={"status": "ok", "count": len(links), "links": links})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/scrape_full")
def scrape_full_endpoint(
    max_pages: Optional[int] = Query(1, ge=1, description="Nombre de pages News (None = toutes)"),
    all_pages: bool = Query(False, description="Si true, ignore max_pages et parcourt toutes les pages"),
    limit: Optional[int] = Query(10, ge=1, description="Nombre max d’articles détaillés"),
    delay_sec: float = Query(0.4, ge=0.0, le=5.0, description="Délai (s) entre requêtes"),
):
    """
    Retourne {"status","count","items":[{url,title,published,author,location,lede,text,word_count,image,caption},...]}.
    """
    try:
        effective_max = None if all_pages else max_pages
        items = scrape_full_impl(
            start_url=START_URL,
            max_pages=effective_max,
            limit=limit,
            delay_sec=delay_sec,
        )
        return JSONResponse(content={"status": "ok", "count": len(items), "items": items})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
