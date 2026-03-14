import json
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
    type_bien = db.Column(db.String(5))
    date_scrape = db.Column(db.DateTime, default=datetime.utcnow)
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

    @property
    def est_nouvelle(self):
        if self.date_scrape is None:
            return True
        return (datetime.utcnow() - self.date_scrape) < timedelta(hours=24)

    def __repr__(self):
        return f"<Annonce {self.ville} {self.prix}€>"
