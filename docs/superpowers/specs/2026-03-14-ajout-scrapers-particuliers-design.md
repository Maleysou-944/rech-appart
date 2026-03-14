# Design — Ajout scrapers particuliers : LeBonCoin + ParuVendu

**Date :** 2026-03-14
**Projet :** AppartSearch IDF
**Statut :** Approuvé

## Contexte

Le site scrape actuellement PAP.fr et Laforêt pour trouver des T1/T2/T3 en IDF à max 1500€ CC.
L'objectif est d'augmenter le volume d'annonces en ajoutant deux sources orientées **particuliers** (sans frais d'agence), en restant dans le free tier ScraperAPI (1000 req/mois).

## Sources ajoutées

### LeBonCoin
- Plus grand gisement d'annonces particuliers en France
- Protégé par Cloudflare → nécessite ScraperAPI
- Site Next.js : les annonces sont dans `<script id="__NEXT_DATA__">` (JSON embarqué dans la page)
- **1 req/scrape** (1 URL couvre tout l'IDF)

### ParuVendu
- Site de petites annonces particuliers
- Pas de Cloudflare → `requests` direct, **0 crédit ScraperAPI**
- HTML server-rendered classique (BeautifulSoup + sélecteurs CSS)
- **1 req/scrape**

## Budget ScraperAPI

| Source     | req/scrape | req/mois (×30) |
|------------|------------|----------------|
| PAP        | 13         | 390            |
| Laforêt    | 3          | 90             |
| LeBonCoin  | 1          | 30             |
| ParuVendu  | 0          | 0              |
| **Total**  | **17**     | **510 / 1000** |

→ 490 req de marge sur le free tier.

> **Contrainte interval :** Ce calcul suppose `SCRAPE_INTERVAL_MINUTES=1440` (1 scrape/jour). Si l'intervalle repasse à 240 min (6×/jour), le total monterait à ~2040 req/mois, dépassant le free tier. L'intervalle doit rester ≥ 1440 min tant qu'on reste sur le free tier ScraperAPI.

## Architecture

Deux nouveaux fichiers dans `scrapers/` :

```
scrapers/
  leboncoin.py     # LeBonCoinScraper — via ScraperAPI + JSON __NEXT_DATA__
  paruvendu.py     # ParuVenduScraper — requests direct + BeautifulSoup
```

Les deux héritent de `AbstractScraper` (même pattern que `pap.py` / `laforet.py`).
Enregistrés dans `scrapers/__init__.py` → `run_all_scrapers()`.

## Détails d'implémentation

### LeBonCoin

**URL :**
```
https://www.leboncoin.fr/recherche?category=10&locations=Ile-de-France&price=max-1500&real_estate_type=2&rooms=1-3
```

**fetch_html() :** via ScraperAPI (même pattern que `pap.py`)

**parse() :**
```python
script = soup.find("script", {"id": "__NEXT_DATA__"})
data = json.loads(script.string)
ads = data["props"]["pageProps"]["searchData"]["ads"]
```

> **Note :** Le chemin JSON exact (`searchData.ads`) est à confirmer depuis la fixture HTML lors de l'implémentation — la structure Next.js de LeBonCoin peut changer. Le parse() doit inclure un `try/except` global avec `logger.error()` en cas d'échec de parsing ou de clé manquante, et retourner `[]` plutôt que lever une exception.

Champs à extraire par annonce (noms de clés JSON à confirmer sur fixture) :
- `url` — lien vers l'annonce (probablement `list_id` → construire l'URL)
- `prix` — int en € (probablement `price[0]`)
- `surface` — int en m² (probablement dans `attributes`, clé `square`)
- `ville` — string (probablement `location.city`)
- `departement` — 2 premiers chiffres du code postal (`location.zipcode[:2]`)

**Filtre département :** code postal → garder uniquement 75/92/93/94
(LeBonCoin IDF inclut aussi 77/78/91/95 qu'on veut exclure)

**Gestion d'erreurs :**
- HTTP error → `raise_for_status()` laissé propager (loggué dans `run_all_scrapers`)
- JSON decode error ou clé manquante → `logger.error()` + retourner `[]`
- Annonce individuelle mal formée → `logger.debug()` + skip (continuer les autres)

**source :** `"leboncoin"`

### ParuVendu

**URL :**
```
https://www.paruvendu.fr/immobilier/louer/appartement/ile-de-france/?px_loyermax=1500&nb_pieces[]=1&nb_pieces[]=2&nb_pieces[]=3
```

**fetch_html() :** `requests` direct avec User-Agent standard (pas de ScraperAPI). En cas de réponse 403 ou CAPTCHA, logger un warning et retourner une chaîne vide — le parse() retournera `[]` silencieusement.

**Pré-requis implémentation :** Capturer une fixture HTML réelle depuis l'URL ci-dessus **avant** d'écrire parse(). Identifier les sélecteurs CSS sur la fixture. Les sélecteurs cibles probables :
- Bloc annonce : `article` ou `div.annonce` (à confirmer)
- Prix, surface, ville : éléments texte dans le bloc

**Gestion d'erreurs :**
- HTTP error ou réponse vide → `logger.warning()` + retourner `[]`
- Annonce individuelle mal formée → skip + `logger.debug()`

**Filtre département :** même logique code postal → 75/92/93/94

**source :** `"paruvendu"`

## Filtres métier (inchangés)

- Anti-colocation : `est_colocation()` de `AbstractScraper` (hérité automatiquement)
- Dédup : basé sur l'URL (unique constraint DB existante)
- Prix max 1500€, T1/T2/T3, IDF petite couronne

## Tests

Un fichier de test par scraper :
- `tests/test_leboncoin.py` — fixture HTML avec `__NEXT_DATA__` JSON
- `tests/test_paruvendu.py` — fixture HTML server-rendered

Pattern identique aux tests existants (`tests/test_pap.py`, `tests/test_laforet.py`).

## Fichiers modifiés

| Fichier | Action |
|---|---|
| `scrapers/leboncoin.py` | Créer |
| `scrapers/paruvendu.py` | Créer |
| `scrapers/__init__.py` | Modifier — enregistrer les 2 nouveaux scrapers |
| `tests/test_leboncoin.py` | Créer |
| `tests/test_paruvendu.py` | Créer |
| `fixtures/leboncoin_sample.html` | Créer |
| `fixtures/paruvendu_sample.html` | Créer |
| `CLAUDE.md` | Modifier — documenter les nouvelles sources |
