import threading
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
        # Migration : ajouter la colonne images si absente (SQLite ne supporte pas IF NOT EXISTS)
        from sqlalchemy import text
        try:
            db.session.execute(text("ALTER TABLE annonces ADD COLUMN images TEXT"))
            db.session.commit()
        except Exception:
            pass  # Colonne déjà présente — ignoré silencieusement

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
        departements = request.args.getlist("departement")
        sources = request.args.getlist("source")
        types_bien = request.args.getlist("type_bien")

        query = Annonce.query.order_by(Annonce.date_scrape.desc())
        if ville:
            query = query.filter(Annonce.ville.ilike(f"%{ville}%"))
        if prix_max:
            query = query.filter(Annonce.prix <= prix_max)
        if surface_min:
            query = query.filter(Annonce.surface >= surface_min)
        if departements:
            query = query.filter(Annonce.departement.in_(departements))
        if sources:
            query = query.filter(Annonce.source.in_(sources))
        if types_bien:
            query = query.filter(Annonce.type_bien.in_(types_bien))

        annonces = query.limit(100).all()
        sources_dispo = [s[0] for s in db.session.query(Annonce.source).distinct().all() if s[0]]

        return render_template(
            "index.html",
            annonces=annonces,
            ville=ville,
            prix_max=prix_max,
            surface_min=surface_min,
            departements=departements,
            sources=sources,
            sources_dispo=sources_dispo,
            types_bien=types_bien,
        )

    @app.route("/scrape-now")
    def scrape_now():
        secret = app.config.get("SCRAPE_SECRET", "")
        if secret and request.args.get("token") != secret:
            return "Non autorisé.", 403
        threading.Thread(target=scrape_and_notify, args=(app,), daemon=True).start()
        return "Scraping lancé en arrière-plan. Reviens dans 1 minute sur la page principale.", 200

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
