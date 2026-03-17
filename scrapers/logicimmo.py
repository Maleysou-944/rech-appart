import logging
import os
import re
import requests
from typing import List, Dict
from bs4 import BeautifulSoup

from .base import AbstractScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://www.logic-immo.com"
SEARCH_URL = (
    "https://www.logic-immo.com/location-immobilier-ile-de-france,3_0"
    "/options/groupprptypesids=1/pricemax=1500/nbrooms=2"
)


class LogicImmoScraper(AbstractScraper):
    def __init__(self, url: str = SEARCH_URL):
        self.url = url

    def fetch_html(self, url: str) -> str:
        api_key = os.environ.get("SCRAPERAPI_KEY", "")
        logger.info("Fetching Logic-immo: %s", url)
        if api_key:
            proxy_url = f"http://api.scraperapi.com?api_key={api_key}&url={url}&country_code=fr"
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
        soup = BeautifulSoup(html, "lxml")
        annonces = []

        items = soup.select("div.offer-block")
        logger.debug("Found %d offer-block items", len(items))

        for item in items:
            link_el = item.select_one("a.offer-block-link")
            if not link_el:
                continue

            href = link_el.get("href", "").strip()
            if not href:
                continue

            url = href if href.startswith("http") else BASE_URL + href

            # Prix — e.g. "750 €/mois"
            prix = None
            price_el = item.select_one("span.price-label")
            if price_el:
                raw = price_el.get_text(separator=" ").strip()
                digits = re.sub(r"[^\d]", "", raw.replace("\u00a0", ""))
                if digits:
                    prix = int(digits)

            # Titre — from h2.offer-title
            titre_el = item.select_one("h2.offer-title")
            titre = titre_el.get_text(strip=True) if titre_el else ""

            # Surface — from span.offer-area or from title text "XX m²"
            surface = None
            area_el = item.select_one("span.offer-area")
            area_text = area_el.get_text(strip=True) if area_el else ""
            if not area_text and titre:
                area_text = titre

            m = re.search(r"([\d,\.]+)\s*m²", area_text)
            if m:
                surface_str = m.group(1).replace(",", ".").replace("\u00a0", "")
                try:
                    surface = int(float(surface_str))
                except ValueError:
                    surface = None

            # Ville & département — from span.offer-city e.g. "Montreuil (93100)"
            city_el = item.select_one("span.offer-city")
            ville_raw = city_el.get_text(strip=True) if city_el else ""

            dept_match = re.search(r"\((\d{5})\)", ville_raw)
            departement = dept_match.group(1)[:2] if dept_match else None

            ville = re.sub(r"\s*\(\d+\)\s*$", "", ville_raw).strip()

            logger.debug(
                "Annonce: ville=%s dept=%s prix=%s surface=%s url=%s",
                ville, departement, prix, surface, url,
            )

            annonces.append(
                {
                    "url": url,
                    "titre": titre,
                    "prix": prix,
                    "surface": surface,
                    "ville": ville,
                    "departement": departement,
                    "source": "logicimmo",
                }
            )

        logger.info("Parsed %d annonces from Logic-immo", len(annonces))
        return annonces
