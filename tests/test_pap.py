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
