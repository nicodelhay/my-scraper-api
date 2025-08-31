## Copilot instructions - my-scraper-api

Bref: petit service FastAPI pour scraper le site Econostream sans Selenium (requests + BeautifulSoup). Le serveur est démarré via `uvicorn main:app` et expose des endpoints de listing et de récupération complète d'articles.

Fichiers clés
- `main.py` : point d'entrée FastAPI; endpoints exposés : `/healthz`, `/scrape`, `/scrape_full`, `/scrape_full.csv`.
- `econostream_requests.py` : logique de scraping (extraction de la liste, parsing d'article, utilitaires de session/retry, encodage d'URL). Voir `START_URL` et `BASE_URL`.
- `requirements.txt` : dépendances (fastapi, uvicorn, requests, beautifulsoup4, python-dateutil).
- `render.yaml` : configuration de déploiement (Render.com) — build/startCommand utiles pour reproduire l'environnement.

Comportement important à connaître
- Pagination/limits : `scrape` et `scrape_full` acceptent `max_pages`, `offset`, `limit`, ou `page`/`page_size` (page/page_size primaires si fournis). Par défaut `max_pages=1`.
- `delay_sec` paramètre par défaut 0.4 → utilisé pour throttling entre pages/requests. Ne pas le réduire en prod sans vérifier la charge.
- Champs retournés : voir `ALL_FIELDS` dans `main.py` (url, title, published, author, location, lede, text, word_count, image, caption). Le param `fields` permet de restreindre.
- CSV : `/scrape_full.csv` renvoie un fichier téléchargeable. Le nom de fichier inclut la date (econostream_YYYY-MM-DD.csv).

Conseils pour un agent IA (modifications sûres / patterns)
- Respecter les utilitaires existants : use `_make_session`, `_fetch_html`, `parse_article_html`, `extract_all_news_links` — préférez réutiliser plutôt que réécrire la logique de retry/UA/encodage.
- Encodage URL : utiliser `_encode_url` / `_abs_and_encode` pour construire des URLs valides (le site utilise des apostrophes typographiques et caractères non-ASCII).
- Tests manuels rapides : lancer `uvicorn main:app --reload` et appeler `/healthz` puis `/scrape?max_pages=1&limit=5`.
- Logging / erreurs : les endpoints renvoient JSON d'erreur en cas d'exception; pour debug local, lancer uvicorn sans `--workers` et observer la trace.

Exemples concrets (dev local)
- Installer : `python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt`
- Lancer : `uvicorn main:app --reload --port 8000`
- Tester un endpoint : `curl "http://127.0.0.1:8000/scrape_full?max_pages=1&limit=3&fields=url,title,published"`

Notes de sécurité/opérations
- Le scraper respecte un intervalle entre requêtes; évitez d'augmenter fortement `delay_sec` pour des runs massifs sans demander l'autorisation du site.
- `render.yaml` contient la commande de démarrage ; pour reproduire l'environnement de déploiement, utilisez la même `buildCommand` / `startCommand`.

Références rapides
- Entrées principales : `main.py` (endpoints + `ALL_FIELDS`) ; implémentation scraping : `econostream_requests.py` (`extract_all_news_links`, `scrape_full`, `parse_article_html`).

Si une section manque (tests, CI, politique de scraping), demandez-moi de l'ajouter — je peux aussi créer un README plus détaillé ou des tests unitaires pour `parse_article_html`.
