# AppartSearch IDF — Améliorations UI + Scrapers

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer la liste d'annonces par une grille de cards aérées, ajouter des filtres département/source, et intégrer de nouvelles sources d'annonces (BienIci, Laforêt, Century21).

**Architecture:** Deux modules indépendants. Module 1 : modifications `app.py` + `index.html` + `style.css` pour les filtres et cards. Module 2 : refactor anti-coloc dans `AbstractScraper` + ajout de 3 nouveaux scrapers enregistrés dans `__init__.py`.

**Tech Stack:** Flask, SQLAlchemy, BeautifulSoup, requests, ScraperAPI, pytest, CSS vanilla

**Spec :** `docs/superpowers/specs/2026-03-12-ameliorations-ui-scrapers-design.md`

---

## Structure des fichiers

| Fichier | Action | Responsabilité |
|---------|--------|----------------|
| `app.py` | Modifier | Ajouter params GET `departement`/`source`, passer `sources_dispo` au template |
| `static/style.css` | Modifier | Remplacer `.annonce` par grid `.cards-grid` + `.card`, ajouter `.checkbox-label` |
| `templates/index.html` | Modifier | Remplacer liste annonces par cards, ajouter filtres département + source |
| `tests/test_routes.py` | Modifier | Tests des nouveaux filtres departement et source |
| `scrapers/base.py` | Modifier | Ajouter `COLOC_KEYWORDS` + méthode `est_colocation()` |
| `scrapers/pap.py` | Modifier | Remplacer logique anti-coloc locale par `self.est_colocation()` |
| `scrapers/bienici.py` | Créer | Scraper BienIci (si server-rendered) |
| `scrapers/laforet.py` | Créer | Scraper Laforêt (si server-rendered) |
| `scrapers/century21.py` | Créer | Scraper Century21 (si server-rendered) |
| `scrapers/__init__.py` | Modifier | Enregistrer les nouveaux scrapers validés |
| `tests/test_base.py` | Créer | Tests `est_colocation()` |
| `tests/test_bienici.py` | Créer | Tests `parse()` BienIci (si implémenté) |
| `tests/test_laforet.py` | Créer | Tests `parse()` Laforêt (si implémenté) |
| `tests/test_century21.py` | Créer | Tests `parse()` Century21 (si implémenté) |
| `fixtures/bienici_sample.html` | Créer | HTML réel de BienIci pour les tests |
| `fixtures/laforet_sample.html` | Créer | HTML réel de Laforêt pour les tests |
| `fixtures/century21_sample.html` | Créer | HTML réel de Century21 pour les tests |

---

## Chunk 1 : UI — Filtres et Cards

### Task 1 : Filtres département et source (backend)

**Files:**
- Modify: `app.py` (route `/`, lignes du bloc filtres et du `render_template`)
- Modify: `tests/test_routes.py`

- [ ] **Step 1 : Écrire les tests des nouveaux filtres**

Ajouter à la fin de `tests/test_routes.py` :

```python
def test_filtre_departement(client, db_session):
    from models import Annonce
    db_session.add(Annonce(url="https://x.fr/1", titre="T", prix=800, ville="Paris", departement="75", source="pap"))
    db_session.add(Annonce(url="https://x.fr/2", titre="T", prix=800, ville="Créteil", departement="94", source="pap"))
    db_session.commit()
    resp = client.get("/?departement=75")
    assert resp.status_code == 200
    assert "Paris".encode() in resp.data
    assert "Créteil".encode() not in resp.data


def test_filtre_source(client, db_session):
    from models import Annonce
    db_session.add(Annonce(url="https://x.fr/3", titre="T", prix=700, ville="Montreuil", departement="93", source="bienici"))
    db_session.add(Annonce(url="https://x.fr/4", titre="T", prix=700, ville="Vincennes", departement="94", source="pap"))
    db_session.commit()
    resp = client.get("/?source=bienici")
    assert resp.status_code == 200
    assert "Montreuil".encode() in resp.data
    assert "Vincennes".encode() not in resp.data


def test_filtre_multi_departement(client, db_session):
    from models import Annonce
    db_session.add(Annonce(url="https://x.fr/5", titre="T", prix=800, ville="Paris", departement="75", source="pap"))
    db_session.add(Annonce(url="https://x.fr/6", titre="T", prix=800, ville="Nanterre", departement="92", source="pap"))
    db_session.add(Annonce(url="https://x.fr/7", titre="T", prix=800, ville="Bobigny", departement="93", source="pap"))
    db_session.commit()
    resp = client.get("/?departement=75&departement=92")
    assert "Paris".encode() in resp.data
    assert "Nanterre".encode() in resp.data
    assert "Bobigny".encode() not in resp.data


def test_sans_filtre_retourne_tout(client, db_session):
    from models import Annonce
    db_session.add(Annonce(url="https://x.fr/8", titre="T", prix=800, ville="Paris", departement="75", source="pap"))
    db_session.add(Annonce(url="https://x.fr/9", titre="T", prix=800, ville="Créteil", departement="94", source="bienici"))
    db_session.commit()
    resp = client.get("/")
    assert "Paris".encode() in resp.data
    assert "Créteil".encode() in resp.data
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```bash
cd "chemin/vers/rech appart"
pytest tests/test_routes.py -v -k "filtre_departement or filtre_source or multi_departement or sans_filtre"
```

Attendu : 4 tests FAILED (KeyError ou assertion échoue — les filtres n'existent pas encore)

- [ ] **Step 3 : Modifier `app.py` — route `/`**

Dans la route `/`, remplacer le bloc de filtres existant par ceci :

```python
@app.route("/")
def index():
    ville = request.args.get("ville", "")
    prix_max = request.args.get("prix_max", type=int)
    surface_min = request.args.get("surface_min", type=int)
    departements = request.args.getlist("departement")
    sources = request.args.getlist("source")

    query = Annonce.query.order_by(Annonce.date_scrape.desc())
    if ville:
        query = query.filter(Annonce.ville.ilike(f"%{ville}%"))
    if prix_max:
        query = query.filter(Annonce.prix <= prix_max)
    if surface_min:
        query = query.filter(Annonce.surface >= surface_min)
    if departements:
        query = query.filter(Annonce.departement.in_(departements))
    if sources:
        query = query.filter(Annonce.source.in_(sources))

    annonces = query.limit(100).all()
    villes = [v[0] for v in db.session.query(Annonce.ville).distinct().all() if v[0]]
    sources_dispo = [s[0] for s in db.session.query(Annonce.source).distinct().all() if s[0]]

    return render_template(
        "index.html",
        annonces=annonces,
        villes=villes,
        ville=ville,
        prix_max=prix_max,
        surface_min=surface_min,
        departements=departements,
        sources=sources,
        sources_dispo=sources_dispo,
    )
```

- [ ] **Step 4 : Relancer les tests**

```bash
pytest tests/test_routes.py -v
```

Attendu : tous les tests PASSED (y compris les 3 anciens)

- [ ] **Step 5 : Commit**

```bash
git add app.py tests/test_routes.py
git commit -m "feat: filtres departement et source dans la route principale"
```

---

### Task 2 : Cards grid (CSS)

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1 : Remplacer le style `.annonce` par la grille de cards**

Dans `static/style.css`, remplacer la ligne `.annonce { ... }` et toutes les règles `.annonce-*` par :

```css
.cards-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
}

@media (max-width: 700px) {
    .cards-grid { grid-template-columns: 1fr; }
}

.card {
    background: white;
    border-radius: 10px;
    padding: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,.1);
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.card-titre a {
    font-size: .95rem;
    font-weight: 600;
    color: #2c3e50;
    text-decoration: none;
    line-height: 1.35;
}

.card-titre a:hover { text-decoration: underline; }

.card-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 2px; }

.card-prix {
    font-size: 1.4rem;
    font-weight: 700;
    color: #27ae60;
}

.card-meta {
    font-size: .83rem;
    color: #777;
}

.card-footer {
    font-size: .76rem;
    color: #bbb;
    margin-top: 4px;
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: .83rem;
    color: #555;
    margin-bottom: 5px;
    cursor: pointer;
}

.checkbox-label input { width: auto; }
```

- [ ] **Step 2 : Commit**

```bash
git add static/style.css
git commit -m "feat: css cards grid remplace liste annonces"
```

---

### Task 3 : Cards grid + nouveaux filtres (template)

**Files:**
- Modify: `templates/index.html`

- [ ] **Step 1 : Remplacer la section annonces par la grille de cards**

Dans `templates/index.html`, remplacer le bloc `{% if annonces %}...{% endif %}` (section main) par :

```html
<p class="count">{{ annonces|length }} annonce(s) trouvée(s)</p>

{% if annonces %}
  <div class="cards-grid">
    {% for a in annonces %}
    <div class="card">
      <div>
        <div class="card-badges">
          {% if a.est_nouvelle %}<span class="badge">Nouveau</span>{% endif %}
          <span class="badge badge-source">{{ a.source }}</span>
        </div>
        <div class="card-titre">
          <a href="{{ a.url }}" target="_blank" rel="noopener">{{ a.titre }}</a>
        </div>
      </div>
      <div class="card-prix">{{ a.prix }}€ CC</div>
      <div class="card-meta">
        {% if a.surface %}📐 {{ a.surface }}m²&nbsp; {% endif %}
        {% if a.ville %}📍 {{ a.ville }}{% if a.departement %} ({{ a.departement }}){% endif %}{% endif %}
      </div>
      <div class="card-footer">{{ a.date_scrape.strftime('%d/%m %H:%M') }}</div>
    </div>
    {% endfor %}
  </div>
{% else %}
  <div class="empty">
    <p>Aucune annonce trouvée.</p>
    <p style="margin-top:8px;font-size:.85rem">Essaie <a href="/scrape-now">de lancer un scraping manuel</a>.</p>
  </div>
{% endif %}
```

- [ ] **Step 2 : Ajouter les filtres département et source dans la sidebar**

Dans `templates/index.html`, dans la sidebar (`<div class="card-filtres">`), ajouter après le groupe `surface_min` et avant le bouton Filtrer.

Note : les départements sont **hardcodés** (75/92/93/94) car le scope du projet est limité à la petite couronne IDF — ce sont les 4 seuls départements scrapés. Les sources sont dynamiques car elles dépendent de quels scrapers sont actifs.

```html
<div class="form-group">
  <label>Département</label>
  {% for dept, nom in [("75","Paris"),("92","Hauts-de-Seine"),("93","Seine-Saint-Denis"),("94","Val-de-Marne")] %}
  <label class="checkbox-label">
    <input type="checkbox" name="departement" value="{{ dept }}"
           {% if dept in departements %}checked{% endif %}>
    {{ dept }} – {{ nom }}
  </label>
  {% endfor %}
</div>

{% if sources_dispo %}
<div class="form-group">
  <label>Source</label>
  {% for s in sources_dispo %}
  <label class="checkbox-label">
    <input type="checkbox" name="source" value="{{ s }}"
           {% if s in sources %}checked{% endif %}>
    {{ s }}
  </label>
  {% endfor %}
</div>
{% endif %}
```

- [ ] **Step 3 : Tester que la page s'affiche sans erreur**

```bash
pytest tests/test_routes.py -v
```

Attendu : tous les tests PASSED

- [ ] **Step 4 : Vérification visuelle en local**

```bash
python app.py
```

Ouvrir `http://localhost:5000` et vérifier :
- Les annonces s'affichent en grille 2 colonnes
- Les filtres département et source sont visibles dans la sidebar
- Les filtres fonctionnent (cocher 75, filtrer, vérifier résultat)

- [ ] **Step 5 : Commit**

```bash
git add templates/index.html
git commit -m "feat: cards grid et filtres departement/source dans le template"
```

---

## Chunk 2 : Scrapers — Anti-coloc + Nouvelles sources

### Task 4 : Filtre anti-coloc mutualisé dans AbstractScraper

**Files:**
- Modify: `scrapers/base.py`
- Modify: `scrapers/pap.py`
- Create: `tests/test_base.py`

- [ ] **Step 1 : Écrire les tests pour `est_colocation()`**

Créer `tests/test_base.py` :

```python
from scrapers.base import AbstractScraper


class ConcreteScraper(AbstractScraper):
    """Implémentation minimale pour tester AbstractScraper."""
    url = "http://example.com"

    def fetch_html(self, url: str) -> str:
        return ""

    def parse(self, html: str) -> list:
        return []


def test_est_colocation_detecte_colocation():
    s = ConcreteScraper()
    assert s.est_colocation("Colocation 2 chambres Paris 15") is True


def test_est_colocation_detecte_coloc():
    s = ConcreteScraper()
    assert s.est_colocation("Coloc sympa Vincennes") is True


def test_est_colocation_detecte_chambre_chez():
    s = ConcreteScraper()
    assert s.est_colocation("Chambre chez habitant CDG") is True


def test_est_colocation_detecte_chambre_en():
    s = ConcreteScraper()
    assert s.est_colocation("Chambre en colocation Montreuil") is True


def test_est_colocation_laisse_passer_t2():
    s = ConcreteScraper()
    assert s.est_colocation("T2 lumineux Paris 15e 850€") is False


def test_est_colocation_insensible_casse():
    s = ConcreteScraper()
    assert s.est_colocation("COLOCATION Paris") is True
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_base.py -v
```

Attendu : AttributeError — `est_colocation` n'existe pas encore

- [ ] **Step 3 : Ajouter `est_colocation()` dans `scrapers/base.py`**

```python
from abc import ABC, abstractmethod
from typing import List, Dict


class AbstractScraper(ABC):
    COLOC_KEYWORDS = ("colocation", "coloc", "chambre chez", "chambre en ")

    @abstractmethod
    def fetch_html(self, url: str) -> str:
        pass

    @abstractmethod
    def parse(self, html: str) -> List[Dict]:
        pass

    def scrape(self) -> List[Dict]:
        html = self.fetch_html(self.url)
        return self.parse(html)

    def est_colocation(self, titre: str) -> bool:
        """Retourne True si le titre indique une colocation à exclure."""
        titre_lower = titre.lower()
        return any(kw in titre_lower for kw in self.COLOC_KEYWORDS)
```

- [ ] **Step 4 : Mettre à jour `scrapers/pap.py`**

Dans `scrapers/pap.py`, supprimer la constante locale :
```python
# Supprimer cette ligne :
COLOC_KEYWORDS = ("colocation", "coloc", "chambre chez", "chambre en ")
```

Et remplacer le bloc de filtre :
```python
# Remplacer :
if any(kw in title_text for kw in COLOC_KEYWORDS):
    continue

# Par :
if self.est_colocation(title_text):
    continue
```

- [ ] **Step 5 : Lancer tous les tests**

```bash
pytest tests/ -v
```

Attendu : tous les tests existants PASSED + 6 nouveaux tests PASSED

- [ ] **Step 6 : Commit**

```bash
git add scrapers/base.py scrapers/pap.py tests/test_base.py
git commit -m "refactor: mutualisé est_colocation() dans AbstractScraper"
```

---

### Task 5 : Scraper BienIci

**Files:**
- Create: `fixtures/bienici_sample.html`
- Create: `scrapers/bienici.py`
- Create: `tests/test_bienici.py`
- Modify: `scrapers/__init__.py`

- [ ] **Step 1 : Découverte — vérifier si BienIci est server-rendered**

Exécuter ce script Python depuis la racine du projet :

```python
import os, requests

api_key = os.environ.get("SCRAPERAPI_KEY", "")
url = "https://www.bienici.com/recherche/location/ile-de-france?surface.min=20&prix.max=1500&typeBien=appartement&nb-pieces.min=2&nb-pieces.max=2"

if api_key:
    proxy = f"http://api.scraperapi.com?api_key={api_key}&url={url}&country_code=fr"
    r = requests.get(proxy, timeout=60)
else:
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)

with open("fixtures/bienici_sample.html", "w", encoding="utf-8") as f:
    f.write(r.text)

print(f"Statut: {r.status_code} — {len(r.text)} caractères")
print("Mot-clé 'annonce' présent:", "annonce" in r.text.lower())
print("Mot-clé 'loyer' présent:", "loyer" in r.text.lower())
```

Attendu : si `annonce` ou `loyer` est dans le HTML brut → server-rendered → continuer.
Si le HTML contient uniquement du JavaScript (fichiers `.js`, peu de texte) → SPA → aller directement au Step 7 (SKIPPED).

- [ ] **Step 2 : Inspecter le HTML sauvegardé**

Ouvrir `fixtures/bienici_sample.html` dans un éditeur ou navigateur.
Identifier :
- Le sélecteur CSS du conteneur d'une annonce (ex: `div.vue-carte-annonce`)
- Le sélecteur du lien titre
- Le sélecteur du prix
- Le sélecteur de la surface
- Le sélecteur de la ville/localisation

Noter ces sélecteurs — ils seront utilisés dans les steps suivants.

- [ ] **Step 3 : Écrire le test de parsing**

Créer `tests/test_bienici.py` en adaptant les sélecteurs découverts :

```python
from pathlib import Path
from scrapers.bienici import BienIciScraper

FIXTURE = Path("fixtures/bienici_sample.html").read_text(encoding="utf-8")


def test_bienici_parse_retourne_des_annonces():
    scraper = BienIciScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) > 0


def test_bienici_annonce_a_les_champs_requis():
    scraper = BienIciScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert "url" in a
        assert "titre" in a
        assert "source" in a
        assert a["source"] == "bienici"


def test_bienici_urls_sont_absolues():
    scraper = BienIciScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["url"].startswith("https://"), f"URL invalide: {a['url']}"


def test_bienici_pas_de_coloc():
    scraper = BienIciScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert not scraper.est_colocation(a["titre"]), f"Coloc non filtrée: {a['titre']}"
```

- [ ] **Step 4 : Vérifier que les tests échouent**

```bash
pytest tests/test_bienici.py -v
```

Attendu : ImportError — `scrapers.bienici` n'existe pas encore

- [ ] **Step 5 : Créer `scrapers/bienici.py`**

Implémenter en utilisant les sélecteurs découverts au Step 2. Structure de base :

```python
import os
import re
import requests
from typing import List, Dict
from bs4 import BeautifulSoup
from .base import AbstractScraper

BASE_URL = "https://www.bienici.com"
SEARCH_URL = (
    "https://www.bienici.com/recherche/location/ile-de-france"
    "?surface.min=20&prix.max=1500&typeBien=appartement&nb-pieces.min=2&nb-pieces.max=2"
)


class BienIciScraper(AbstractScraper):
    def __init__(self, url: str = SEARCH_URL):
        self.url = url

    def fetch_html(self, url: str) -> str:
        api_key = os.environ.get("SCRAPERAPI_KEY", "")
        if api_key:
            proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={url}&country_code=fr"
            response = requests.get(proxy_url, timeout=60)
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "fr-FR,fr;q=0.9",
            }
            response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")
        annonces = []

        # Adapter SELECTEUR_ITEM, SELECTEUR_LIEN, SELECTEUR_PRIX,
        # SELECTEUR_VILLE, SELECTEUR_SURFACE avec les sélecteurs découverts
        items = soup.select("SELECTEUR_ITEM")  # À remplacer

        for item in items:
            link = item.select_one("SELECTEUR_LIEN")  # À remplacer
            if not link:
                continue

            titre = link.get_text(strip=True)
            if self.est_colocation(titre):
                continue

            href = link.get("href", "").strip()
            if not href:
                continue
            url = href if href.startswith("http") else BASE_URL + href

            # Prix (adapter le sélecteur)
            prix_el = item.select_one("SELECTEUR_PRIX")  # À remplacer
            prix = None
            if prix_el:
                digits = re.sub(r"[^\d]", "", prix_el.get_text().replace("\u00a0", ""))
                if digits:
                    prix = int(digits)

            # Ville et département (adapter le sélecteur)
            ville_el = item.select_one("SELECTEUR_VILLE")  # À remplacer
            ville_raw = ville_el.get_text(strip=True) if ville_el else ""
            dept_match = re.search(r"\b(75|92|93|94)\b", ville_raw)
            departement = dept_match.group(1) if dept_match else None
            ville = re.sub(r"\s*\(?\d+\)?.*$", "", ville_raw).strip()

            # Surface (adapter le sélecteur)
            surface_el = item.select_one("SELECTEUR_SURFACE")  # À remplacer
            surface = None
            if surface_el:
                m = re.search(r"([\d,\.]+)\s*m²", surface_el.get_text())
                if m:
                    try:
                        surface = int(float(m.group(1).replace(",", ".")))
                    except ValueError:
                        pass

            annonces.append({
                "url": url,
                "titre": titre,
                "prix": prix,
                "surface": surface,
                "ville": ville or None,
                "departement": departement,
                "source": "bienici",
            })

        return annonces
```

- [ ] **Step 6 : Relancer les tests**

```bash
pytest tests/test_bienici.py -v
```

Attendu : 4 tests PASSED

- [ ] **Step 7 (si server-rendered) : Enregistrer dans `scrapers/__init__.py`**

Ajouter après les imports PAP existants :

```python
from .bienici import BienIciScraper

def run_all_scrapers():
    results = []

    # PAP (code existant)
    pap = PapScraper()
    for url in PAP_PAGES:
        try:
            html = pap.fetch_html(url)
            results.extend(pap.parse(html))
        except Exception as e:
            logger.error(f"Erreur PAP {url}: {e}")

    # BienIci
    bienici = BienIciScraper()
    try:
        html = bienici.fetch_html(bienici.url)
        results.extend(bienici.parse(html))
        print("BienIci: OK", flush=True)
    except Exception as e:
        logger.error(f"Erreur BienIci: {e}")
        print(f"SCRAPER ERROR BienIci: {e}", flush=True)

    return results
```

**Si SPA/inaccessible :** ne pas créer `scrapers/bienici.py`. Dans `scrapers/__init__.py`, ajouter un commentaire :
```python
# BienIci : écarté — site SPA, HTML non disponible sans JavaScript
```

- [ ] **Step 8 : Lancer tous les tests**

```bash
pytest tests/ -v
```

Attendu : tous les tests PASSED

- [ ] **Step 9 : Commit**

```bash
git add scrapers/bienici.py tests/test_bienici.py fixtures/bienici_sample.html scrapers/__init__.py
git commit -m "feat: scraper BienIci"
# ou si écarté :
git commit -m "chore: BienIci ecarté (SPA)"
```

---

### Task 6 : Scraper Laforêt

**Files:**
- Create: `fixtures/laforet_sample.html`
- Create: `scrapers/laforet.py`
- Create: `tests/test_laforet.py`
- Modify: `scrapers/__init__.py`

Suivre exactement le même processus que Task 5 (BienIci), avec :

- **URL cible à tester :** `https://www.laforet.com/annonces/location/appartement/ile-de-france/?type_de_bien=appartement&nombre_de_pieces=2`
- **Source value :** `"laforet"`
- **Nom de classe :** `LaforetScraper`
- **Fixture :** `fixtures/laforet_sample.html`

Appliquer Steps 1→9 de Task 5 en adaptant ces valeurs.

Si server-rendered, ajouter `LaforetScraper` à `run_all_scrapers()` dans `scrapers/__init__.py` après BienIci (ou après PAP si BienIci écarté).

---

### Task 7 : Scraper Century21

**Files:**
- Create: `fixtures/century21_sample.html`
- Create: `scrapers/century21.py`
- Create: `tests/test_century21.py`
- Modify: `scrapers/__init__.py`

Suivre exactement le même processus que Task 5 (BienIci), avec :

- **URL cible à tester :** `https://www.century21.fr/annonces/locations/?types=2&localisation=ile-de-france&nb_pieces_min=2&nb_pieces_max=2`
- **Source value :** `"century21"`
- **Nom de classe :** `Century21Scraper`
- **Fixture :** `fixtures/century21_sample.html`

Appliquer Steps 1→9 de Task 5 en adaptant ces valeurs.

---

## Récapitulatif des commandes

```bash
# Tests
pytest tests/ -v

# Lancer en local
python app.py
# puis ouvrir http://localhost:5000

# Vérifier le scraping
curl http://localhost:5000/scrape-now
```
