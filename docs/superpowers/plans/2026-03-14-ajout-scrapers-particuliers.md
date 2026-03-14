# Ajout Scrapers Particuliers (LeBonCoin + ParuVendu) Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter deux scrapers d'annonces particuliers (LeBonCoin et ParuVendu) au site AppartSearch IDF, en restant dans le free tier ScraperAPI (1000 req/mois).

**Architecture:** LeBonCoin utilise ScraperAPI pour contourner Cloudflare et extrait les données depuis le JSON `__NEXT_DATA__` embarqué dans la page. ParuVendu n'a pas de Cloudflare donc utilise `requests` direct avec BeautifulSoup sur HTML classique. Les deux héritent de `AbstractScraper` et sont enregistrés dans `run_all_scrapers()`.

**Tech Stack:** Python 3, requests, BeautifulSoup (lxml), json, pytest, ScraperAPI

**Spec:** `docs/superpowers/specs/2026-03-14-ajout-scrapers-particuliers-design.md`

---

## File Map

| Fichier | Action | Responsabilité |
|---|---|---|
| `fixtures/leboncoin_sample.html` | Créer | Fixture HTML avec `__NEXT_DATA__` JSON pour les tests |
| `scrapers/leboncoin.py` | Créer | `LeBonCoinScraper` — fetch via ScraperAPI, parse JSON |
| `tests/test_leboncoin.py` | Créer | Tests unitaires du scraper LeBonCoin |
| `fixtures/paruvendu_sample.html` | Créer | Fixture HTML réelle capturée depuis ParuVendu |
| `scrapers/paruvendu.py` | Créer | `ParuVenduScraper` — fetch direct, parse HTML |
| `tests/test_paruvendu.py` | Créer | Tests unitaires du scraper ParuVendu |
| `scrapers/__init__.py` | Modifier | Enregistrer les 2 nouveaux scrapers dans `run_all_scrapers()` |
| `CLAUDE.md` | Modifier | Documenter les nouvelles sources et leurs sélecteurs |

---

## Chunk 1: LeBonCoin scraper

### Task 1: Créer la fixture LeBonCoin

**Files:**
- Create: `fixtures/leboncoin_sample.html`

LeBonCoin est un site Next.js. Les annonces sont dans un bloc `<script id="__NEXT_DATA__" type="application/json">` dans le HTML. On crée une fixture avec 3 annonces : 2 valides en IDF petite couronne (75/92), 1 à exclure (78 — grande couronne).

- [ ] **Step 1: Créer la fixture HTML**

Créer `fixtures/leboncoin_sample.html` :

```html
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>leboncoin</title></head>
<body>
<script id="__NEXT_DATA__" type="application/json">
{
  "props": {
    "pageProps": {
      "searchData": {
        "ads": [
          {
            "list_id": 2740000001,
            "subject": "Appartement T2 Paris 11e",
            "price": [950],
            "location": {
              "city": "Paris",
              "zipcode": "75011",
              "department_id": "75"
            },
            "attributes": [
              {"key": "square", "value": "35", "value_label": "35 m²"}
            ]
          },
          {
            "list_id": 2740000002,
            "subject": "T2 Neuilly-sur-Seine calme",
            "price": [1200],
            "location": {
              "city": "Neuilly-sur-Seine",
              "zipcode": "92200",
              "department_id": "92"
            },
            "attributes": [
              {"key": "square", "value": "45", "value_label": "45 m²"}
            ]
          },
          {
            "list_id": 2740000003,
            "subject": "Appartement Versailles",
            "price": [900],
            "location": {
              "city": "Versailles",
              "zipcode": "78000",
              "department_id": "78"
            },
            "attributes": []
          }
        ]
      }
    }
  }
}
</script>
</body>
</html>
```

- [ ] **Step 2: Commit la fixture**

```bash
git add fixtures/leboncoin_sample.html
git commit -m "test: fixture HTML LeBonCoin avec __NEXT_DATA__"
```

---

### Task 2: TDD — LeBonCoin scraper

**Files:**
- Create: `tests/test_leboncoin.py`
- Create: `scrapers/leboncoin.py`

- [ ] **Step 1: Écrire les tests (qui vont échouer)**

Créer `tests/test_leboncoin.py` :

```python
from pathlib import Path
from scrapers.leboncoin import LeBonCoinScraper

FIXTURE = Path("fixtures/leboncoin_sample.html").read_text(encoding="utf-8")


def test_leboncoin_parse_retourne_des_annonces():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) > 0


def test_leboncoin_annonce_a_les_champs_requis():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert "url" in a
        assert "titre" in a
        assert "prix" in a
        assert "source" in a
        assert a["source"] == "leboncoin"


def test_leboncoin_urls_absolues():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["url"].startswith("https://"), f"URL invalide: {a['url']}"


def test_leboncoin_filtre_hors_idf():
    """Versailles (78) doit être exclu — seuls 75/92/93/94 gardés."""
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["departement"] in {"75", "92", "93", "94"}, (
            f"Département hors IDF petite couronne: {a['departement']}"
        )


def test_leboncoin_fixture_a_2_annonces_valides():
    """La fixture a 3 annonces, 1 en grande couronne (78) → 2 retournées."""
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) == 2


def test_leboncoin_surface_est_entier_ou_none():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["surface"] is None or isinstance(a["surface"], int)


def test_leboncoin_prix_est_entier_ou_none():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["prix"] is None or isinstance(a["prix"], int)


def test_leboncoin_parse_html_vide_retourne_liste_vide():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse("")
    assert annonces == []


def test_leboncoin_parse_sans_next_data_retourne_liste_vide():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse("<html><body>Pas de __NEXT_DATA__</body></html>")
    assert annonces == []
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd "C:/Users/mugiw/OneDrive/Bureau/projet/rech appart"
python -m pytest tests/test_leboncoin.py -v
```

Résultat attendu : `ModuleNotFoundError: No module named 'scrapers.leboncoin'`

- [ ] **Step 3: Implémenter `scrapers/leboncoin.py`**

Créer `scrapers/leboncoin.py` :

```python
import json
import logging
import os
import requests
from typing import List, Dict
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base import AbstractScraper

logger = logging.getLogger(__name__)

SEARCH_URL = (
    "https://www.leboncoin.fr/recherche"
    "?category=10&locations=Ile-de-France"
    "&price=max-1500&real_estate_type=2&rooms=1-3"
)
BASE_URL = "https://www.leboncoin.fr"
IDF_DEPTS = {"75", "92", "93", "94"}


class LeBonCoinScraper(AbstractScraper):
    def __init__(self, url: str = SEARCH_URL):
        self.url = url

    def fetch_html(self, url: str) -> str:
        api_key = os.environ.get("SCRAPERAPI_KEY", "")
        logger.info("Fetching LeBonCoin: %s", url)
        if api_key:
            proxy_url = (
                f"http://api.scraperapi.com?api_key={api_key}"
                f"&url={quote(url, safe='')}&country_code=fr"
            )
            response = requests.get(proxy_url, timeout=60)
        else:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "fr-FR,fr;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> List[Dict]:
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        annonces = []

        try:
            script = soup.find("script", {"id": "__NEXT_DATA__"})
            if not script or not script.string:
                logger.error("LeBonCoin: balise __NEXT_DATA__ introuvable")
                return []
            data = json.loads(script.string)
            ads = data["props"]["pageProps"]["searchData"]["ads"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("LeBonCoin: échec parsing __NEXT_DATA__: %s", e)
            return []

        for ad in ads:
            try:
                list_id = ad.get("list_id")
                if not list_id:
                    continue

                url = f"{BASE_URL}/ad/locations/{list_id}.htm"

                # Prix
                price_list = ad.get("price", [])
                prix = int(price_list[0]) if price_list else None

                # Surface — dans la liste "attributes", clé "square"
                surface = None
                for attr in ad.get("attributes", []):
                    if attr.get("key") == "square":
                        try:
                            surface = int(float(attr.get("value", 0)))
                        except (ValueError, TypeError):
                            pass
                        break

                # Localisation
                location = ad.get("location", {})
                ville = location.get("city", "")
                zipcode = location.get("zipcode", "")
                departement = zipcode[:2] if zipcode else None

                # Filtre petite couronne IDF uniquement
                if departement not in IDF_DEPTS:
                    continue

                titre = f"{prix} {ville}" if prix and ville else ad.get("subject", "")

                if self.est_colocation(titre):
                    continue

                annonces.append({
                    "url": url,
                    "titre": titre,
                    "prix": prix,
                    "surface": surface,
                    "ville": ville,
                    "departement": departement,
                    "source": "leboncoin",
                })
            except Exception as e:
                logger.debug("LeBonCoin: skip annonce %s: %s", ad.get("list_id"), e)
                continue

        logger.info("Parsed %d annonces depuis LeBonCoin", len(annonces))
        return annonces
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
python -m pytest tests/test_leboncoin.py -v
```

Résultat attendu : tous les tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add scrapers/leboncoin.py tests/test_leboncoin.py
git commit -m "feat: scraper LeBonCoin — __NEXT_DATA__ JSON + filtre IDF petite couronne"
```

---

### Task 3: Brancher LeBonCoin dans run_all_scrapers()

**Files:**
- Modify: `scrapers/__init__.py`

- [ ] **Step 1: Ajouter l'import et l'appel dans `__init__.py`**

En haut du fichier, ajouter l'import :
```python
from .leboncoin import LeBonCoinScraper
```

Dans `run_all_scrapers()`, après le bloc Laforêt, ajouter :
```python
    leboncoin = LeBonCoinScraper()
    try:
        html = leboncoin.fetch_html(leboncoin.url)
        annonces_lbc = leboncoin.parse(html)
        results.extend(annonces_lbc)
        print(f"LeBonCoin: OK ({len(annonces_lbc)} annonces IDF)", flush=True)
    except Exception as e:
        logger.error(f"Erreur LeBonCoin: {e}")
        print(f"SCRAPER ERROR LeBonCoin: {e}", flush=True)
```

- [ ] **Step 2: Lancer la suite de tests complète**

```bash
python -m pytest tests/ -v
```

Résultat attendu : tous les tests existants + `test_leboncoin.py` passent.

- [ ] **Step 3: Commit**

```bash
git add scrapers/__init__.py
git commit -m "feat: enregistrer LeBonCoinScraper dans run_all_scrapers"
```

---

## Chunk 2: ParuVendu scraper

### Task 4: Capturer la fixture ParuVendu

**Files:**
- Create: `fixtures/paruvendu_sample.html`

> **Note importante :** Les sélecteurs CSS de ParuVendu ne sont pas connus à l'avance. Cette tâche consiste à capturer le vrai HTML, puis à identifier les sélecteurs avant d'écrire les tests.

- [ ] **Step 1: Capturer le HTML réel de ParuVendu**

Exécuter ce script Python une fois en local pour sauvegarder la fixture :

```python
import requests
from pathlib import Path

url = (
    "https://www.paruvendu.fr/immobilier/louer/appartement/ile-de-france/"
    "?px_loyermax=1500&nb_pieces[]=1&nb_pieces[]=2&nb_pieces[]=3"
)
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fr-FR,fr;q=0.9",
}
r = requests.get(url, headers=headers, timeout=15)
r.raise_for_status()
Path("fixtures/paruvendu_sample.html").write_text(r.text, encoding="utf-8")
print(f"Sauvegardé ({len(r.text)} chars)")
```

Si la requête retourne un 403 ou un CAPTCHA : ré-essayer plus tard ou manuellement sauvegarder la page depuis le navigateur (Ctrl+S → "Page Web, HTML uniquement").

- [ ] **Step 2: Inspecter la fixture pour trouver les sélecteurs**

Ouvrir `fixtures/paruvendu_sample.html` et identifier :
- Le sélecteur du bloc annonce (ex: `article.annonce`, `div[class*="offer"]`, etc.)
- Le sélecteur du prix
- Le sélecteur de la surface
- Le sélecteur de la ville / code postal
- Le sélecteur du lien vers l'annonce

Méthode rapide en Python :
```python
from bs4 import BeautifulSoup
from pathlib import Path

html = Path("fixtures/paruvendu_sample.html").read_text(encoding="utf-8")
soup = BeautifulSoup(html, "lxml")

# Explorer la structure
# Chercher des blocs répétés qui ressemblent à des annonces :
for tag in ["article", "li", "div"]:
    items = soup.find_all(tag, limit=3)
    for i, el in enumerate(items):
        classes = el.get("class", [])
        if classes:
            print(f"{tag}.{'.'.join(classes)}: {el.get_text()[:80]!r}")
```

- [ ] **Step 3: Commit la fixture**

```bash
git add fixtures/paruvendu_sample.html
git commit -m "test: fixture HTML ParuVendu capturée depuis le site réel"
```

---

### Task 5: TDD — ParuVendu scraper

**Files:**
- Create: `tests/test_paruvendu.py`
- Create: `scrapers/paruvendu.py`

> **Prérequis :** Les sélecteurs CSS identifiés à la Task 4 sont nécessaires pour écrire les tests et l'implémentation. Remplacer `SELECTEUR_BLOC`, `SELECTEUR_PRIX`, etc. par les vraies valeurs trouvées.

- [ ] **Step 1: Écrire les tests (qui vont échouer)**

Créer `tests/test_paruvendu.py` :

```python
from pathlib import Path
from scrapers.paruvendu import ParuVenduScraper

FIXTURE = Path("fixtures/paruvendu_sample.html").read_text(encoding="utf-8")


def test_paruvendu_parse_retourne_des_annonces():
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) > 0


def test_paruvendu_annonce_a_les_champs_requis():
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert "url" in a
        assert "titre" in a
        assert "prix" in a
        assert "source" in a
        assert a["source"] == "paruvendu"


def test_paruvendu_urls_absolues():
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["url"].startswith("https://"), f"URL invalide: {a['url']}"


def test_paruvendu_filtre_hors_idf():
    """Seuls les depts 75/92/93/94 doivent être retournés."""
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        if a["departement"]:
            assert a["departement"] in {"75", "92", "93", "94"}, (
                f"Département hors IDF petite couronne: {a['departement']}"
            )


def test_paruvendu_surface_est_entier_ou_none():
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["surface"] is None or isinstance(a["surface"], int)


def test_paruvendu_prix_est_entier_ou_none():
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["prix"] is None or isinstance(a["prix"], int)


def test_paruvendu_parse_html_vide_retourne_liste_vide():
    scraper = ParuVenduScraper()
    annonces = scraper.parse("")
    assert annonces == []
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
python -m pytest tests/test_paruvendu.py -v
```

Résultat attendu : `ModuleNotFoundError: No module named 'scrapers.paruvendu'`

- [ ] **Step 3: Implémenter `scrapers/paruvendu.py`**

Créer `scrapers/paruvendu.py` en adaptant les sélecteurs trouvés à la Task 4 :

```python
import logging
import re
import requests
from typing import List, Dict

from bs4 import BeautifulSoup

from .base import AbstractScraper

logger = logging.getLogger(__name__)

SEARCH_URL = (
    "https://www.paruvendu.fr/immobilier/louer/appartement/ile-de-france/"
    "?px_loyermax=1500&nb_pieces[]=1&nb_pieces[]=2&nb_pieces[]=3"
)
BASE_URL = "https://www.paruvendu.fr"
IDF_DEPTS = {"75", "92", "93", "94"}


class ParuVenduScraper(AbstractScraper):
    def __init__(self, url: str = SEARCH_URL):
        self.url = url

    def fetch_html(self, url: str) -> str:
        logger.info("Fetching ParuVendu: %s", url)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.warning("ParuVendu: échec fetch %s: %s", url, e)
            return ""

    def parse(self, html: str) -> List[Dict]:
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        annonces = []

        # TODO: remplacer "SELECTEUR_BLOC" par le sélecteur identifié à la Task 4
        # Exemple : items = soup.select("article.annonce")
        items = soup.select("SELECTEUR_BLOC")
        logger.debug("ParuVendu: %d blocs trouvés", len(items))

        for item in items:
            try:
                # Lien — adapter le sélecteur
                link_el = item.select_one("a[href]")
                if not link_el:
                    continue
                href = link_el.get("href", "").strip()
                url = href if href.startswith("http") else BASE_URL + href

                # Prix — adapter le sélecteur et le parsing
                prix = None
                prix_el = item.select_one("SELECTEUR_PRIX")
                if prix_el:
                    raw = prix_el.get_text(separator=" ").strip()
                    digits = re.sub(r"[^\d]", "", raw.replace("\u00a0", ""))
                    if digits:
                        prix = int(digits)

                # Surface
                surface = None
                surface_el = item.select_one("SELECTEUR_SURFACE")
                if surface_el:
                    m = re.search(r"([\d,\.]+)\s*m²", surface_el.get_text())
                    if m:
                        try:
                            surface = int(float(m.group(1).replace(",", ".")))
                        except ValueError:
                            pass

                # Ville & département — adapter le sélecteur
                ville = ""
                departement = None
                ville_el = item.select_one("SELECTEUR_VILLE")
                if ville_el:
                    ville_raw = ville_el.get_text(strip=True)
                    dept_match = re.search(r"\((\d{5})\)", ville_raw)
                    if dept_match:
                        departement = dept_match.group(1)[:2]
                    ville = re.sub(r"\s*\(\d+\)\s*$", "", ville_raw).strip()

                # Filtre petite couronne IDF
                if departement not in IDF_DEPTS:
                    continue

                titre = f"{prix} {ville}" if prix and ville else ""

                if self.est_colocation(titre):
                    continue

                annonces.append({
                    "url": url,
                    "titre": titre,
                    "prix": prix,
                    "surface": surface,
                    "ville": ville,
                    "departement": departement,
                    "source": "paruvendu",
                })
            except Exception as e:
                logger.debug("ParuVendu: skip annonce: %s", e)
                continue

        logger.info("Parsed %d annonces depuis ParuVendu", len(annonces))
        return annonces
```

> **Important :** Remplacer tous les `"SELECTEUR_*"` par les vrais sélecteurs trouvés à la Task 4 avant de lancer les tests.

- [ ] **Step 4: Vérifier que les tests passent**

```bash
python -m pytest tests/test_paruvendu.py -v
```

Résultat attendu : tous les tests `PASSED`

- [ ] **Step 5: Commit**

```bash
git add scrapers/paruvendu.py tests/test_paruvendu.py
git commit -m "feat: scraper ParuVendu — requests direct + filtre IDF petite couronne"
```

---

### Task 6: Brancher ParuVendu dans run_all_scrapers()

**Files:**
- Modify: `scrapers/__init__.py`

- [ ] **Step 1: Ajouter l'import et l'appel dans `__init__.py`**

En haut du fichier, ajouter l'import :
```python
from .paruvendu import ParuVenduScraper
```

Dans `run_all_scrapers()`, après le bloc LeBonCoin, ajouter :
```python
    paruvendu = ParuVenduScraper()
    try:
        html = paruvendu.fetch_html(paruvendu.url)
        annonces_pv = paruvendu.parse(html)
        results.extend(annonces_pv)
        print(f"ParuVendu: OK ({len(annonces_pv)} annonces IDF)", flush=True)
    except Exception as e:
        logger.error(f"Erreur ParuVendu: {e}")
        print(f"SCRAPER ERROR ParuVendu: {e}", flush=True)
```

- [ ] **Step 2: Lancer la suite de tests complète**

```bash
python -m pytest tests/ -v
```

Résultat attendu : tous les tests passent.

- [ ] **Step 3: Commit**

```bash
git add scrapers/__init__.py
git commit -m "feat: enregistrer ParuVenduScraper dans run_all_scrapers"
```

---

### Task 7: Mettre à jour CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Ajouter les nouvelles sources dans le tableau**

Dans la section `## Sources scrapées`, ajouter les lignes :

```markdown
| LeBonCoin | `script#__NEXT_DATA__` → JSON `props.pageProps.searchData.ads` | 1 | 75, 92, 93, 94 |
| ParuVendu | sélecteurs CSS à documenter après Task 4 | 1 | 75/92/93/94 (filtré par CP) |
```

Et ajouter dans la section `## Sources scrapées` une note :
```markdown
**Contrainte ScraperAPI :** Intervalle scrape doit rester ≥ 1440 min (SCRAPE_INTERVAL_MINUTES) — sinon le budget free tier (1000 req/mois) est dépassé.
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: documenter LeBonCoin et ParuVendu dans CLAUDE.md"
```

---

## Vérification finale

- [ ] Lancer la suite complète une dernière fois :

```bash
python -m pytest tests/ -v
```

Tous les tests doivent passer (31 existants + nouveaux).

- [ ] Vérifier que `source` dans la DB inclut bien `"leboncoin"` et `"paruvendu"` dans l'interface (filtre sources sur le site).
