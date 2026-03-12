import os
import re
import requests
from typing import List, Dict
from urllib.parse import quote
from bs4 import BeautifulSoup

from .base import AbstractScraper

BASE_URL = "https://www.laforet.com"
# 2 pièces, regions=12 (Île-de-France) — filtering is reinforced in parse() by postal code
SEARCH_URL = (
    "https://www.laforet.com/louer/location-appartement/"
    "?nb_pieces=2&regions=12&prix_max=1500"
)

IDF_DEPTS = {"75", "92", "93", "94"}


class LaforetScraper(AbstractScraper):
    def __init__(self, url: str = SEARCH_URL):
        self.url = url

    def fetch_html(self, url: str) -> str:
        api_key = os.environ.get("SCRAPERAPI_KEY", "")
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
        soup = BeautifulSoup(html, "lxml")
        annonces = []
        seen_urls = set()

        # Each listing is an <a> tag linking to /agence-immobiliere/*/louer/*
        # with data-gtm-click-vignette-param containing the human title
        listing_links = [
            a for a in soup.find_all("a", href=True)
            if "/agence-immobiliere/" in a.get("href", "")
            and "/louer/" in a.get("href", "")
            and a.get("data-gtm-click-vignette-param")
        ]

        for a in listing_links:
            href = a.get("href", "").strip()
            if not href:
                continue

            url = href if href.startswith("http") else BASE_URL + href

            # De-duplicate (same listing appears multiple times in page)
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Title from data attribute (e.g. "Appartement T2 Sevran à louer")
            titre = a.get("data-gtm-click-vignette-param", "").strip()

            # Skip colocation listings
            if self.est_colocation(titre):
                continue

            # Price — <span> containing "€/mois"
            prix = None
            price_el = a.select_one("span.text-tertiary")
            if price_el:
                raw = price_el.get_text(separator=" ", strip=True)
                digits = re.sub(r"[^\d]", "", raw.replace("\u00a0", ""))
                if digits:
                    prix = int(digits)

            # City and postal code — <span class="font-bold text-gray-600">
            ville = None
            departement = None
            city_el = a.select_one("span.font-bold.text-gray-600")
            if city_el:
                city_raw = city_el.get_text(separator=" ", strip=True)
                # Extract postal code e.g. "(93270)"
                dept_match = re.search(r"\((\d{5})\)", city_raw)
                if dept_match:
                    departement = dept_match.group(1)[:2]
                # City name: strip the (XXXXX) part
                ville = re.sub(r"\s*\(\d+\)\s*", "", city_raw).strip()

            # Filter to IDF departments only
            if departement not in IDF_DEPTS:
                continue

            # Surface — look for "XX m²" in the text div
            surface = None
            text_div = a.select_one("div.text")
            if text_div:
                surface_text = text_div.get_text(separator=" ", strip=True)
                m = re.search(r"([\d,\.]+)\s*m²", surface_text)
                if m:
                    surface_str = m.group(1).replace(",", ".").replace("\u00a0", "")
                    try:
                        surface = int(float(surface_str))
                    except ValueError:
                        surface = None

            annonces.append(
                {
                    "url": url,
                    "titre": titre,
                    "prix": prix,
                    "surface": surface,
                    "ville": ville,
                    "departement": departement,
                    "source": "laforet",
                }
            )

        return annonces
