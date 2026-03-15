# AppartSearch IDF — CLAUDE.md

Veille immobilière automatisée pour trouver un T2 en Île-de-France à max 1500€ CC.

## Stack

- **Backend :** Python 3 + Flask + SQLAlchemy (SQLite en local, SQLite sur Render)
- **Scraping :** BeautifulSoup (lxml) + requests + ScraperAPI (anti-Cloudflare)
- **Scheduler :** APScheduler — scrape toutes les 4h (`SCRAPE_INTERVAL_MINUTES=240`)
- **Alertes :** Gmail SMTP (`notifier.py`)
- **Frontend :** Jinja2 + CSS vanilla (pas de JS framework)
- **Hébergement :** Railway (gunicorn, `railway.toml`) — pas de cold start
- **Tests :** pytest + pytest-flask (31 tests)

## Architecture

```
app.py               # create_app(), routes /, /scrape-now, scrape_and_notify()
config.py            # Config class — toutes les vars d'env
models.py            # Annonce (SQLAlchemy model)
notifier.py          # send_email_alert() via Gmail SMTP
scrapers/
  __init__.py        # run_all_scrapers() — agrège toutes les sources
  base.py            # AbstractScraper (fetch_html, parse, scrape, est_colocation)
  pap.py             # PapScraper
  laforet.py         # LaforetScraper
  logicimmo.py       # LogicImmoScraper
tests/               # pytest — un fichier par module
```

## Sources scrapées

| Source     | Sélecteurs CSS clés                          | Pages | Depts couverts       |
|------------|----------------------------------------------|-------|----------------------|
| PAP.fr     | `div.search-list-item-alt`, `a.item-title`, `span.item-price` | 2 (Paris) + 1/dept | 75, 92, 93, 94 |
| Laforêt    | `a[data-gtm-click-vignette-param]`           | 1     | 75/92/93/94 (filtré par CP) |
| LeBonCoin  | `script#__NEXT_DATA__` → JSON `props.pageProps.searchData.ads` | 1 (tout IDF) | 75, 92, 93, 94 (filtré par zipcode) |
| ParuVendu  | `div.flex-1.overflow-hidden`, `h3.text-base a[href]`, `div.encoded-lnk div` (prix), `h3.text-base a span` (surface + ville) | 1 | 75, 92, 93, 94 (filtré par code dept) |

**Codes géo PAP.fr :** `dept_number + 364 = g_code` (ex: 92+364=456 → `g456`)

**LeBonCoin :** Site Next.js — données dans `<script id="__NEXT_DATA__">` JSON embarqué. Prix dans `price[0]`, surface dans `attributes[key="square"].value`, URL construite comme `https://www.leboncoin.fr/ad/locations/{list_id}.htm`. Le filtre dept exclut 77/78/91/95 (grande couronne IDF).

**ParuVendu :** HTML windows-1252 (forcer `response.encoding = "windows-1252"`). Pas de filtre IDF server-side — filtrage client-side par dept code `(XX)` dans le texte. Prix dans `div.encoded-lnk div`, surface via regex `(\d+)\s*m\s*2` (car `m²` = `m<sup>2</sup>`).

**Contrainte ScraperAPI :** `SCRAPE_INTERVAL_MINUTES` doit rester ≥ 1440 (1 scrape/jour). À 240 min (6×/jour), le budget free tier 1000 req/mois serait dépassé.

**Sources écartées :**
- BienIci — SPA JS-only, pas de contenu server-rendered
- Century21 — résultats chargés en JS uniquement

## ScraperAPI

- Clé : dans `SCRAPERAPI_KEY` (env var), free tier 1000 req/mois
- Utilisé dans `fetch_html()` via `urllib.parse.quote(url, safe='')` — **important** : l'URL doit être encodée sinon la page 2 de PAP est silencieusement ignorée
- Sans clé : fallback User-Agent classique (peut être bloqué par Cloudflare)

## Modèle Annonce

```python
url         # unique — sert de dédup (pas de doublons)
titre       # "{prix} {ville_raw}"
prix        # int (€ CC)
surface     # int (m²)
ville       # string — ville sans le code postal
departement # "75" / "92" / "93" / "94"
source      # "pap" / "laforet" / "logicimmo"
date_scrape # datetime UTC
```

## Filtres métier

- **T2 seulement**, IDF petite couronne (75/92/93/94), max 1500€ CC
- **Anti-colocation** : `est_colocation()` dans `AbstractScraper` filtre les mots-clés : `colocation`, `coloc`, `chambre chez`, `chambre en`
- **Dédup** : basé sur l'URL (unique constraint en DB)

## Variables d'environnement

| Variable                  | Description                          | Défaut          |
|---------------------------|--------------------------------------|-----------------|
| `SECRET_KEY`              | Flask secret key                     | `dev-key-...`   |
| `DATABASE_URL`            | SQLAlchemy URI                       | `sqlite:///annonces.db` |
| `EMAIL_DESTINATAIRE`      | Email qui reçoit les alertes         | `` (désactivé)  |
| `GMAIL_USER`              | Compte Gmail expéditeur              | ``              |
| `GMAIL_PASSWORD`          | Mot de passe d'application Gmail     | ``              |
| `SCRAPERAPI_KEY`          | Clé ScraperAPI anti-Cloudflare       | `` (fallback UA)|
| `SCRAPE_INTERVAL_MINUTES` | Fréquence scrape en minutes          | `240`           |
| `PRIX_MAX`                | Prix max (utilisé par certains scrapers) | `1500`      |

## Commandes utiles

```bash
# Lancer en local
cd "C:/Users/mugiw/OneDrive/Bureau/projet/rech appart"
python app.py

# Tests
python -m pytest tests/ -v

# Tests rapides (stop au 1er échec)
python -m pytest tests/ -x -q

# Scrape manuel (via l'appli)
# GET /scrape-now
```

## Déploiement (Railway)

- **Repo GitHub :** https://github.com/Maleysou-944/rech-appart.git
- **Site :** https://web-production-5bcef.up.railway.app (domaine custom : https://appart-rech.com)
- Push sur `master` → déploiement automatique
- Variables d'env à configurer dans le dashboard Railway (pas de `.env` en prod)
- Pas de cold start — APScheduler tourne en permanence
- **`--workers 1` obligatoire** : APScheduler in-process — plusieurs workers = N scrapes simultanés
- **`SCRAPE_INTERVAL_MINUTES=1440`** : contrainte ScraperAPI free tier (1000 req/mois)

## Conventions

- **Pas de framework JS** — templates Jinja2 + CSS vanilla uniquement
- **Un scraper = une classe** héritant de `AbstractScraper` dans `scrapers/`
- **Nouveaux scrapers** : implémenter `fetch_html()` et `parse()`, retourner une `List[Dict]` avec les clés du modèle `Annonce`
- **Tests** : un fichier `tests/test_<module>.py` par scraper, utiliser des fixtures HTML dans `fixtures/`
- **Pas de migration DB** — `db.create_all()` au démarrage suffit (SQLite simple)
