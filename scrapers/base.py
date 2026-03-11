from abc import ABC, abstractmethod
from typing import List, Dict


class AbstractScraper(ABC):
    @abstractmethod
    def fetch_html(self, url: str) -> str:
        pass

    @abstractmethod
    def parse(self, html: str) -> List[Dict]:
        pass

    def scrape(self) -> List[Dict]:
        html = self.fetch_html(self.url)
        return self.parse(html)
