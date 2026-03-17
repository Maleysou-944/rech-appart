import json
import logging
import os
import requests
from typing import List, Dict
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base import AbstractScraper

logger = logging.getLogger(__name__)

SEARCH_URL = (
    "https://www.leboncoin.fr/recherche"
    "?category=locations&region=ile-de-france"
    "&price=min-1500&rooms=2-2&real_estate_type=2"
)
BASE_URL = "https://www.leboncoin.fr"
IDF_DEPTS = {"75", "92", "93", "94"}


class LeBonCoinScraper(AbstractScraper):
    def __init__(self, url: str = SEARCH_URL):
        self.url = url

    def fetch_html(self, url: str) -> str:
        api_key = os.environ.get("SCRAPERAPI_KEY", "")
        logger.info("Fetching LeBonCoin: %s", url)
        if api_key:
            proxy_url = (
                f"http://api.scraperapi.com?api_key={api_key}"
                f"&url={quote(url, safe='')}&country_code=fr"
            )
            response = requests.get(proxy_url, timeout=60)
        else:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "fr-FR,fr;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text

    def parse(self, html: str) -> List[Dict]:
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        annonces = []

        try:
            script = soup.find("script", {"id": "__NEXT_DATA__"})
            if not script or not script.string:
                logger.error("LeBonCoin: balise __NEXT_DATA__ introuvable")
                return []
            data = json.loads(script.string)
            ads = data["props"]["pageProps"]["searchData"]["ads"]
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("LeBonCoin: échec parsing __NEXT_DATA__: %s", e)
            return []

        for ad in ads:
            try:
                list_id = ad.get("list_id")
                if not list_id:
                    continue

                url = f"{BASE_URL}/ad/locations/{list_id}.htm"

                # Prix
                price_list = ad.get("price", [])
                prix = int(price_list[0]) if price_list else None

                # Surface — dans la liste "attributes", clé "square"
                surface = None
                for attr in ad.get("attributes", []):
                    if attr.get("key") == "square":
                        try:
                            surface = int(float(attr.get("value", 0)))
                        except (ValueError, TypeError):
                            pass
                        break

                # Localisation — zipcode est toujours 5 chiffres en France métropolitaine
                location = ad.get("location", {})
                ville = location.get("city", "")
                zipcode = location.get("zipcode", "")
                departement = zipcode[:2] if zipcode else None

                # Filtre petite couronne IDF uniquement (exclut 77/78/91/95)
                if departement not in IDF_DEPTS:
                    continue

                subject = ad.get("subject", "")
                titre = f"{prix} {ville}" if prix and ville else subject

                # Vérifier le titre original (subject) car le titre construit ne contient pas les mots-clés
                if self.est_colocation(subject) or self.est_colocation(titre):
                    continue

                # Images — dans ad["images"]["urls"], jusqu'à 3 URLs
                images = None
                raw_images = ad.get("images", {})
                if isinstance(raw_images, dict):
                    urls = raw_images.get("urls", [])
                    if not urls:
                        # Fallback : small_url (str) ou image_url (str)
                        small = raw_images.get("small_url")
                        if small and small.startswith("http"):
                            urls = [small]
                    if not urls:
                        direct = ad.get("image_url")
                        if direct and direct.startswith("http"):
                            urls = [direct]
                    valid = [u for u in urls[:3] if u and u.startswith("http")]
                    if valid:
                        images = json.dumps(valid)
                    else:
                        logger.debug("LeBonCoin images keys: %s", list(raw_images.keys()))

                annonces.append({
                    "url": url,
                    "titre": titre,
                    "prix": prix,
                    "surface": surface,
                    "ville": ville,
                    "departement": departement,
                    "source": "leboncoin",
                    "images": images,
                })
            except Exception as e:
                logger.debug("LeBonCoin: skip annonce %s: %s", ad.get("list_id"), e)
                continue

        logger.info("Parsed %d annonces depuis LeBonCoin", len(annonces))
        return annonces
