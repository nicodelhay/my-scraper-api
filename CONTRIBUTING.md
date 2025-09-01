# Contributing

Merci de vouloir contribuer à my-scraper-api. Ce fichier décrit rapidement le flux attendu pour apporter des changements utiles et sûrs au scraper.

1) But du projet
- Service FastAPI qui scrape Econostream sans Selenium. Toute contribution doit préserver la gestion des retries, de l'UA et de l'encodage d'URL (voir `econostream_requests.py`).

2) Mise en place locale (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

3) Règles de branche / PR
- Créez une branche courte descriptive : `feat/xxx`, `fix/xxx`, `docs/xxx`.
- Commits atomiques et messages clairs : `feat: add X`, `fix: handle Y`, `docs: update README`.
- Ouvrez une PR contre `main` (même si actuellement nous acceptons aussi des pushes directs, préférez la PR pour les changements significatifs).

4) Tests et validations
- Écrivez des tests unitaires pour tout changement sur le parsing HTML (cible : `parse_article_html`).
- Si vous ajoutez linters/formatters (black/isort/flake8), documentez la commande de vérification.

5) Spécificités du scraper
- Respectez le paramètre `delay_sec` pour limiter la charge. Par défaut 0.4s.
- Réutilisez `_make_session`, `_fetch_html`, et `parse_article_html` pour garder la cohérence des retries/UA.
- Utilisez `_abs_and_encode` pour normaliser les URLs (le site contient des caractères typographiques non-ASCII).

6) Politique d'éthique
- N'exécutez pas de crawl massif sans accord du site. Si vous avez besoin d'extraire de grandes quantités, contactez le mainteneur.

7) Contact / revue
- Ouvrez une PR et ajoutez un petit descriptif du changement et des étapes pour reproduire localement. Le mainteneur procédera à la revue.

Merci !
