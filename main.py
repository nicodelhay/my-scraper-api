# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import date
from typing import List, Optional, Sequence

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, StreamingResponse
import io, csv

from econostream_requests import (
    extract_all_news_links,
    scrape_full as scrape_full_impl,
    START_URL,
)

app = FastAPI(title="Econostream Scraper API", version="1.3.0")

# --- utils API --- #
ALL_FIELDS: Sequence[str] = (
    "url", "title", "published", "author", "location",
    "lede", "text", "word_count", "image", "caption"
)

def _parse_fields(fields: Optional[str]) -> List[str]:
    if not fields:
        return list(ALL_FIELDS)
    want = [f.strip() for f in fields.split(",") if f.strip()]
    # garde uniquement les champs connus; si vide, on renvoie tout
    keep = [f for f in want if f in ALL_FIELDS]
    return keep if keep else list(ALL_FIELDS)

def _project_item(item: dict, keep: Sequence[str]) -> dict:
    return {k: item.get(k) for k in keep}

# --- endpoints --- #
@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/scrape")
def scrape(
    max_pages: int | None = Query(1, ge=1, description="Nombre de pages /news à parcourir (None = toutes)"),
    all_pages: bool = Query(False, description="Si true, ignore max_pages et prend toutes les pages"),
    delay_sec: float = Query(0.4, ge=0.0, le=5.0),
    offset: int = Query(0, ge=0, description="Décalage dans la liste d'URLs"),
    limit: Optional[int] = Query(None, ge=1, description="Nombre d'URLs à renvoyer"),
):
    """
    Renvoie des URLs d'articles (avec pagination offset/limit).
    """
    try:
        effective_max = None if all_pages else max_pages
        links = extract_all_news_links(start_url=START_URL, max_pages=effective_max, delay_sec=delay_sec)
        total = len(links)
        sel = links[offset: offset + limit] if (limit is not None) else links[offset:]
        return JSONResponse(content={
            "status": "ok",
            "total": total,
            "offset": offset,
            "count": len(sel),
            "links": sel
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/scrape_full")
def scrape_full_endpoint(
    max_pages: Optional[int] = Query(1, ge=1, description="Nombre de pages /news à collecter (None = toutes)"),
    all_pages: bool = Query(False, description="Si true, ignore max_pages"),
    offset: int = Query(0, ge=0, description="Décalage dans la liste d'articles"),
    limit: Optional[int] = Query(10, ge=1, description="Nombre d’articles à renvoyer"),
    delay_sec: float = Query(0.4, ge=0.0, le=5.0),
    fields: Optional[str] = Query(None, description=f"Champs à renvoyer, séparés par des virgules. Ex: url,title,published (défaut: {','.join(ALL_FIELDS)})"),
    # pagination alternative (page/page_size) – optionnelle
    page: Optional[int] = Query(None, ge=1, description="Page (alternative à offset)"),
    page_size: Optional[int] = Query(None, ge=1, description="Taille de page (alternative à limit)"),
):
    """
    JSON (par défaut) avec pagination offset/limit ou page/page_size et filtrage de champs.
    """
    try:
        # Normalisation pagination
        if page is not None:
            # Si page/page_size fournis, ils priment
            ps = page_size or (limit or 10)
            offset = (page - 1) * ps
            limit = ps

        effective_max = None if all_pages else max_pages
        items, total = scrape_full_impl(
            start_url=START_URL,
            max_pages=effective_max,
            offset=offset,
            limit=limit,
            delay_sec=delay_sec,
        )

        keep = _parse_fields(fields)
        items = [_project_item(it, keep) for it in items]

        return JSONResponse(content={
            "status": "ok",
            "total": total,        # nb total de candidats trouvés sur /news (selon max_pages)
            "offset": offset,
            "count": len(items),
            "fields": keep,
            "items": items,
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/scrape_full.csv")
def scrape_full_csv(
    max_pages: Optional[int] = Query(1, ge=1),
    all_pages: bool = Query(False),
    offset: int = Query(0, ge=0),
    limit: Optional[int] = Query(10, ge=1),
    delay_sec: float = Query(0.4, ge=0.0, le=5.0),
    fields: Optional[str] = Query(None, description="Champs CSV, ex: url,title,published"),
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1),
):
    """
    Même données que /scrape_full, mais au format CSV (download).
    """
    try:
        if page is not None:
            ps = page_size or (limit or 10)
            offset = (page - 1) * ps
            limit = ps

        effective_max = None if all_pages else max_pages
        items, total = scrape_full_impl(
            start_url=START_URL,
            max_pages=effective_max,
            offset=offset,
            limit=limit,
            delay_sec=delay_sec,
        )

        keep = _parse_fields(fields)
        # Construction CSV
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=keep, extrasaction="ignore")
        writer.writeheader()
        for it in items:
            writer.writerow({k: it.get(k, "") for k in keep})
        buf.seek(0)

        filename = f"econostream_{date.today().isoformat()}.csv"
        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
        return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv", headers=headers)
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
