from pathlib import Path
from scrapers.leboncoin import LeBonCoinScraper

FIXTURE = Path("fixtures/leboncoin_sample.html").read_text(encoding="utf-8")


def test_leboncoin_parse_retourne_des_annonces():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) > 0


def test_leboncoin_annonce_a_les_champs_requis():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert "url" in a
        assert "titre" in a
        assert "prix" in a
        assert "source" in a
        assert a["source"] == "leboncoin"


def test_leboncoin_urls_absolues():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["url"].startswith("https://"), f"URL invalide: {a['url']}"


def test_leboncoin_filtre_hors_idf():
    """Versailles (78) doit être exclu — seuls 75/92/93/94 gardés."""
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["departement"] in {"75", "92", "93", "94"}, (
            f"Département hors IDF petite couronne: {a['departement']}"
        )


def test_leboncoin_fixture_a_2_annonces_valides():
    """Fixture: 4 annonces — 1 grande couronne (78) + 1 colocation → 2 retournées."""
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    assert len(annonces) == 2


def test_leboncoin_filtre_colocation():
    """L'annonce 'Colocation T2 Paris' doit être filtrée."""
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert "colocation" not in a["titre"].lower()


def test_leboncoin_surface_est_entier_ou_none():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["surface"] is None or isinstance(a["surface"], int)


def test_leboncoin_prix_est_entier_ou_none():
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    for a in annonces:
        assert a["prix"] is None or isinstance(a["prix"], int)


def test_leboncoin_parse_html_vide_retourne_liste_vide():
    scraper = LeBonCoinScraper()
    assert scraper.parse("") == []


def test_leboncoin_parse_sans_next_data_retourne_liste_vide():
    scraper = LeBonCoinScraper()
    assert scraper.parse("<html><body>Pas de __NEXT_DATA__</body></html>") == []


def test_leboncoin_extrait_images():
    """L'annonce Paris doit avoir 3 URLs d'images (JSON stringifié)."""
    import json
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(FIXTURE)
    paris = next(a for a in annonces if a["departement"] == "75")
    assert "images" in paris
    images = json.loads(paris["images"])
    assert len(images) == 3
    assert all(u.startswith("https://") for u in images)


def test_leboncoin_images_none_si_absent():
    """L'annonce sans clé images doit retourner images=None."""
    html_sans_images = FIXTURE.replace(
        '"images": {\n              "urls": [\n                "https://img.leboncoin.fr/api/thumb/abc1.jpg",\n                "https://img.leboncoin.fr/api/thumb/abc2.jpg",\n                "https://img.leboncoin.fr/api/thumb/abc3.jpg"\n              ]\n            }', ""
    ).replace(
        '"images": {\n              "urls": [\n                "https://img.leboncoin.fr/api/thumb/def1.jpg"\n              ]\n            }', ""
    )
    scraper = LeBonCoinScraper()
    annonces = scraper.parse(html_sans_images)
    for a in annonces:
        assert a.get("images") is None
