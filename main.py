from fastapi import FastAPI
from fastapi.responses import JSONResponse
from scraper import extract_all_news_links

app = FastAPI()

@app.get("/scrape")
def scrape():
    try:
        links = extract_all_news_links(max_pages=1)
        return JSONResponse(content={"status": "ok", "links": links})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
