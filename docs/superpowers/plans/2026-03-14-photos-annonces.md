# Photos Annonces avec Carrousel Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un carrousel de 2-3 photos par annonce sur les cards, avec un placeholder gris + icône maison quand aucune image n'est disponible.

**Architecture:** Nouvelle colonne `images` (JSON text) sur le modèle `Annonce`, migration SQLite par ALTER TABLE au démarrage. LeBonCoin extrait les images depuis `__NEXT_DATA__`, ParuVendu depuis `div.blocMedia`. PAP et Laforêt (lazy-load JS) affichent le placeholder. Le carrousel est un composant HTML/CSS/JS vanilla ~25 lignes.

**Tech Stack:** Python 3, Flask, SQLAlchemy (SQLite), BeautifulSoup, Jinja2, CSS vanilla, JS vanilla

**Spec:** `docs/superpowers/specs/2026-03-14-photos-annonces-design.md`

---

## File Map

| Fichier | Action | Responsabilité |
|---|---|---|
| `models.py` | Modifier | + colonne `images`, + `get_images()`, + `get_first_image()` |
| `app.py` | Modifier | + migration ALTER TABLE au démarrage |
| `scrapers/leboncoin.py` | Modifier | extraire images depuis `__NEXT_DATA__` JSON |
| `scrapers/paruvendu.py` | Modifier | extraire images depuis `div.blocMedia img` |
| `tests/test_models.py` | Modifier | + tests get_images / get_first_image |
| `tests/test_leboncoin.py` | Modifier | + test extraction images |
| `tests/test_paruvendu.py` | Modifier | + test extraction images |
| `fixtures/leboncoin_sample.html` | Modifier | + clé `images` dans __NEXT_DATA__ JSON |
| `templates/index.html` | Modifier | + zone carrousel par card + {% block scripts %} |
| `templates/base.html` | Modifier | + {% block scripts %}{% endblock %} avant </body> |
| `static/style.css` | Modifier | + styles carrousel + placeholder |

---

## Chunk 1: Backend — modèle, migration, scrapers

### Task 1: Modèle Annonce + migration SQLite

**Files:**
- Modify: `models.py`
- Modify: `app.py`
- Modify: `tests/test_models.py`

- [ ] **Step 1: Écrire les tests qui vont échouer**

Ajouter à la fin de `tests/test_models.py` :

```python
import json

def test_get_images_retourne_liste_vide_si_none():
    a = Annonce(url="https://x.fr/1", titre="T", prix=800, source="pap")
    assert a.get_images() == []

def test_get_images_retourne_liste_vide_si_json_invalide():
    a = Annonce(url="https://x.fr/2", titre="T", prix=800, source="pap")
    a.images = "pas du json"
    assert a.get_images() == []

def test_get_images_retourne_liste_urls():
    a = Annonce(url="https://x.fr/3", titre="T", prix=800, source="pap")
    a.images = json.dumps(["https://img1.fr/a.jpg", "https://img2.fr/b.jpg"])
    assert a.get_images() == ["https://img1.fr/a.jpg", "https://img2.fr/b.jpg"]

def test_get_first_image_retourne_none_si_pas_images():
    a = Annonce(url="https://x.fr/4", titre="T", prix=800, source="pap")
    assert a.get_first_image() is None

def test_get_first_image_retourne_premiere_url():
    a = Annonce(url="https://x.fr/5", titre="T", prix=800, source="pap")
    a.images = json.dumps(["https://img1.fr/a.jpg", "https://img2.fr/b.jpg"])
    assert a.get_first_image() == "https://img1.fr/a.jpg"
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
cd "C:/Users/mugiw/OneDrive/Bureau/projet/rech appart"
python -m pytest tests/test_models.py -v -k "get_images or get_first_image"
```

Résultat attendu : `AttributeError: 'Annonce' object has no attribute 'get_images'`

- [ ] **Step 3: Ajouter la colonne et les helpers dans `models.py`**

Ajouter `import json` en haut du fichier.

Ajouter dans la classe `Annonce`, après `date_scrape` :

```python
    images = db.Column(db.Text, nullable=True)
    # JSON list d'URLs : '["https://...", "https://..."]' ou None

    def get_images(self) -> list:
        """Retourne la liste des URLs d'images, [] si None ou JSON invalide."""
        if not self.images:
            return []
        try:
            return json.loads(self.images)
        except (json.JSONDecodeError, TypeError):
            return []

    def get_first_image(self):
        """Retourne la première URL d'image ou None."""
        imgs = self.get_images()
        return imgs[0] if imgs else None
```

- [ ] **Step 4: Ajouter la migration ALTER TABLE dans `app.py`**

Dans `create_app()`, remplacer :

```python
    with app.app_context():
        db.create_all()
```

Par :

```python
    with app.app_context():
        db.create_all()
        # Migration : ajouter la colonne images si absente (SQLite ne supporte pas IF NOT EXISTS)
        from sqlalchemy import text
        try:
            db.session.execute(text("ALTER TABLE annonces ADD COLUMN images TEXT"))
            db.session.commit()
        except Exception:
            pass  # Colonne déjà présente — ignoré silencieusement
```

- [ ] **Step 5: Vérifier que les tests passent**

```bash
python -m pytest tests/test_models.py -v
```

Résultat attendu : tous les tests `PASSED` (y compris les 3 existants)

- [ ] **Step 6: Commit**

```bash
git add models.py app.py tests/test_models.py
git commit -m "feat: colonne images sur Annonce + helpers get_images/get_first_image + migration SQLite"
```

---

### Task 2: Extraction images LeBonCoin

**Files:**
- Modify: `fixtures/leboncoin_sample.html`
- Modify: `tests/test_leboncoin.py`
- Modify: `scrapers/leboncoin.py`

- [ ] **Step 1: Mettre à jour la fixture pour inclure des images**

Dans `fixtures/leboncoin_sample.html`, dans le JSON `__NEXT_DATA__`, mettre à jour les deux premières annonces (Paris 75011 et Neuilly 92200) pour inclure une clé `images` :

```json
{
  "list_id": 2740000001,
  "subject": "Appartement T2 Paris 11e",
  "price": [950],
  "images": {
    "urls": [
      "https://img.leboncoin.fr/api/thumb/abc1.jpg",
      "https://img.leboncoin.fr/api/thumb/abc2.jpg",
      "https://img.leboncoin.fr/api/thumb/abc3.jpg"
    ]
  },
  "location": { "city": "Paris", "zipcode": "75011", "department_id": "75" },
  "attributes": [{"key": "square", "value": "35", "value_label": "35 m²"}]
},
{
  "list_id": 2740000002,
  "subject": "T2 Neuilly-sur-Seine calme",
  "price": [1200],
  "images": {
    "urls": [
      "https://img.leboncoin.fr/api/thumb/def1.jpg"
    ]
  },
  "location": { "city": "Neuilly-sur-Seine", "zipcode": "92200", "department_id": "92" },
  "attributes": [{"key": "square", "value": "45", "value_label": "45 m²"}]
}
```

Les annonces Versailles (78) et Colocation (75) n'ont pas de clé `images` — tester le cas sans images.

- [ ] **Step 2: Écrire le test d'extraction d'images**

Ajouter à la fin de `tests/test_leboncoin.py` :

```python
def test_leboncoin_extrait_images():
    """La 1re annonce (Paris) doit avoir 3 images, la 2e (Neuilly) 1 image."""
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    # Paris (list_id 2740000001) a 3 images
    paris = next(a for a in annonces if "Paris" in a["ville"])
    assert isinstance(paris["images"], str)  # JSON string
    import json
    imgs = json.loads(paris["images"])
    assert len(imgs) == 3
    assert all(u.startswith("https://") for u in imgs)

def test_leboncoin_images_none_si_absent():
    """Annonce sans clé images → images=None dans le résultat."""
    # La fixture a des annonces sans images (Versailles filtrée, mais la colocation n'a pas d'images)
    # On teste directement avec un HTML minimal
    scraper = LeBonCoinScraper()
    minimal_html = '''<html><script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"searchData":{"ads":[
      {"list_id":9001,"subject":"T2 Paris","price":[900],
       "location":{"city":"Paris","zipcode":"75001","department_id":"75"},
       "attributes":[]}
    ]}}}}
    </script></html>'''
    annonces = scraper.parse(minimal_html)
    assert len(annonces) == 1
    assert annonces[0]["images"] is None
```

- [ ] **Step 3: Vérifier que les tests échouent**

```bash
python -m pytest tests/test_leboncoin.py::test_leboncoin_extrait_images tests/test_leboncoin.py::test_leboncoin_images_none_si_absent -v
```

Résultat attendu : `KeyError: 'images'` ou `AssertionError`

- [ ] **Step 4: Modifier `scrapers/leboncoin.py` pour extraire les images**

Dans `parse()`, dans la boucle `for ad in ads`, après l'extraction de `surface` et avant `annonces.append(...)`, ajouter :

```python
                # Images — dans __NEXT_DATA__ ad["images"]["urls"]
                # Fallback : small_url (str) ou image_url (str direct)
                images = []
                raw_images = ad.get("images", {})
                if isinstance(raw_images, dict):
                    urls = raw_images.get("urls", [])
                    if urls and isinstance(urls, list):
                        images = [u for u in urls[:3] if u and u.startswith("http")]
                    elif not images:
                        small = raw_images.get("small_url", "")
                        if small and small.startswith("http"):
                            images = [small]
                elif isinstance(raw_images, str) and raw_images.startswith("http"):
                    images = [raw_images]
                if not images:
                    img_url = ad.get("image_url", "")
                    if img_url and img_url.startswith("http"):
                        images = [img_url]
                logger.debug("LeBonCoin images pour %s: %d trouvées", list_id, len(images))
```

Et dans `annonces.append(...)`, ajouter la clé `images` :

```python
                annonces.append({
                    "url": url,
                    "titre": titre,
                    "prix": prix,
                    "surface": surface,
                    "ville": ville,
                    "departement": departement,
                    "source": "leboncoin",
                    "images": json.dumps(images) if images else None,
                })
```

Ajouter `import json` en haut du fichier si pas déjà présent (il l'est déjà).

- [ ] **Step 5: Vérifier que tous les tests LeBonCoin passent**

```bash
python -m pytest tests/test_leboncoin.py -v
```

Résultat attendu : tous les tests `PASSED`

- [ ] **Step 6: Commit**

```bash
git add fixtures/leboncoin_sample.html scrapers/leboncoin.py tests/test_leboncoin.py
git commit -m "feat: extraction images LeBonCoin depuis __NEXT_DATA__"
```

---

### Task 3: Extraction images ParuVendu

**Files:**
- Modify: `tests/test_paruvendu.py`
- Modify: `scrapers/paruvendu.py`

La fixture `fixtures/paruvendu_sample.html` contient déjà de vraies images CDN dans `div.blocMedia` — pas besoin de la modifier.

- [ ] **Step 1: Écrire les tests d'extraction d'images**

Ajouter à la fin de `tests/test_paruvendu.py` :

```python
import json

def test_paruvendu_extrait_images():
    """Les annonces IDF de la fixture doivent avoir des images ou images=None."""
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) > 0
    # Toutes les annonces ont la clé images
    for a in annonces:
        assert "images" in a
        # images est soit None soit un JSON valide
        if a["images"] is not None:
            imgs = json.loads(a["images"])
            assert isinstance(imgs, list)
            assert len(imgs) <= 3
            assert all(u.startswith("https://") for u in imgs)

def test_paruvendu_images_pas_de_transparent():
    """Aucune image transparente (placeholder 1x1) ne doit être dans les résultats."""
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        if a["images"]:
            imgs = json.loads(a["images"])
            for url in imgs:
                assert "transparent" not in url
                assert "1x1" not in url
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
python -m pytest tests/test_paruvendu.py::test_paruvendu_extrait_images tests/test_paruvendu.py::test_paruvendu_images_pas_de_transparent -v
```

Résultat attendu : `KeyError: 'images'`

- [ ] **Step 3: Modifier `scrapers/paruvendu.py` pour extraire les images**

Ajouter `import json` en haut du fichier.

Dans `parse()`, dans la boucle `for item in items`, après l'extraction de `ville`/`departement` et avant le filtre IDF, ajouter :

```python
                # Images — div.blocMedia img, skip placeholders transparents
                images = []
                bloc = item.select_one("div.blocMedia")
                if bloc:
                    for img in bloc.find_all("img", src=True):
                        src = img.get("src", "")
                        if (src and src.startswith("http")
                                and "transparent" not in src
                                and "1x1" not in src):
                            images.append(src)
                        if len(images) >= 3:
                            break
```

Et dans `annonces.append(...)`, ajouter la clé `images` :

```python
                annonces.append({
                    "url": url,
                    "titre": titre,
                    "prix": prix,
                    "surface": surface,
                    "ville": ville,
                    "departement": departement,
                    "source": "paruvendu",
                    "images": json.dumps(images) if images else None,
                })
```

- [ ] **Step 4: Vérifier que tous les tests ParuVendu passent**

```bash
python -m pytest tests/test_paruvendu.py -v
```

Résultat attendu : tous les tests `PASSED`

- [ ] **Step 5: Lancer la suite complète**

```bash
python -m pytest tests/ -q
```

Résultat attendu : tous les tests passent.

- [ ] **Step 6: Commit**

```bash
git add scrapers/paruvendu.py tests/test_paruvendu.py
git commit -m "feat: extraction images ParuVendu depuis div.blocMedia"
```

---

## Chunk 2: Frontend — carrousel HTML/CSS/JS

### Task 4: CSS carrousel + placeholder

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Ajouter les styles à la fin de `static/style.css`**

```css
/* ── Carrousel photos ─────────────────────────────── */
.carousel {
  position: relative;
  height: 200px;
  overflow: hidden;
  background: #f0f0f0;
  border-radius: 8px 8px 0 0;
}

.carousel-track {
  display: flex;
  height: 100%;
  transition: transform 0.3s ease;
}

.carousel-img {
  flex: none;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.carousel-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(0,0,0,0.45);
  color: #fff;
  border: none;
  border-radius: 50%;
  width: 28px;
  height: 28px;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.carousel-btn-prev { left: 6px; }
.carousel-btn-next { right: 6px; }
.carousel-btn:hover { background: rgba(0,0,0,0.7); }

.carousel-dots {
  position: absolute;
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  gap: 5px;
  z-index: 2;
}

.carousel-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(255,255,255,0.5);
  cursor: pointer;
  transition: background 0.2s;
}

.carousel-dot.active { background: #fff; }

/* ── Placeholder (aucune image) ─────────────────────── */
.carousel-placeholder {
  height: 200px;
  background: #f0f0f0;
  border-radius: 8px 8px 0 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

- [ ] **Step 2: Vérifier visuellement en lançant l'appli en local**

```bash
cd "C:/Users/mugiw/OneDrive/Bureau/projet/rech appart"
python app.py
```

Ouvrir http://localhost:5000 — les cards doivent s'afficher (sans images encore, les placeholders apparaîtront après Task 5).

- [ ] **Step 3: Commit**

```bash
git add static/style.css
git commit -m "feat: styles CSS carrousel et placeholder photos"
```

---

### Task 5: Template HTML carrousel + bloc scripts

**Files:**
- Modify: `templates/base.html`
- Modify: `templates/index.html`

- [ ] **Step 1: Ajouter `{% block scripts %}` dans `base.html`**

`base.html` se termine actuellement par :
```html
  </div>
</body>
</html>
```

Remplacer ces 3 lignes par :
```html
  </div>
  {% block scripts %}{% endblock %}
</body>
</html>
```

> Le bloc est placé **après** `</div>` (fermeture de `.container`) et **avant** `</body>`, de façon à ce que le DOM soit chargé quand le JS s'exécute. Il n'y a pas d'autres scripts en bas de page dans `base.html` — les scripts existants (Google Analytics) sont dans `<head>`.

- [ ] **Step 2: Modifier `templates/index.html` pour ajouter les photos**

Dans la boucle `{% for a in annonces %}`, remplacer :

```html
    <div class="card">
      <div>
```

Par :

```html
    <div class="card">
      {% set imgs = a.get_images() %}
      {% if imgs %}
      <div class="carousel">
        <div class="carousel-track">
          {% for img_url in imgs %}
          <img class="carousel-img" src="{{ img_url }}" alt="Photo" loading="lazy"
               onerror="this.style.visibility='hidden'">
          {% endfor %}
          {# onerror : masque visuellement l'image cassée (slide reste dans le DOM).
             Le carrousel navigue normalement — slide vide = fond gris du .carousel.
             Limitation connue documentée dans la spec. #}
        </div>
        {% if imgs|length > 1 %}
        <button class="carousel-btn carousel-btn-prev">&#8249;</button>
        <button class="carousel-btn carousel-btn-next">&#8250;</button>
        <div class="carousel-dots">
          {% for _ in imgs %}
          <span class="carousel-dot {% if loop.first %}active{% endif %}"></span>
          {# Le premier dot a la classe 'active' dès le rendu Jinja — état initial correct sans JS #}
          {% endfor %}
        </div>
        {% endif %}
      </div>
      {% else %}
      <div class="carousel-placeholder">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#bbb" width="48" height="48">
          <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
        </svg>
      </div>
      {% endif %}
      <div>
```

- [ ] **Step 3: Ajouter le JS carrousel dans `{% block scripts %}`**

À la fin de `templates/index.html`, avant `{% endblock %}`, ajouter :

```html
{% block scripts %}
<script>
(function () {
  document.querySelectorAll('.carousel').forEach(function (c) {
    var track = c.querySelector('.carousel-track');
    var dots = c.querySelectorAll('.carousel-dot');
    var n = c.querySelectorAll('.carousel-img').length;
    var i = 0;

    function go(to) {
      i = ((to % n) + n) % n;
      track.style.transform = 'translateX(-' + (i * 100) + '%)';
      dots.forEach(function (d, j) { d.classList.toggle('active', j === i); });
    }

    var prev = c.querySelector('.carousel-btn-prev');
    var next = c.querySelector('.carousel-btn-next');
    if (prev) prev.addEventListener('click', function (e) { e.preventDefault(); go(i - 1); });
    if (next) next.addEventListener('click', function (e) { e.preventDefault(); go(i + 1); });
    dots.forEach(function (d, j) { d.addEventListener('click', function () { go(j); }); });
  });
})();
</script>
{% endblock %}
```

- [ ] **Step 4: Vérifier visuellement**

```bash
python app.py
```

Ouvrir http://localhost:5000. Les annonces LeBonCoin et ParuVendu doivent afficher un carrousel avec photos. Les annonces PAP et Laforêt affichent l'icône maison grise.

> Si la DB locale est vide ou sans images : lancer un scrape manuel via http://localhost:5000/scrape-now (si `SCRAPE_SECRET` n'est pas défini en local, ça passe sans token).

- [ ] **Step 5: Lancer la suite de tests**

```bash
python -m pytest tests/ -q
```

Résultat attendu : tous les tests passent (les templates ne sont pas testés unitairement).

- [ ] **Step 6: Commit**

```bash
git add templates/base.html templates/index.html
git commit -m "feat: carrousel photos dans les cards + placeholder SVG maison"
```

---

## Vérification finale

- [ ] **Lancer la suite complète une dernière fois**

```bash
python -m pytest tests/ -v
```

Tous les tests doivent passer.

- [ ] **Lancer un scrape manuel local pour voir les photos en vrai**

```bash
python app.py
# Dans un autre terminal ou navigateur :
# GET http://localhost:5000/scrape-now
```

Vérifier que :
- Les annonces LeBonCoin/ParuVendu affichent des photos (si images disponibles)
- Les annonces PAP/Laforêt affichent le placeholder maison
- Le carrousel fonctionne (flèches, dots) quand il y a plusieurs photos
- Les flèches/dots sont masqués quand il n'y a qu'une seule photo

- [ ] **Push sur GitHub pour déployer sur Render**

```bash
git push origin master
```
