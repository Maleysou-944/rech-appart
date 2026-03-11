import logging
from .pap import PapScraper
from .logicimmo import LogicImmoScraper

logger = logging.getLogger(__name__)


def run_all_scrapers():
    results = []
    for ScraperClass in [PapScraper, LogicImmoScraper]:
        try:
            scraper = ScraperClass()
            results.extend(scraper.scrape())
        except Exception as e:
            logger.error(f"Erreur {ScraperClass.__name__}: {e}")
            print(f"SCRAPER ERROR {ScraperClass.__name__}: {e}", flush=True)
    return results
