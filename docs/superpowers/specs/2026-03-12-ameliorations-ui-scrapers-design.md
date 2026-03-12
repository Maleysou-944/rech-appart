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

**Département** — cases à cocher : 75 (Paris), 92 (Hauts-de-Seine), 93 (Seine-Saint-Denis), 94 (Val-de-Marne). Plusieurs sélections possibles (paramètre GET `departement` répété).

**Source** — cases à cocher dynamiques : liste des sources présentes en base. Paramètre GET `source` répété.

### Modifications backend (app.py)

Route `/` : deux nouveaux paramètres GET :
- `departement` (liste) → `filter(Annonce.departement.in_(...))`
- `source` (liste) → `filter(Annonce.source.in_(...))`

Aucune autre modification.

---

## Module 2 — Nouveaux scrapers

### Architecture existante conservée

Chaque nouveau scraper :
- Hérite de `AbstractScraper`
- Implémente `fetch_html(url)` et `parse(html)`
- Est enregistré dans `scrapers/__init__.py` → `run_all_scrapers()`

**Filtre anti-coloc mutualisé** : déplacé de `PapScraper` vers `AbstractScraper` (méthode `est_colocation(titre)`) pour bénéficier à tous les scrapers.

### BienIci (`scrapers/bienici.py`)

Agrégateur immobilier, potentiellement server-rendered. Cible : recherche T2 IDF ≤ 1500€.
- ScraperAPI en fallback si protection détectée
- ⚠️ À vérifier à l'implémentation : BienIci a été racheté par SeLoger group, accessibilité à confirmer
- Si inaccessible (SPA/redirect), scraper documenté comme non-disponible et ignoré

### Laforêt (`scrapers/laforet.py`)

Réseau de franchises, site server-rendered. Cible : location appartement T2 IDF.
- Volume attendu faible (agence locale)
- Même approche BeautifulSoup + ScraperAPI

### Century21 (`scrapers/century21.py`)

Même logique que Laforêt.
- Volume attendu faible
- Si le site utilise du JavaScript pour charger les résultats, scraper écarté

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
