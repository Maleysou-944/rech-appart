# AppartSearch IDF Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire un site Flask qui scrape PAP.fr et Logic-immo toutes les heures, affiche les T2 IDF ≤ 900€ CC, et envoie des alertes email pour les nouvelles annonces.

**Architecture:** Flask app avec SQLite via SQLAlchemy. Scrapers BeautifulSoup séparés par source. APScheduler lance les scrapers en arrière-plan. Templates Jinja2 pour le frontend.

**Tech Stack:** Python 3.11, Flask 3, SQLAlchemy 2, BeautifulSoup4, APScheduler 3, smtplib, Railway

---

## Structure des fichiers

```
appart-search/
├── app.py                    # Flask app, routes, scheduler init
├── config.py                 # Variables d'environnement
├── models.py                 # SQLAlchemy model Annonce
├── notifier.py               # Envoi email Gmail SMTP
├── scrapers/
│   ├── __init__.py           # run_all_scrapers()
│   ├── base.py               # Classe de base AbstractScraper
│   ├── pap.py                # Scraper PAP.fr
│   └── logicimmo.py          # Scraper Logic-immo.fr
├── templates/
│   ├── base.html             # Layout commun
│   └── index.html            # Liste annonces + filtres
├── static/
│   └── style.css             # Styles minimalistes
├── tests/
│   ├── conftest.py           # Fixtures pytest (app, db)
│   ├── test_models.py        # Tests modèle Annonce
│   ├── test_pap.py           # Tests scraper PAP avec fixture HTML
│   ├── test_logicimmo.py     # Tests scraper Logic-immo avec fixture HTML
│   ├── test_notifier.py      # Tests email (mock SMTP)
│   └── test_routes.py        # Tests routes Flask
├── fixtures/
│   ├── pap_sample.html       # HTML exemple de PAP.fr pour tests
│   └── logicimmo_sample.html # HTML exemple de Logic-immo pour tests
├── requirements.txt
├── Procfile                  # Railway: web process
├── railway.toml              # Config Railway
└── .env.example              # Variables d'environnement exemple
```

---

## Chunk 1: Setup et modèle de données

### Task 1: Initialisation du projet

**Files:**
- Create: `appart-search/requirements.txt`
- Create: `appart-search/config.py`
- Create: `appart-search/.env.example`
- Create: `appart-search/.gitignore`

- [ ] **Step 1: Créer requirements.txt**

```
flask==3.0.3
sqlalchemy==2.0.35
flask-sqlalchemy==3.1.1
beautifulsoup4==4.12.3
requests==2.32.3
apscheduler==3.10.4
pytest==8.3.3
pytest-flask==1.3.0
lxml==5.3.0
python-dotenv==1.0.1
gunicorn==23.0.0
```

- [ ] **Step 2: Créer config.py**

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-in-prod")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///annonces.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    EMAIL_DESTINATAIRE = os.environ.get("EMAIL_DESTINATAIRE", "")
    GMAIL_USER = os.environ.get("GMAIL_USER", "")
    GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "")
    SCRAPE_INTERVAL_MINUTES = int(os.environ.get("SCRAPE_INTERVAL_MINUTES", "60"))
    PRIX_MAX = int(os.environ.get("PRIX_MAX", "900"))
```

- [ ] **Step 3: Créer .env.example**

```
SECRET_KEY=change-me
DATABASE_URL=sqlite:///annonces.db
EMAIL_DESTINATAIRE=ton-email@gmail.com
GMAIL_USER=expéditeur@gmail.com
GMAIL_PASSWORD=mot-de-passe-app-gmail
SCRAPE_INTERVAL_MINUTES=60
PRIX_MAX=900
```

- [ ] **Step 4: Créer .gitignore**

```
.env
*.db
__pycache__/
*.pyc
.pytest_cache/
venv/
```

- [ ] **Step 5: Installer les dépendances**

```bash
cd appart-search
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt config.py .env.example .gitignore
git commit -m "feat: project setup and configuration"
```

---

### Task 2: Modèle de données

**Files:**
- Create: `appart-search/models.py`
- Create: `appart-search/tests/conftest.py`
- Create: `appart-search/tests/test_models.py`

- [ ] **Step 1: Écrire les tests du modèle**

`tests/test_models.py`:
```python
from models import Annonce
from datetime import datetime

def test_annonce_creation(db_session):
    annonce = Annonce(
        url="https://pap.fr/annonce/123",
        titre="T2 Créteil 42m²",
        prix=850,
        surface=42,
        ville="Créteil",
        departement="94",
        source="pap",
    )
    db_session.add(annonce)
    db_session.commit()
    found = db_session.get(Annonce, annonce.id)
    assert found.titre == "T2 Créteil 42m²"
    assert found.prix == 850

def test_annonce_url_unique(db_session):
    url = "https://pap.fr/annonce/456"
    db_session.add(Annonce(url=url, titre="A", prix=800, source="pap"))
    db_session.commit()
    db_session.add(Annonce(url=url, titre="B", prix=800, source="pap"))
    import pytest
    with pytest.raises(Exception):
        db_session.commit()

def test_annonce_est_nouvelle(db_session):
    annonce = Annonce(url="https://pap.fr/1", titre="T", prix=800, source="pap")
    assert annonce.est_nouvelle is True
```

- [ ] **Step 2: Créer conftest.py**

`tests/conftest.py`:
```python
import pytest
from app import create_app
from models import db as _db, Annonce

@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture
def db_session(app):
    with app.app_context():
        yield _db.session
```

- [ ] **Step 3: Vérifier que les tests échouent**

```bash
pytest tests/test_models.py -v
```
Expected: erreurs d'import (models.py n'existe pas encore)

- [ ] **Step 4: Créer models.py**

```python
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Annonce(db.Model):
    __tablename__ = "annonces"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), unique=True, nullable=False)
    titre = db.Column(db.String(200), nullable=False)
    prix = db.Column(db.Integer)
    surface = db.Column(db.Integer)
    ville = db.Column(db.String(100))
    departement = db.Column(db.String(3))
    source = db.Column(db.String(20), nullable=False)
    date_scrape = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def est_nouvelle(self):
        return (datetime.utcnow() - self.date_scrape) < timedelta(hours=24)

    def __repr__(self):
        return f"<Annonce {self.ville} {self.prix}€>"
```

- [ ] **Step 5: Créer app.py minimal (pour conftest)**

```python
from flask import Flask
from models import db
from config import Config

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    db.init_app(app)
    return app

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
```

- [ ] **Step 6: Lancer les tests**

```bash
pytest tests/test_models.py -v
```
Expected: 3 PASSED

- [ ] **Step 7: Commit**

```bash
git add models.py app.py tests/conftest.py tests/test_models.py
git commit -m "feat: Annonce model with SQLAlchemy"
```

---

## Chunk 2: Scrapers

### Task 3: Scraper PAP.fr

**Files:**
- Create: `appart-search/scrapers/__init__.py`
- Create: `appart-search/scrapers/base.py`
- Create: `appart-search/scrapers/pap.py`
- Create: `appart-search/fixtures/pap_sample.html`
- Create: `appart-search/tests/test_pap.py`

- [ ] **Step 1: Télécharger une page PAP.fr pour fixture**

Ouvrir dans le navigateur :
```
https://www.pap.fr/annonce/locations-appartement-t2-ile-de-france-g439-bu2p0?prix-max=900
```
Sauvegarder le HTML dans `fixtures/pap_sample.html` (Ctrl+S → "Page web, HTML seulement")

- [ ] **Step 2: Inspecter les sélecteurs CSS dans le navigateur**

Avec les DevTools (F12), identifier :
- Le conteneur de chaque annonce (probablement `.search-list-item` ou `article`)
- Le titre (probablement `h2 a` ou `.title`)
- Le prix (probablement `.price`)
- La surface (probablement dans la description)
- La ville

Noter les sélecteurs trouvés — ils seront utilisés dans pap.py.

- [ ] **Step 3: Créer scrapers/base.py**

```python
from abc import ABC, abstractmethod
from typing import List, Dict

class AbstractScraper(ABC):
    @abstractmethod
    def fetch_html(self, url: str) -> str:
        """Récupère le HTML d'une URL."""
        pass

    @abstractmethod
    def parse(self, html: str) -> List[Dict]:
        """Parse le HTML et retourne une liste de dicts d'annonces."""
        pass

    def scrape(self) -> List[Dict]:
        html = self.fetch_html(self.url)
        return self.parse(html)
```

- [ ] **Step 4: Écrire les tests du scraper PAP**

`tests/test_pap.py`:
```python
from pathlib import Path
from scrapers.pap import PapScraper

FIXTURE = Path("fixtures/pap_sample.html").read_text(encoding="utf-8")

def test_pap_parse_retourne_des_annonces():
    scraper = PapScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) > 0

def test_pap_annonce_a_les_champs_requis():
    scraper = PapScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert "url" in a
        assert "titre" in a
        assert "prix" in a
        assert "source" in a
        assert a["source"] == "pap"

def test_pap_prix_dans_budget():
    scraper = PapScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        if a["prix"]:
            assert a["prix"] <= 900
```

- [ ] **Step 5: Lancer les tests pour voir l'échec**

```bash
pytest tests/test_pap.py -v
```
Expected: ImportError

- [ ] **Step 6: Créer scrapers/pap.py**

```python
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from .base import AbstractScraper

PAP_URL = (
    "https://www.pap.fr/annonce/locations-appartement-t2-"
    "ile-de-france-g439-bu2p0?prix-max=900"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
}

class PapScraper(AbstractScraper):
    url = PAP_URL

    def fetch_html(self, url: str) -> str:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text

    def parse(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")
        annonces = []
        # ADAPTER CES SÉLECTEURS selon l'inspection DevTools (Step 2)
        for item in soup.select("article.search-list-item"):
            lien = item.select_one("a[href]")
            titre_el = item.select_one("h2")
            prix_el = item.select_one(".price")

            if not lien:
                continue

            url = "https://www.pap.fr" + lien["href"] if lien["href"].startswith("/") else lien["href"]
            titre = titre_el.get_text(strip=True) if titre_el else ""
            prix_text = prix_el.get_text(strip=True) if prix_el else ""
            prix = _extract_prix(prix_text)
            surface = _extract_surface(titre + " " + item.get_text())
            ville = _extract_ville(item.get_text())

            annonces.append({
                "url": url,
                "titre": titre,
                "prix": prix,
                "surface": surface,
                "ville": ville,
                "departement": _extract_dept(ville),
                "source": "pap",
            })
        return annonces


def _extract_prix(text: str):
    match = re.search(r"(\d[\d\s]*)\s*€", text.replace("\u00a0", " "))
    return int(match.group(1).replace(" ", "")) if match else None

def _extract_surface(text: str):
    match = re.search(r"(\d+)\s*m²", text)
    return int(match.group(1)) if match else None

def _extract_ville(text: str):
    match = re.search(r"([A-ZÀ-Ý][a-zà-ÿ\-]+(?:\s[A-ZÀ-Ý][a-zà-ÿ\-]+)*)\s*\((\d{2})\)", text)
    return match.group(1) if match else ""

def _extract_dept(ville: str) -> str:
    # PAP inclut souvent le département dans le texte (ex: "Créteil (94)")
    # Extraire depuis le texte brut de l'item si possible
    return ""
```

**Note:** Les sélecteurs CSS (`article.search-list-item`, `.price`, etc.) doivent être ajustés après inspection réelle de la page PAP.fr en Step 2.

- [ ] **Step 7: Créer scrapers/__init__.py**

```python
from .pap import PapScraper
from .logicimmo import LogicImmoScraper

def run_all_scrapers():
    results = []
    for ScraperClass in [PapScraper, LogicImmoScraper]:
        try:
            scraper = ScraperClass()
            results.extend(scraper.scrape())
        except Exception as e:
            print(f"Erreur {ScraperClass.__name__}: {e}")
    return results
```

- [ ] **Step 8: Lancer les tests**

```bash
pytest tests/test_pap.py -v
```
Expected: 3 PASSED (si la fixture HTML est bien téléchargée)

- [ ] **Step 9: Commit**

```bash
git add scrapers/ fixtures/pap_sample.html tests/test_pap.py
git commit -m "feat: PAP.fr scraper with BeautifulSoup"
```

---

### Task 4: Scraper Logic-immo

**Files:**
- Create: `appart-search/scrapers/logicimmo.py`
- Create: `appart-search/fixtures/logicimmo_sample.html`
- Create: `appart-search/tests/test_logicimmo.py`

- [ ] **Step 1: Télécharger une page Logic-immo pour fixture**

Ouvrir :
```
https://www.logic-immo.com/location-immobilier-ile-de-france,3_0/options/groupprptypesids=1/pricemax=900/nbrooms=2
```
Sauvegarder le HTML dans `fixtures/logicimmo_sample.html`

- [ ] **Step 2: Inspecter les sélecteurs Logic-immo (DevTools F12)**

Identifier les sélecteurs pour : conteneur annonce, titre, prix, surface, ville.

- [ ] **Step 3: Écrire les tests Logic-immo**

`tests/test_logicimmo.py`:
```python
from pathlib import Path
from scrapers.logicimmo import LogicImmoScraper

FIXTURE = Path("fixtures/logicimmo_sample.html").read_text(encoding="utf-8")

def test_logicimmo_parse_retourne_des_annonces():
    scraper = LogicImmoScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) > 0

def test_logicimmo_annonce_a_les_champs_requis():
    scraper = LogicImmoScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert "url" in a
        assert "source" in a
        assert a["source"] == "logicimmo"
```

- [ ] **Step 4: Créer scrapers/logicimmo.py**

```python
import re
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from .base import AbstractScraper

LOGICIMMO_URL = (
    "https://www.logic-immo.com/location-immobilier-ile-de-france,3_0"
    "/options/groupprptypesids=1/pricemax=900/nbrooms=2"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
}

class LogicImmoScraper(AbstractScraper):
    url = LOGICIMMO_URL

    def fetch_html(self, url: str) -> str:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.text

    def parse(self, html: str) -> List[Dict]:
        soup = BeautifulSoup(html, "lxml")
        annonces = []
        # ADAPTER CES SÉLECTEURS selon l'inspection DevTools (Step 2)
        for item in soup.select(".offer-block, .announcement-container, article"):
            lien = item.select_one("a[href]")
            titre_el = item.select_one("h2, .offer-title, .announcement-title")
            prix_el = item.select_one(".offer-price, .price, .announcement-price")

            if not lien:
                continue

            href = lien["href"]
            url = href if href.startswith("http") else "https://www.logic-immo.com" + href
            titre = titre_el.get_text(strip=True) if titre_el else ""
            prix_text = prix_el.get_text(strip=True) if prix_el else ""
            prix = _extract_prix(prix_text)
            surface = _extract_surface(item.get_text())
            ville = _extract_ville(item.get_text())

            annonces.append({
                "url": url,
                "titre": titre,
                "prix": prix,
                "surface": surface,
                "ville": ville,
                "departement": "",
                "source": "logicimmo",
            })
        return annonces


def _extract_prix(text: str):
    match = re.search(r"(\d[\d\s]*)\s*€", text.replace("\u00a0", " "))
    return int(match.group(1).replace(" ", "")) if match else None

def _extract_surface(text: str):
    match = re.search(r"(\d+)\s*m²", text)
    return int(match.group(1)) if match else None

def _extract_ville(text: str):
    match = re.search(r"([A-ZÀ-Ý][a-zà-ÿ\-]+(?:\s[A-ZÀ-Ý][a-zà-ÿ\-]+)*)\s*\((\d{2})\)", text)
    return match.group(1) if match else ""
```

- [ ] **Step 5: Lancer les tests**

```bash
pytest tests/test_logicimmo.py -v
```
Expected: 2 PASSED

- [ ] **Step 6: Commit**

```bash
git add scrapers/logicimmo.py fixtures/logicimmo_sample.html tests/test_logicimmo.py
git commit -m "feat: Logic-immo scraper"
```

---

## Chunk 3: Notifier et Scheduler

### Task 5: Envoi d'emails

**Files:**
- Create: `appart-search/notifier.py`
- Create: `appart-search/tests/test_notifier.py`

- [ ] **Step 1: Écrire les tests du notifier**

`tests/test_notifier.py`:
```python
from unittest.mock import patch, MagicMock
from notifier import send_email_alert
from models import Annonce

def test_send_email_alert_appelle_smtp(app):
    with app.app_context():
        annonces = [
            Annonce(url="https://pap.fr/1", titre="T2 Créteil 42m²", prix=850,
                    surface=42, ville="Créteil", source="pap"),
        ]
        with patch("notifier.smtplib.SMTP_SSL") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            send_email_alert(annonces, destinataire="test@example.com",
                             gmail_user="user@gmail.com", gmail_password="pass")
            assert mock_server.login.called
            assert mock_server.sendmail.called

def test_send_email_alert_ne_fait_rien_si_liste_vide(app):
    with app.app_context():
        with patch("notifier.smtplib.SMTP_SSL") as mock_smtp:
            send_email_alert([], "test@test.com", "u", "p")
            assert not mock_smtp.called
```

- [ ] **Step 2: Vérifier l'échec**

```bash
pytest tests/test_notifier.py -v
```
Expected: ImportError

- [ ] **Step 3: Créer notifier.py**

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from models import Annonce

def send_email_alert(annonces: List[Annonce], destinataire: str,
                     gmail_user: str, gmail_password: str) -> None:
    if not annonces:
        return

    sujet = f"🏠 {len(annonces)} nouvelle(s) annonce(s) T2 IDF"
    corps = _build_email_body(annonces)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = sujet
    msg["From"] = gmail_user
    msg["To"] = destinataire
    msg.attach(MIMEText(corps, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_user, gmail_password)
        server.sendmail(gmail_user, destinataire, msg.as_string())


def _build_email_body(annonces: List[Annonce]) -> str:
    lignes = []
    for a in annonces:
        lignes.append(f"""
        <div style="border:1px solid #ddd;padding:12px;margin:8px 0;border-radius:6px">
            <strong><a href="{a.url}">{a.titre}</a></strong><br>
            💶 {a.prix}€ CC &nbsp;|&nbsp;
            📐 {a.surface or "?"}m² &nbsp;|&nbsp;
            📍 {a.ville or "IDF"} &nbsp;|&nbsp;
            🔗 {a.source}
        </div>
        """)
    return f"""
    <html><body>
    <h2>🏠 Nouvelles annonces T2 Île-de-France</h2>
    {''.join(lignes)}
    <p style="color:#666;font-size:12px">AppartSearch IDF</p>
    </body></html>
    """
```

- [ ] **Step 4: Lancer les tests**

```bash
pytest tests/test_notifier.py -v
```
Expected: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add notifier.py tests/test_notifier.py
git commit -m "feat: Gmail SMTP email notifier"
```

---

### Task 6: Scheduler + intégration DB

**Files:**
- Modify: `appart-search/app.py`

- [ ] **Step 1: Mettre à jour app.py avec le scheduler et la logique de sauvegarde**

```python
from flask import Flask, render_template, request
from models import db, Annonce
from config import Config
from notifier import send_email_alert
from scrapers import run_all_scrapers
from apscheduler.schedulers.background import BackgroundScheduler

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        db.create_all()

    if not test_config:
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=lambda: scrape_and_notify(app),
            trigger="interval",
            minutes=app.config["SCRAPE_INTERVAL_MINUTES"],
        )
        scheduler.start()

    @app.route("/")
    def index():
        ville = request.args.get("ville", "")
        prix_max = request.args.get("prix_max", type=int)
        surface_min = request.args.get("surface_min", type=int)

        query = Annonce.query.order_by(Annonce.date_scrape.desc())
        if ville:
            query = query.filter(Annonce.ville.ilike(f"%{ville}%"))
        if prix_max:
            query = query.filter(Annonce.prix <= prix_max)
        if surface_min:
            query = query.filter(Annonce.surface >= surface_min)

        annonces = query.limit(100).all()
        villes = [v[0] for v in db.session.query(Annonce.ville).distinct().all() if v[0]]
        return render_template("index.html", annonces=annonces, villes=villes,
                               ville=ville, prix_max=prix_max, surface_min=surface_min)

    @app.route("/scrape-now")
    def scrape_now():
        scrape_and_notify(app)
        return "Scraping terminé", 200

    return app


def scrape_and_notify(app):
    with app.app_context():
        resultats = run_all_scrapers()
        nouvelles = []
        for data in resultats:
            if Annonce.query.filter_by(url=data["url"]).first():
                continue
            annonce = Annonce(**data)
            db.session.add(annonce)
            nouvelles.append(annonce)
        db.session.commit()

        if nouvelles and app.config["EMAIL_DESTINATAIRE"]:
            send_email_alert(
                nouvelles,
                destinataire=app.config["EMAIL_DESTINATAIRE"],
                gmail_user=app.config["GMAIL_USER"],
                gmail_password=app.config["GMAIL_PASSWORD"],
            )
        print(f"Scraping: {len(nouvelles)} nouvelle(s) annonce(s)")


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, use_reloader=False)
```

- [ ] **Step 2: Écrire le test de la route index**

`tests/test_routes.py`:
```python
def test_index_retourne_200(client):
    resp = client.get("/")
    assert resp.status_code == 200

def test_index_avec_filtre_ville(client, db_session):
    from models import Annonce
    db_session.add(Annonce(url="https://pap.fr/1", titre="T2", prix=800, ville="Créteil", source="pap"))
    db_session.commit()
    resp = client.get("/?ville=Créteil")
    assert b"Cr" in resp.data
```

Ajouter `client` fixture dans `conftest.py`:
```python
@pytest.fixture
def client(app):
    return app.test_client()
```

- [ ] **Step 3: Lancer tous les tests**

```bash
pytest tests/ -v
```
Expected: tous PASSED

- [ ] **Step 4: Commit**

```bash
git add app.py tests/test_routes.py tests/conftest.py
git commit -m "feat: scheduler, DB integration, and Flask routes"
```

---

## Chunk 4: Frontend et déploiement

### Task 7: Templates HTML

**Files:**
- Create: `appart-search/templates/base.html`
- Create: `appart-search/templates/index.html`
- Create: `appart-search/static/style.css`

- [ ] **Step 1: Créer static/style.css**

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f5f5; color: #333; }
.container { max-width: 1100px; margin: 0 auto; padding: 16px; }
nav { background: #2c3e50; color: white; padding: 12px 24px; display: flex; align-items: center; gap: 12px; }
nav h1 { font-size: 1.1rem; }
.layout { display: flex; gap: 20px; margin-top: 16px; }
.sidebar { width: 220px; flex-shrink: 0; }
.main { flex: 1; }
.card-filtres { background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.08); }
.card-filtres h3 { margin-bottom: 12px; font-size: .9rem; color: #666; text-transform: uppercase; letter-spacing: .05em; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: .85rem; margin-bottom: 4px; color: #555; }
.form-group input, .form-group select { width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: .9rem; }
.btn { display: block; width: 100%; padding: 8px; background: #2c3e50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: .9rem; margin-top: 4px; }
.btn:hover { background: #34495e; }
.btn-reset { background: #eee; color: #333; }
.annonce { background: white; border-radius: 8px; padding: 14px 16px; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,.08); display: flex; justify-content: space-between; align-items: flex-start; }
.annonce-info h2 { font-size: 1rem; margin-bottom: 4px; }
.annonce-info h2 a { color: #2c3e50; text-decoration: none; }
.annonce-info h2 a:hover { text-decoration: underline; }
.annonce-meta { font-size: .82rem; color: #777; }
.annonce-prix { font-size: 1.1rem; font-weight: bold; color: #27ae60; white-space: nowrap; }
.badge { display: inline-block; background: #27ae60; color: white; font-size: .7rem; padding: 2px 7px; border-radius: 10px; margin-left: 8px; vertical-align: middle; }
.badge-source { background: #3498db; }
.empty { text-align: center; padding: 40px; color: #999; }
.count { font-size: .85rem; color: #777; margin-bottom: 10px; }
```

- [ ] **Step 2: Créer templates/base.html**

```html
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AppartSearch IDF</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
  <nav>
    <h1>🏠 AppartSearch IDF</h1>
    <span style="font-size:.85rem;opacity:.7">T2 · Île-de-France · max 900€ CC</span>
  </nav>
  <div class="container">
    {% block content %}{% endblock %}
  </div>
</body>
</html>
```

- [ ] **Step 3: Créer templates/index.html**

```html
{% extends "base.html" %}
{% block content %}
<div class="layout">

  <aside class="sidebar">
    <div class="card-filtres">
      <h3>Filtres</h3>
      <form method="get" action="/">
        <div class="form-group">
          <label>Ville</label>
          <input type="text" name="ville" value="{{ ville or '' }}" placeholder="ex: Créteil">
        </div>
        <div class="form-group">
          <label>Prix max (€)</label>
          <input type="number" name="prix_max" value="{{ prix_max or '' }}" placeholder="900" min="0" max="900">
        </div>
        <div class="form-group">
          <label>Surface min (m²)</label>
          <input type="number" name="surface_min" value="{{ surface_min or '' }}" placeholder="25" min="0">
        </div>
        <button type="submit" class="btn">Filtrer</button>
        <a href="/" class="btn btn-reset" style="text-align:center;margin-top:6px;display:block;text-decoration:none">Réinitialiser</a>
      </form>
    </div>
  </aside>

  <main class="main">
    <p class="count">{{ annonces|length }} annonce(s) trouvée(s)</p>

    {% if annonces %}
      {% for a in annonces %}
      <div class="annonce">
        <div class="annonce-info">
          <h2>
            <a href="{{ a.url }}" target="_blank" rel="noopener">{{ a.titre }}</a>
            {% if a.est_nouvelle %}<span class="badge">Nouveau</span>{% endif %}
            <span class="badge badge-source">{{ a.source }}</span>
          </h2>
          <div class="annonce-meta">
            {% if a.surface %}📐 {{ a.surface }}m² &nbsp;{% endif %}
            {% if a.ville %}📍 {{ a.ville }}{% if a.departement %} ({{ a.departement }}){% endif %}{% endif %}
            &nbsp;· {{ a.date_scrape.strftime('%d/%m %H:%M') }}
          </div>
        </div>
        <div class="annonce-prix">{{ a.prix }}€ CC</div>
      </div>
      {% endfor %}
    {% else %}
      <div class="empty">
        <p>Aucune annonce trouvée.</p>
        <p style="margin-top:8px;font-size:.85rem">Essaie <a href="/scrape-now">de lancer un scraping manuel</a>.</p>
      </div>
    {% endif %}
  </main>

</div>
{% endblock %}
```

- [ ] **Step 4: Tester manuellement**

```bash
python app.py
```
Ouvrir http://localhost:5000 — vérifier que la page s'affiche correctement.

- [ ] **Step 5: Commit**

```bash
git add templates/ static/
git commit -m "feat: HTML templates and CSS styling"
```

---

### Task 8: Déploiement Railway

**Files:**
- Create: `appart-search/Procfile`
- Create: `appart-search/railway.toml`

- [ ] **Step 1: Créer Procfile**

```
web: gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 1
```

- [ ] **Step 2: Créer railway.toml**

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn 'app:create_app()' --bind 0.0.0.0:$PORT --workers 1"
healthcheckPath = "/"
```

- [ ] **Step 3: Créer un compte Railway et déployer**

1. Aller sur https://railway.app → Se connecter avec GitHub
2. "New Project" → "Deploy from GitHub repo"
3. Sélectionner le repo `appart-search`
4. Dans les settings du projet → "Variables" → Ajouter :
   - `EMAIL_DESTINATAIRE`
   - `GMAIL_USER`
   - `GMAIL_PASSWORD`
   - `SECRET_KEY` (générer une clé aléatoire)

- [ ] **Step 4: Configurer Gmail**

Pour que l'envoi d'email fonctionne :
1. Aller sur https://myaccount.google.com/security
2. Activer la "Validation en deux étapes"
3. Aller dans "Mots de passe des applications"
4. Créer un mot de passe pour "Autre (appart-search)"
5. Utiliser ce mot de passe dans `GMAIL_PASSWORD` (pas le mot de passe Gmail normal)

- [ ] **Step 5: Vérifier le déploiement**

Ouvrir l'URL Railway fournie → vérifier que le site s'affiche.
Aller sur `https://votre-url.railway.app/scrape-now` pour déclencher un premier scraping.

- [ ] **Step 6: Commit final**

```bash
git add Procfile railway.toml
git commit -m "feat: Railway deployment configuration"
git push origin main
```

---

## Résumé

| Chunk | Tâches | Tests |
|-------|--------|-------|
| 1 | Setup + modèle DB | test_models.py |
| 2 | Scrapers PAP + Logic-immo | test_pap.py, test_logicimmo.py |
| 3 | Notifier email + Scheduler | test_notifier.py, test_routes.py |
| 4 | Frontend + Railway | Test manuel |
