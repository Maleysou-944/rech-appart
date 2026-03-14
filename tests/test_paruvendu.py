from pathlib import Path
from scrapers.paruvendu import ParuVenduScraper

FIXTURE = Path("fixtures/paruvendu_sample.html").read_text(encoding="utf-8")


def test_paruvendu_parse_retourne_des_annonces():
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) > 0


def test_paruvendu_annonce_a_les_champs_requis():
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert "url" in a
        assert "titre" in a
        assert "prix" in a
        assert "source" in a
        assert a["source"] == "paruvendu"


def test_paruvendu_urls_absolues():
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["url"].startswith("https://"), f"URL invalide: {a['url']}"


def test_paruvendu_filtre_hors_idf():
    """Seuls les depts 75/92/93/94 doivent être retournés."""
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["departement"] in {"75", "92", "93", "94"}, (
            f"Département hors IDF petite couronne: {a['departement']}"
        )


def test_paruvendu_surface_est_entier_ou_none():
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["surface"] is None or isinstance(a["surface"], int)


def test_paruvendu_prix_est_entier_ou_none():
    scraper = ParuVenduScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["prix"] is None or isinstance(a["prix"], int)


def test_paruvendu_parse_html_vide_retourne_liste_vide():
    scraper = ParuVenduScraper()
    assert scraper.parse("") == []
