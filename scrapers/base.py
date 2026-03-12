from abc import ABC, abstractmethod
from typing import List, Dict


class AbstractScraper(ABC):
    COLOC_KEYWORDS = ("colocation", "coloc", "chambre chez", "chambre en ")

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
