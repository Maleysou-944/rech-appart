# AppartSearch IDF — Design Spec
Date: 2026-03-11

## Contexte
Site web de veille immobilière pour trouver un T2 en Île-de-France à max 900€ charges comprises. Scrape PAP.fr et Logic-immo.fr automatiquement et envoie des alertes email pour les nouvelles annonces.

## Stack technique
- **Backend** : Python 3.11 + Flask
- **Scraping** : requests + BeautifulSoup4
- **Base de données** : SQLite (via SQLAlchemy)
- **Scheduler** : APScheduler (toutes les heures)
- **Emails** : smtplib + Gmail SMTP
- **Frontend** : Jinja2 templates + CSS vanilla
- **Hébergement** : Railway (free tier)

## Fonctionnalités

### Scraping
- Sources : PAP.fr + Logic-immo.fr
- Critères fixes : T2, Île-de-France, max 900€ CC
- Fréquence : toutes les heures
- Déduplication par URL d'annonce

### Interface (layout liste + filtres)
- Filtres à gauche : ville/département, prix max, surface min
- Liste d'annonces à droite : titre, prix, surface, ville, source, date
- Badge "Nouveau" pour annonces < 24h
- Lien direct vers l'annonce originale

### Alertes email
- Déclenchement : dès qu'une nouvelle annonce est trouvée
- Contenu : liste des nouvelles annonces avec lien
- Config : adresse email destinataire dans variable d'environnement

## Ce qui est hors scope
- Authentification utilisateur
- Carte interactive
- LeBonCoin (protection anti-bot Cloudflare)
- Application mobile

## Structure de la base de données
```
annonces (
  id, url, titre, prix, surface, ville, departement,
  source, date_publication, date_scrape, vue
)
```

## Variables d'environnement (Railway)
- `EMAIL_DESTINATAIRE` — adresse qui reçoit les alertes
- `GMAIL_USER` — compte Gmail expéditeur
- `GMAIL_PASSWORD` — mot de passe d'application Gmail
- `SECRET_KEY` — clé Flask
