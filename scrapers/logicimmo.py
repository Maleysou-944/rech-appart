from typing import List, Dict
from .base import AbstractScraper


class LogicImmoScraper(AbstractScraper):
    """Stub — will be implemented in Task 4."""

    def __init__(self, url: str = ""):
        self.url = url

    def fetch_html(self, url: str) -> str:
        raise NotImplementedError("LogicImmoScraper not yet implemented")

    def parse(self, html: str) -> List[Dict]:
        raise NotImplementedError("LogicImmoScraper not yet implemented")
