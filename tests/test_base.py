from scrapers.base import AbstractScraper


class ConcreteScraper(AbstractScraper):
    """Implémentation minimale pour tester AbstractScraper."""
    url = "http://example.com"

    def fetch_html(self, url: str) -> str:
        return ""

    def parse(self, html: str) -> list:
        return []


def test_est_colocation_detecte_colocation():
    s = ConcreteScraper()
    assert s.est_colocation("Colocation 2 chambres Paris 15") is True


def test_est_colocation_detecte_coloc():
    s = ConcreteScraper()
    assert s.est_colocation("Coloc sympa Vincennes") is True


def test_est_colocation_detecte_chambre_chez():
    s = ConcreteScraper()
    assert s.est_colocation("Chambre chez habitant CDG") is True


def test_est_colocation_detecte_chambre_en():
    s = ConcreteScraper()
    assert s.est_colocation("Chambre en colocation Montreuil") is True


def test_est_colocation_laisse_passer_t2():
    s = ConcreteScraper()
    assert s.est_colocation("T2 lumineux Paris 15e 850€") is False


def test_est_colocation_insensible_casse():
    s = ConcreteScraper()
    assert s.est_colocation("COLOCATION Paris") is True
