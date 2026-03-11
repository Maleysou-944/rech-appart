import os
import re
import requests
from typing import List, Dict
from bs4 import BeautifulSoup

from .base import AbstractScraper

BASE_URL = "https://www.pap.fr"
SEARCH_URL = (
    "https://www.pap.fr/annonce/locations-appartement-t2-ile-de-france-g439-bu2p0"
    "?prix-max=1500"
)


class PapScraper(AbstractScraper):
    def __init__(self, url: str = SEARCH_URL):
        self.url = url

    def fetch_html(self, url: str) -> str:
        api_key = os.environ.get("SCRAPERAPI_KEY", "")
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

        COLOC_KEYWORDS = ("colocation", "coloc", "chambre chez", "chambre en ")

        items = soup.select("div.search-list-item-alt")
        for item in items:
            title_link = item.select_one("a.item-title")
            if not title_link:
                continue

            # Exclure les colocations
            title_text = title_link.get_text(strip=True).lower()
            if any(kw in title_text for kw in COLOC_KEYWORDS):
                continue

            # URL
            href = title_link.get("href", "").strip()
            if not href:
                continue
            url = href if href.startswith("http") else BASE_URL + href

            # Prix — strip &nbsp; and parse number
            price_el = item.select_one("span.item-price")
            prix = None
            if price_el:
                raw = price_el.get_text(separator=" ").strip()
                # Remove thousands separator (dot) and extract digits
                digits = re.sub(r"[^\d]", "", raw.replace("\u00a0", ""))
                if digits:
                    prix = int(digits)

            # Ville from <span class="h1">
            city_el = item.select_one("span.h1")
            ville_raw = city_el.get_text(strip=True) if city_el else ""

            # Extract département from parentheses e.g. "Paris 9E (75009)" -> "75"
            dept_match = re.search(r"\((\d{5})\)", ville_raw)
            departement = dept_match.group(1)[:2] if dept_match else None

            # Ville: strip the (XXXXX) part
            ville = re.sub(r"\s*\(\d+\)\s*$", "", ville_raw).strip()

            # Surface from item-tags: look for "XX m²"
            surface = None
            tags = item.select("ul.item-tags li")
            for tag in tags:
                tag_text = tag.get_text(separator=" ", strip=True)
                m = re.search(r"([\d,\.]+)\s*m²", tag_text)
                if m:
                    surface_str = m.group(1).replace(",", ".").replace("\u00a0", "")
                    try:
                        surface = int(float(surface_str))
                    except ValueError:
                        surface = None
                    break

            # Titre: combine price + ville
            titre = f"{price_el.get_text(strip=True) if price_el else ''} {ville_raw}".strip()

            annonces.append(
                {
                    "url": url,
                    "titre": titre,
                    "prix": prix,
                    "surface": surface,
                    "ville": ville,
                    "departement": departement,
                    "source": "pap",
                }
            )

        return annonces
