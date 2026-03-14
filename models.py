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

    @property
    def est_nouvelle(self):
        if self.date_scrape is None:
            return True
        return (datetime.utcnow() - self.date_scrape) < timedelta(hours=24)

    def __repr__(self):
        return f"<Annonce {self.ville} {self.prix}€>"
