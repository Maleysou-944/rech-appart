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

**Migration :** `db.create_all()` ne fait rien sur une table existante. Il faut ajouter la colonne manuellement au démarrage si elle n'existe pas encore :

```python
# Dans create_app(), après db.create_all() :
with app.app_context():
    from sqlalchemy import text
    try:
        db.session.execute(text("ALTER TABLE annonce ADD COLUMN images TEXT"))
        db.session.commit()
    except Exception:
        pass  # Colonne déjà présente — ignoré silencieusement
```

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

> **Stratégie de fallback :** Si `ad["images"]["urls"]` est vide ou absent, essayer dans l'ordre : `ad["images"]["small_url"]` (str → liste d'un élément), `ad["image_url"]` (str direct). Ajouter `logger.debug("LeBonCoin images keys: %s", list(raw_images.keys()))` pour diagnostiquer si aucune image n'est trouvée. Le chemin exact est à confirmer depuis un vrai HTML lors de l'implémentation — la fixture synthétique ne contient pas de clé `images`.

### ParuVendu (`scrapers/paruvendu.py`)

Dans `parse()`, sur chaque `item` :

```python
# Images — dans div.blocMedia, sauter les placeholders transparents
# Filtre : src doit contenir "media" (CDN réel) ET ne pas contenir "transparent"
images = []
bloc = item.select_one("div.blocMedia")
if bloc:
    imgs = bloc.find_all("img", src=True)
    for img in imgs:
        src = img.get("src", "")
        if src and src.startswith("http") and "transparent" not in src and "1x1" not in src:
            images.append(src)
        if len(images) >= 3:
            break
```

Les URLs d'images réelles ParuVendu contiennent `img.paruvendu.fr/media_ext/` tandis que le placeholder contient `transparent_1x1.png` — le double filtre `"transparent" not in src and "1x1" not in src` est suffisant.

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

Le JS carrousel est placé dans un `{% block scripts %}` en bas de `templates/index.html` (pas dans `base.html`) — il n'est chargé que sur la page index, pas globalement.

~20 lignes :
- Navigation manuelle uniquement (pas d'auto-play)
- Flèches prev/next masquées si 1 seule image
- Dots indicateurs cliquables
- Pas de bibliothèque externe

**Gestion des images cassées dans le carrousel :** si une image se charge avec erreur, le slide correspondant est masqué via `onerror` et le carrousel recalcule le nombre de slides visibles. Si toutes les images d'un carrousel sont cassées, le placeholder est affiché à la place. Ce comportement est documenté comme une limitation acceptable (les URLs d'images peuvent expirer si l'annonce est supprimée).

### Fichiers modifiés

| Fichier | Action |
|---|---|
| `models.py` | + colonne `images`, + `get_images()`, + `get_first_image()` |
| `scrapers/leboncoin.py` | extraire `images` depuis `__NEXT_DATA__` |
| `scrapers/paruvendu.py` | extraire `images` depuis `div.blocMedia` |
| `templates/index.html` | zone photo + HTML carrousel par card |
| `static/style.css` | styles carrousel + placeholder |
| `templates/index.html` | `{% block scripts %}` JS carrousel (bas de page, index seulement) |

## Gestion d'erreurs

- Image cassée (404) → masquée silencieusement via `onerror="this.style.display='none'"` sur les `<img>`
- `images` NULL en DB → `get_images()` retourne `[]` → placeholder affiché
- JSON invalide en DB → `get_images()` retourne `[]` → placeholder affiché

## Tests

- `tests/test_models.py` — tester `get_images()` et `get_first_image()` avec valeurs valides, None, JSON invalide
- `tests/test_leboncoin.py` — ajouter test `test_leboncoin_extrait_images()` : fixture avec images dans `__NEXT_DATA__`
- `tests/test_paruvendu.py` — ajouter test `test_paruvendu_extrait_images()` : fixture avec `div.blocMedia` réel
- Pas de test JS (vanilla, sans framework de test)
