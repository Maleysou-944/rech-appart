from .pap import PapScraper
from .logicimmo import LogicImmoScraper


def run_all_scrapers():
    results = []
    for ScraperClass in [PapScraper, LogicImmoScraper]:
        try:
            scraper = ScraperClass()
            results.extend(scraper.scrape())
        except Exception as e:
            print(f"Erreur {ScraperClass.__name__}: {e}")
    return results
