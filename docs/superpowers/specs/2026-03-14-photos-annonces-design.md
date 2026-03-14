# Design — Photos des annonces avec carrousel

**Date :** 2026-03-14
**Projet :** AppartSearch IDF
**Statut :** Approuvé

## Contexte

Les cards d'annonces n'affichent actuellement aucune image. L'objectif est d'ajouter un carrousel de 2-3 photos par annonce pour rendre le site plus visuel, avec un placeholder gris + icône maison quand aucune image n'est disponible.

## Sources et disponibilité des images

| Source | Images disponibles | Méthode d'extraction |
|---|---|---|
| LeBonCoin | ✅ jusqu'à 3 | JSON `__NEXT_DATA__` → `ad["images"]["urls"][:3]` |
| ParuVendu | ✅ jusqu'à 3 | `div.blocMedia img[src]` (skip 1er transparent 1×1) |
| PAP.fr | ❌ | Lazy-load JS — placeholder uniquement |
| Laforêt | ❌ | Lazy-load JS — placeholder uniquement |

PAP et Laforêt chargent leurs images en JavaScript. Utiliser le mode JS rendering de ScraperAPI coûterait ~5× plus de crédits (hors budget free tier). Ces sources afficheront le placeholder.

## Modèle de données

### Nouveau champ `Annonce`

```python
images = db.Column(db.Text, nullable=True)
# Stocké comme JSON list : '["https://...", "https://..."]'
# None si pas d'images disponibles
```

`db.create_all()` au démarrage ajoute la colonne automatiquement (SQLite, pas de migration).

### Helpers sur le modèle

```python
def get_images(self) -> list[str]:
    """Retourne la liste des URLs d'images, [] si None ou invalide."""
    if not self.images:
        return []
    try:
        return json.loads(self.images)
    except (json.JSONDecodeError, TypeError):
        return []

def get_first_image(self) -> str | None:
    imgs = self.get_images()
    return imgs[0] if imgs else None
```

## Extraction des images par scraper

### LeBonCoin (`scrapers/leboncoin.py`)

Dans `parse()`, après extraction des champs existants :

```python
# Images — dans __NEXT_DATA__ ad["images"]["urls"]
images = []
raw_images = ad.get("images", {})
urls = raw_images.get("urls", []) if isinstance(raw_images, dict) else []
images = [u for u in urls[:3] if u and u.startswith("http")]
```

Stocker comme `json.dumps(images)` si `images` non vide, sinon `None`.

> **Note :** Le chemin exact (`images.urls`) est à confirmer depuis un vrai HTML LeBonCoin lors de l'implémentation. Alternatives possibles : `ad["images"]["small_url"]`, `ad["image_url"]`. Ajouter un `logger.debug` pour inspecter la structure si vide.

### ParuVendu (`scrapers/paruvendu.py`)

Dans `parse()`, sur chaque `item` :

```python
# Images — dans div.blocMedia, sauter le 1er (transparent 1×1)
images = []
bloc = item.select_one("div.blocMedia")
if bloc:
    imgs = bloc.find_all("img", src=True)
    for img in imgs:
        src = img.get("src", "")
        if src and "transparent" not in src and src.startswith("http"):
            images.append(src)
        if len(images) >= 3:
            break
```

## Frontend

### Layout card

```
┌─────────────────────────┐
│  [←]   📷 image   [→]  │  hauteur: 200px, object-fit: cover
│         • • •          │  indicateurs dots
├─────────────────────────┤
│  🆕  PAP                │
│  950€ CC · Paris        │  contenu existant inchangé
└─────────────────────────┘
```

### Placeholder (aucune image)

Fond `#f0f0f0`, icône maison en SVG inline centré verticalement. Hauteur identique (200px) pour que toutes les cards aient la même taille.

### Carrousel (JS vanilla)

~20 lignes dans un `<script>` en bas de `base.html` :
- Navigation manuelle uniquement (pas d'auto-play)
- Flèches prev/next masquées si 1 seule image
- Dots indicateurs cliquables
- Pas de bibliothèque externe

### Fichiers modifiés

| Fichier | Action |
|---|---|
| `models.py` | + colonne `images`, + `get_images()`, + `get_first_image()` |
| `scrapers/leboncoin.py` | extraire `images` depuis `__NEXT_DATA__` |
| `scrapers/paruvendu.py` | extraire `images` depuis `div.blocMedia` |
| `templates/index.html` | zone photo + HTML carrousel par card |
| `static/style.css` | styles carrousel + placeholder |
| `templates/base.html` | `<script>` JS carrousel (bas de page) |

## Gestion d'erreurs

- Image cassée (404) → masquée silencieusement via `onerror="this.style.display='none'"` sur les `<img>`
- `images` NULL en DB → `get_images()` retourne `[]` → placeholder affiché
- JSON invalide en DB → `get_images()` retourne `[]` → placeholder affiché

## Tests

- `tests/test_models.py` — tester `get_images()` et `get_first_image()` avec valeurs valides, None, JSON invalide
- `tests/test_leboncoin.py` — ajouter test `test_leboncoin_extrait_images()` : fixture avec images dans `__NEXT_DATA__`
- `tests/test_paruvendu.py` — ajouter test `test_paruvendu_extrait_images()` : fixture avec `div.blocMedia` réel
- Pas de test JS (vanilla, sans framework de test)
