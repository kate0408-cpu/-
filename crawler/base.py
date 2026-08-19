"""
Base crawler class and data structures for tariff policy monitoring.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("Crawler")


@dataclass
class Article:
    """Standardized article data representation."""
    title: str
    source: str
    url: str
    published_date: str
    content: str
    summary: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "published_date": self.published_date,
            "content": self.content,
            "summary": self.summary,
        }


class BaseCrawler:
    """Base class for all news and government announcement crawlers."""

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-TW;q=0.8,zh;q=0.7",
    }

    def __init__(self, name: str, timeout: int = 15):
        self.name = name
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self.logger = logging.getLogger(f"Crawler.{name}")

    def fetch(self) -> List[Article]:
        """Fetch and return list of articles. Subclasses must implement this."""
        raise NotImplementedError("Subclasses must implement fetch()")

    def get_html(self, url: str, headers: Optional[dict] = None) -> Optional[str]:
        """Helper to get HTML response safely."""
        try:
            req_headers = self.DEFAULT_HEADERS.copy()
            if headers:
                req_headers.update(headers)
            resp = self.session.get(url, headers=req_headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            self.logger.warning(f"Error fetching URL {url}: {e}")
            return None
