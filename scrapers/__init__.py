import logging
from .pap import PapScraper, SEARCH_URL as PAP_PARIS_URL

logger = logging.getLogger(__name__)

# PAP.fr geographic codes: dept_number + 364 = g_code
# g439=Paris(75), g456=Hauts-de-Seine(92), g457=Seine-Saint-Denis(93), g458=Val-de-Marne(94)
PAP_PAGES = [
    PAP_PARIS_URL,                    # Paris (75) - page 1
    f"{PAP_PARIS_URL}&page=2",        # Paris (75) - page 2
    "https://www.pap.fr/annonce/locations-appartement-t2-g456?prix-max=1500",  # Hauts-de-Seine (92)
    "https://www.pap.fr/annonce/locations-appartement-t2-g457?prix-max=1500",  # Seine-Saint-Denis (93)
    "https://www.pap.fr/annonce/locations-appartement-t2-g458?prix-max=1500",  # Val-de-Marne (94)
]


def run_all_scrapers():
    results = []

    pap = PapScraper()
    for url in PAP_PAGES:
        try:
            html = pap.fetch_html(url)
            results.extend(pap.parse(html))
            label = url.split("?")[0].split("-")[-1]
            print(f"PAP {label}: OK", flush=True)
        except Exception as e:
            logger.error(f"Erreur PAP {url}: {e}")
            print(f"SCRAPER ERROR PAP {url}: {e}", flush=True)

    return results
