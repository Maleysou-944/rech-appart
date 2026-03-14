import logging
from .pap import PapScraper
from .laforet import LaforetScraper
from .leboncoin import LeBonCoinScraper
from .paruvendu import ParuVenduScraper

logger = logging.getLogger(__name__)

# PAP.fr geographic codes: dept_number + 364 = g_code
# g439=Paris(75), g456=Hauts-de-Seine(92), g457=Seine-Saint-Denis(93), g458=Val-de-Marne(94)
_PAP_BASE = "https://www.pap.fr/annonce/locations-appartement"
PAP_PAGES = [
    # Paris (75) — 2 pages pour T1/T2/T3
    f"{_PAP_BASE}-t1-ile-de-france-g439-bu2p0?prix-max=1500",
    f"{_PAP_BASE}-t2-ile-de-france-g439-bu2p0?prix-max=1500",
    f"{_PAP_BASE}-t2-ile-de-france-g439-bu2p0?prix-max=1500&page=2",
    f"{_PAP_BASE}-t3-ile-de-france-g439-bu2p0?prix-max=1500",
    # Petite couronne — T1/T2/T3
    f"{_PAP_BASE}-t1-g456?prix-max=1500",  # 92
    f"{_PAP_BASE}-t2-g456?prix-max=1500",
    f"{_PAP_BASE}-t3-g456?prix-max=1500",
    f"{_PAP_BASE}-t1-g457?prix-max=1500",  # 93
    f"{_PAP_BASE}-t2-g457?prix-max=1500",
    f"{_PAP_BASE}-t3-g457?prix-max=1500",
    f"{_PAP_BASE}-t1-g458?prix-max=1500",  # 94
    f"{_PAP_BASE}-t2-g458?prix-max=1500",
    f"{_PAP_BASE}-t3-g458?prix-max=1500",
]

_LAFORET_BASE = "https://www.laforet.com/louer/location-appartement/?regions=12&prix_max=1500&nb_pieces="
LAFORET_URLS = [
    f"{_LAFORET_BASE}1",  # T1
    f"{_LAFORET_BASE}2",  # T2
    f"{_LAFORET_BASE}3",  # T3
]


# BienIci : écarté — site SPA ou inaccessible, HTML des annonces non disponible sans JavaScript

# Century21 : écarté — site SPA, le paramètre localisation= n'est pas traité côté serveur ;
# les seuls éléments HTML présents sont des "coups de coeur" éditoriaux (9 annonces nationales),
# pas des résultats filtrés par département IDF.


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

    laforet = LaforetScraper()
    for url in LAFORET_URLS:
        try:
            html = laforet.fetch_html(url)
            annonces = laforet.parse(html)
            results.extend(annonces)
            print(f"Laforêt {url.split('=')[-1]} pièce(s): OK ({len(annonces)} annonces IDF)", flush=True)
        except Exception as e:
            logger.error(f"Erreur Laforêt {url}: {e}")
            print(f"SCRAPER ERROR Laforêt {url}: {e}", flush=True)

    leboncoin = LeBonCoinScraper()
    try:
        html = leboncoin.fetch_html(leboncoin.url)
        annonces_lbc = leboncoin.parse(html)
        results.extend(annonces_lbc)
        print(f"LeBonCoin: OK ({len(annonces_lbc)} annonces IDF)", flush=True)
    except Exception as e:
        logger.error(f"Erreur LeBonCoin: {e}")
        print(f"SCRAPER ERROR LeBonCoin: {e}", flush=True)

    paruvendu = ParuVenduScraper()
    try:
        html = paruvendu.fetch_html(paruvendu.url)
        annonces_pv = paruvendu.parse(html)
        results.extend(annonces_pv)
        print(f"ParuVendu: OK ({len(annonces_pv)} annonces IDF)", flush=True)
    except Exception as e:
        logger.error(f"Erreur ParuVendu: {e}")
        print(f"SCRAPER ERROR ParuVendu: {e}", flush=True)

    return results
