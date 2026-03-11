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
