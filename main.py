# -*- coding: utf-8 -*-
from __future__ import annotations

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from econostream_requests import extract_all_news_links, START_URL

app = FastAPI(title="Econostream Scraper API", version="1.0.0")

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/scrape")
def scrape(
    max_pages: int | None = Query(1, ge=1, description="Nombre de pages à parcourir (None = toutes)"),
    all_pages: bool = Query(False, description="Si true, ignore max_pages et parcourt toutes les pages"),
    delay_sec: float = Query(0.4, ge=0.0, le=5.0, description="Delai (s) entre pages"),
):
    try:
        effective_max = None if all_pages else max_pages
        links = extract_all_news_links(start_url=START_URL, max_pages=effective_max, delay_sec=delay_sec)
        return JSONResponse(content={"status": "ok", "count": len(links), "links": links})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
