"""
CNBC Financial News Crawler.
"""
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
from crawler.base import BaseCrawler, Article


class CNBCCrawler(BaseCrawler):
    """Crawler for CNBC international trade, economy, and tariff policy news."""

    RSS_URLS = [
        "https://search.cnbc.com/rs/search/combinedList/view.xml?partnerId=wrss01&id=10001147", # International Trade / Business
        "https://search.cnbc.com/rs/search/combinedList/view.xml?partnerId=wrss01&id=20910258", # Economy
        "https://search.cnbc.com/rs/search/combinedList/view.xml?partnerId=wrss01&id=19832390", # Asia Pacific
        "https://search.cnbc.com/rs/search/combinedList/view.xml?partnerId=wrss01&id=100003114", # Top News
        "https://news.google.com/rss/search?q=site:cnbc.com+(tariff+OR+trade+OR+commerce)+when:7d&hl=en-US&gl=US&ceid=US:en",
    ]

    def __init__(self):
        super().__init__(name="CNBC")

    def fetch(self) -> List[Article]:
        articles: List[Article] = []
        seen_urls = set()

        for rss_url in self.RSS_URLS:
            try:
                resp = self.session.get(rss_url, timeout=self.timeout)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.content, "xml")
                    items = soup.find_all("item")
                    for item in items:
                        title = item.find("title").get_text(strip=True) if item.find("title") else ""
                        link = item.find("link").get_text(strip=True) if item.find("link") else ""
                        pub_date = item.find("pubDate").get_text(strip=True) if item.find("pubDate") else ""
                        desc = item.find("description").get_text(strip=True) if item.find("description") else ""

                        if not title or not link or link in seen_urls:
                            continue

                        formatted_date = datetime.now().strftime("%Y-%m-%d")
                        if pub_date:
                            try:
                                dt = datetime.strptime(pub_date[:25].strip(), "%a, %d %b %Y %H:%M:%S")
                                formatted_date = dt.strftime("%Y-%m-%d")
                            except Exception:
                                pass

                        seen_urls.add(link)
                        articles.append(Article(
                            title=title,
                            source="CNBC",
                            url=link,
                            published_date=formatted_date,
                            content=desc or title,
                            summary=desc[:250] if desc else title,
                        ))
            except Exception as e:
                self.logger.warning(f"Error parsing CNBC RSS {rss_url}: {e}")

        self.logger.info(f"Fetched {len(articles)} articles from CNBC")
        return articles
