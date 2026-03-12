# AppartSearch IDF — Améliorations UI + Scrapers

**Date :** 2026-03-12
**Scope :** Redesign interface (cards, filtres département/source) + ajout scrapers BienIci, Laforêt, Century21

---

## Contexte

Le site tourne en production sur Render.com. Il scrape PAP.fr toutes les 4h et envoie des alertes email. L'interface est fonctionnelle mais brute (liste dense, filtres limités). Une seule source d'annonces (PAP) réduit le volume disponible.

**Objectifs :**
- Interface plus lisible : cards aérées, prix en évidence
- Filtres enrichis : département (75/92/93/94) + source
- Nouvelles sources : BienIci, Laforêt, Century21

---

## Architecture globale

Aucun changement de schéma BDD. Les champs `departement` et `source` existent déjà dans le modèle `Annonce`. Les deux modules (UI et scrapers) sont indépendants et peuvent être développés en parallèle.

---

## Module 1 — Redesign UI

### Cards en grille

Remplacement de la liste `.annonce` par une grille de cards 2 colonnes (desktop) / 1 colonne (mobile).

**Contenu de chaque card :**
- En-tête : titre (lien cliquable), badges "Nouveau" + source (PAP, BienIci, etc.)
- Corps : prix affiché en grand (couleur d'accentuation), surface + ville + département
- Pied : date de scrape, discrète

**CSS :** `box-shadow` léger, `border-radius`, espacement généreux entre cards. Palette sobre, cohérente avec l'existant.

### Filtres enrichis

Deux nouveaux filtres ajoutés dans la sidebar existante :

**Département** — cases à cocher fixes : 75 (Paris), 92 (Hauts-de-Seine), 93 (Seine-Saint-Denis), 94 (Val-de-Marne). Plusieurs sélections possibles via paramètre GET `departement` répété.
- Aucune case cochée = pas de filtre département (toutes les annonces)
- Cases cochées = `WHERE departement IN (...)`

**Source** — cases à cocher dynamiques : `SELECT DISTINCT source FROM annonces` au chargement de chaque page. Pas de mise en cache. Si une source n'a aucune annonce en base, elle n'apparaît pas dans le filtre. Paramètre GET `source` répété.
- Aucune case cochée = pas de filtre source (toutes les sources)
- Cases cochées = `WHERE source IN (...)`

### Modifications backend (app.py)

Route `/` : deux nouveaux paramètres GET récupérés via `request.args.getlist(...)` :
```python
departements = request.args.getlist("departement")   # ex: ["75", "92"]
sources = request.args.getlist("source")             # ex: ["pap", "bienici"]

if departements:
    query = query.filter(Annonce.departement.in_(departements))
if sources:
    query = query.filter(Annonce.source.in_(sources))
```

La liste des sources disponibles est passée au template :
```python
sources_dispo = [s[0] for s in db.session.query(Annonce.source).distinct().all() if s[0]]
```

Aucune autre modification de `app.py`.

---

## Module 2 — Nouveaux scrapers

### AbstractScraper (existant, `scrapers/base.py`)

```python
class AbstractScraper(ABC):
    url: str                                    # URL de recherche, définie dans chaque sous-classe
    def fetch_html(self, url: str) -> str: ...  # à implémenter
    def parse(self, html: str) -> List[Dict]: ...  # à implémenter
    def scrape(self) -> List[Dict]:             # appelle fetch_html(self.url) puis parse()
```

### Champs attendus par `run_all_scrapers()` (modèle `Annonce`)

Chaque `parse()` retourne une liste de dicts avec ces clés :

| Champ | Type | Obligatoire | Notes |
|-------|------|-------------|-------|
| `url` | str | ✅ | URL absolue, unique en base (déduplication) |
| `titre` | str | ✅ | Texte libre |
| `prix` | int | ✅ si disponible | `None` si absent |
| `surface` | int | non | `None` si absent |
| `ville` | str | non | `None` si absent |
| `departement` | str | non | `"75"`, `"92"`, `"93"`, `"94"` |
| `source` | str | ✅ | `"bienici"`, `"laforet"`, `"century21"` |

### Déduplication

Gérée dans `app.py` → `scrape_and_notify()` :
```python
if Annonce.query.filter_by(url=data["url"]).first():
    continue  # annonce déjà en base, ignorée
```
L'URL est donc la clé de déduplication. Même annonce présente sur BienIci et PAP = deux entrées distinctes (URLs différentes). Acceptable.

### Filtre anti-coloc mutualisé

Méthode `est_colocation(titre: str) -> bool` déplacée de `PapScraper` vers `AbstractScraper` :
```python
COLOC_KEYWORDS = ("colocation", "coloc", "chambre chez", "chambre en ")

def est_colocation(self, titre: str) -> bool:
    return any(kw in titre.lower() for kw in self.COLOC_KEYWORDS)
```
Chaque `parse()` appelle `self.est_colocation(titre)` avant d'ajouter une annonce.

### BienIci (`scrapers/bienici.py`)

- **Statut :** à explorer — BienIci a été racheté par le groupe SeLoger. Le site bienici.com existe toujours mais peut rediriger ou être rendu en SPA.
- **Action à l'implémentation :** inspecter manuellement `https://www.bienici.com/recherche/location` (T2, IDF, ≤ 1500€) et vérifier si le HTML des annonces est présent dans la réponse brute (sans JS). Si server-rendered : implémenter. Si SPA : scraper écarté et marqué `SKIPPED` dans `__init__.py`.
- **Sélecteurs :** à déterminer à l'implémentation via inspection HTML.
- **Source value :** `"bienici"`

### Laforêt (`scrapers/laforet.py`)

- **Statut :** à explorer — site traditionnel de franchise, probablement server-rendered.
- **Action à l'implémentation :** inspecter `https://www.laforet.com/annonces/location/` (filtres : appartement, T2, IDF). Vérifier présence du HTML des annonces dans la réponse brute.
- **Sélecteurs :** à déterminer à l'implémentation.
- **Volume attendu :** faible (agence locale).
- **Source value :** `"laforet"`

### Century21 (`scrapers/century21.py`)

- **Statut :** à explorer — même approche que Laforêt.
- **Action à l'implémentation :** inspecter `https://www.century21.fr/annonces/locations/` (filtres : appartement, IDF).
- **Sélecteurs :** à déterminer à l'implémentation.
- **Volume attendu :** faible.
- **Source value :** `"century21"`

### Enregistrement dans `scrapers/__init__.py`

Chaque scraper validé est ajouté à `run_all_scrapers()` avec gestion d'erreur identique à PAP (try/except, log). Les scrapers écartés (SPA) sont commentés avec la raison.

---

## Champs BDD

Aucun changement. Le modèle `Annonce` possède déjà :
- `source` (String 20) — valeur : `"pap"`, `"bienici"`, `"laforet"`, `"century21"`
- `departement` (String 3) — valeur : `"75"`, `"92"`, `"93"`, `"94"`

---

## Hors scope

- Carte géographique des annonces
- Système de favoris / annonces vues
- Nouvelle source Leboncoin (trop protégée)
- Modification du système d'alertes email
