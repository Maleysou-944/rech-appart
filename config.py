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
    SCRAPE_INTERVAL_MINUTES = int(os.environ.get("SCRAPE_INTERVAL_MINUTES", "240"))
    PRIX_MAX = int(os.environ.get("PRIX_MAX", "900"))
    SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")
