import logging
from .pap import PapScraper, BASE_URL as PAP_BASE, SEARCH_URL as PAP_URL
from .logicimmo import LogicImmoScraper, SEARCH_URL as LOGICIMMO_URL

logger = logging.getLogger(__name__)

PAP_PAGES = [
    f"{PAP_URL}&page={i}" for i in range(1, 3)
]

LOGICIMMO_PAGES = [
    LOGICIMMO_URL,
    LOGICIMMO_URL + "/page=2",
]


def run_all_scrapers():
    results = []

    pap = PapScraper()
    for url in PAP_PAGES:
        try:
            html = pap.fetch_html(url)
            results.extend(pap.parse(html))
            print(f"PAP page {url[-1]}: OK", flush=True)
        except Exception as e:
            logger.error(f"Erreur PAP {url}: {e}")
            print(f"SCRAPER ERROR PAP {url}: {e}", flush=True)

    li = LogicImmoScraper()
    for url in LOGICIMMO_PAGES:
        try:
            html = li.fetch_html(url)
            results.extend(li.parse(html))
            print(f"LogicImmo {url[-6:]}: OK", flush=True)
        except Exception as e:
            logger.error(f"Erreur LogicImmo {url}: {e}")
            print(f"SCRAPER ERROR LogicImmo {url}: {e}", flush=True)

    return results
