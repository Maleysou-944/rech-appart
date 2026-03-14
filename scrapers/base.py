import re
from abc import ABC, abstractmethod
from typing import List, Dict


class AbstractScraper(ABC):
    COLOC_KEYWORDS = ("colocation", "coloc", "chambre chez", "chambre en ")

    @staticmethod
    def detect_type_bien(text: str):
        m = re.search(r'\bT([123])\b', text, re.IGNORECASE)
        if m:
            return f"T{m.group(1)}"
        m = re.search(r'(\d)\s*pièces?', text, re.IGNORECASE)
        if m and 1 <= int(m.group(1)) <= 3:
            return f"T{m.group(1)}"
        return None

    @abstractmethod
    def fetch_html(self, url: str) -> str:
        pass

    @abstractmethod
    def parse(self, html: str) -> List[Dict]:
        pass

    def scrape(self) -> List[Dict]:
        html = self.fetch_html(self.url)
        return self.parse(html)

    def est_colocation(self, titre: str) -> bool:
        """Retourne True si le titre indique une colocation à exclure."""
        titre_lower = titre.lower()
        return any(kw in titre_lower for kw in self.COLOC_KEYWORDS)
