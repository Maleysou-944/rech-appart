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


def test_logicimmo_annonce_urls_absolues():
    scraper = LogicImmoScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["url"].startswith("https://")


def test_logicimmo_surface_entier_ou_none():
    scraper = LogicImmoScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["surface"] is None or isinstance(a["surface"], int)
