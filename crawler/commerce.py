"""
U.S. Department of Commerce / International Trade Administration (ITA) Crawler.
"""
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
import re
from crawler.base import BaseCrawler, Article


class USCommerceCrawler(BaseCrawler):
    """Crawler for U.S. Department of Commerce official trade and tariff announcements."""

    COMMERCE_RSS = "https://www.commerce.gov/rss/news/press-releases.xml"
    COMMERCE_NEWS_URL = "https://www.commerce.gov/news/press-releases"
    TRADE_GOV_URL = "https://www.trade.gov/press-releases"
    FALLBACK_FEED = "https://news.google.com/rss/search?q=(site:commerce.gov+OR+site:trade.gov)+(tariff+OR+trade+OR+export+OR+import)&hl=en-US&gl=US&ceid=US:en"

    def __init__(self):
        super().__init__(name="US_Commerce")

    def fetch(self) -> List[Article]:
        articles: List[Article] = []
        seen_urls = set()

        # 1. Try Commerce RSS
        try:
            resp = self.session.get(self.COMMERCE_RSS, timeout=self.timeout)
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
                            # e.g., Thu, 15 Aug 2024 14:00:00 +0000
                            dt = datetime.strptime(pub_date[:25].strip(), "%a, %d %b %Y %H:%M:%S")
                            formatted_date = dt.strftime("%Y-%m-%d")
                        except Exception:
                            pass

                    seen_urls.add(link)
                    articles.append(Article(
                        title=title,
                        source="U.S. Department of Commerce",
                        url=link,
                        published_date=formatted_date,
                        content=desc or title,
                        summary=desc[:250] if desc else title,
                    ))
        except Exception as e:
            self.logger.warning(f"Error fetching U.S. Commerce RSS: {e}")

        # 2. Try Fallback Google News Commerce Feed
        if len(articles) < 5:
            try:
                resp = self.session.get(self.FALLBACK_FEED, timeout=self.timeout)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.content, "xml")
                    for item in soup.find_all("item"):
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
                            source="U.S. Department of Commerce",
                            url=link,
                            published_date=formatted_date,
                            content=desc or title,
                            summary=desc[:250] if desc else title,
                        ))
            except Exception as e:
                self.logger.warning(f"Error fetching Fallback Commerce Feed: {e}")

        # 2. HTML fallback if RSS returned few or none
        if len(articles) < 5:
            try:
                html = self.get_html(self.COMMERCE_NEWS_URL)
                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    # Look for article blocks or links in press release lists
                    for item in soup.select("article, .views-row, h3 a, h2 a"):
                        a_tag = item if item.name == "a" else item.find("a", href=True)
                        if not a_tag:
                            continue
                        href = a_tag.get("href", "")
                        title = a_tag.get_text(strip=True)
                        if not title or not href:
                            continue

                        full_url = href if href.startswith("http") else f"https://www.commerce.gov{href}"
                        if full_url in seen_urls:
                            continue

                        seen_urls.add(full_url)
                        articles.append(Article(
                            title=title,
                            source="U.S. Department of Commerce",
                            url=full_url,
                            published_date=datetime.now().strftime("%Y-%m-%d"),
                            content=title,
                            summary=title,
                        ))
            except Exception as e:
                self.logger.warning(f"Error fetching U.S. Commerce HTML: {e}")

        self.logger.info(f"Fetched {len(articles)} articles from U.S. Department of Commerce")
        return articles
