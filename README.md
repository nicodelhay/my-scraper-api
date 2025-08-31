# Econostream Scraper API

Petit service FastAPI pour scraper le site Econostream (requests + BeautifulSoup). Conçu pour tourner sur Render (voir `render.yaml`).

Quick start

1. Créer un environnement virtuel et installer les dépendances :

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. Lancer le serveur en local :

   ```powershell
   uvicorn main:app --reload --port 8000
   ```

3. Endpoints utiles :

- `/healthz` — état du service
- `/scrape` — renvoie une liste d'URLs d'articles (params: `max_pages`, `delay_sec`, `offset`, `limit`)
- `/scrape_full` — renvoie les articles complets (params: `max_pages`, `delay_sec`, `offset`, `limit`, `fields`)
- `/scrape_full.csv` — même données que `/scrape_full` mais en CSV téléchargeable

Structure du projet

- `main.py` : FastAPI app, endpoints et logique de projection/champs
- `econostream_requests.py` : scraping, parsing d'articles, utilitaires réseau
- `render.yaml` : configuration pour déploiement sur Render
- `requirements.txt` : dépendances

Contribuer

Ouvrez une PR pour toute modification. Si vous ajoutez des tests ou changez le parsing HTML, vérifiez que `parse_article_html` couvre les cas (title, date, auteur, image).

Licence

Doit être ajoutée — contactez le mainteneur pour la choisir.
