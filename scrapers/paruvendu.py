import json
import logging
import re
import requests
from typing import List, Dict

from bs4 import BeautifulSoup

from .base import AbstractScraper

logger = logging.getLogger(__name__)

SEARCH_URL = (
    "https://www.paruvendu.fr/immobilier/location/appartement/"
    "?px_loyermax=1500"
)
BASE_URL = "https://www.paruvendu.fr"
IDF_DEPTS = {"75", "92", "93", "94"}


class ParuVenduScraper(AbstractScraper):
    def __init__(self, url: str = SEARCH_URL):
        self.url = url

    def fetch_html(self, url: str) -> str:
        logger.info("Fetching ParuVendu: %s", url)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "fr-FR,fr;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = "windows-1252"
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.warning("ParuVendu: échec fetch %s: %s", url, e)
            return ""

    def parse(self, html: str) -> List[Dict]:
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        annonces = []

        items = soup.select("div.flex-1.overflow-hidden")
        logger.debug("ParuVendu: %d blocs trouvés", len(items))

        for item in items:
            try:
                # URL — href direct dans le h3
                link_el = item.select_one("h3.text-base a[href]")
                if not link_el:
                    continue
                href = link_el.get("href", "").strip()
                url = BASE_URL + href if not href.startswith("http") else href

                # Prix — premier div dans div.encoded-lnk
                prix = None
                prix_el = item.select_one("div.encoded-lnk div")
                if prix_el:
                    raw = prix_el.get_text().replace("\u00a0", "").split("CC")[0]
                    digits = re.sub(r"[^\d]", "", raw)
                    if digits:
                        prix = int(digits)

                # Surface et ville — texte du span dans h3 a
                surface = None
                ville = ""
                departement = None
                span = item.select_one("h3.text-base a span")
                if span:
                    text = span.get_text(separator=" ")

                    # Surface : nombre suivi de "m" puis "2" (m<sup>2</sup>)
                    m_surf = re.search(r"(\d+)\s*m\s*2", text)
                    if m_surf:
                        surface = int(m_surf.group(1))

                    # Ville et département : "Ville (XX)" avec XX 2 chiffres
                    m_loc = re.search(r"([^\n|]+)\s*\((\d{2})\)", text)
                    if m_loc:
                        ville = m_loc.group(1).strip()
                        departement = m_loc.group(2)

                # Filtre petite couronne IDF uniquement
                if departement not in IDF_DEPTS:
                    continue

                titre = f"{prix} {ville}" if prix and ville else ""

                if self.est_colocation(titre):
                    continue

                # Images — dans div.blocMedia (sibling du container item)
                images = None
                bloc = item.parent.select_one("div.blocMedia") if item.parent else None
                if bloc:
                    img_urls = []
                    for img in bloc.find_all("img", src=True):
                        src = img.get("src", "")
                        if (src and src.startswith("http")
                                and "transparent" not in src
                                and "1x1" not in src):
                            img_urls.append(src)
                        if len(img_urls) >= 3:
                            break
                    if img_urls:
                        images = json.dumps(img_urls)

                annonces.append({
                    "url": url,
                    "titre": titre,
                    "prix": prix,
                    "surface": surface,
                    "ville": ville,
                    "departement": departement,
                    "source": "paruvendu",
                    "images": images,
                })
            except Exception as e:
                logger.debug("ParuVendu: skip annonce: %s", e)
                continue

        logger.info("Parsed %d annonces depuis ParuVendu", len(annonces))
        return annonces
