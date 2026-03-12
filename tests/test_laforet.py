from pathlib import Path
from scrapers.laforet import LaforetScraper

FIXTURE = Path("fixtures/laforet_sample.html").read_text(encoding="utf-8")


def test_laforet_parse_retourne_des_annonces():
    scraper = LaforetScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) > 0


def test_laforet_annonce_a_les_champs_requis():
    scraper = LaforetScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert "url" in a
        assert "titre" in a
        assert "source" in a
        assert a["source"] == "laforet"


def test_laforet_urls_sont_absolues():
    scraper = LaforetScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["url"].startswith("https://"), f"URL invalide: {a['url']}"


def test_laforet_pas_de_coloc():
    scraper = LaforetScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert not scraper.est_colocation(a["titre"]), f"Coloc non filtrée: {a['titre']}"


def test_laforet_departements_idf_uniquement():
    scraper = LaforetScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["departement"] in ("75", "92", "93", "94"), (
            f"Département hors IDF: {a['departement']} — {a['ville']}"
        )
