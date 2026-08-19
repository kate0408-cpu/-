"""
Taiwan International Trade Administration (經濟部國際貿易署) Crawler.
"""
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from crawler.base import BaseCrawler, Article


class TaiwanTradeCrawler(BaseCrawler):
    """Crawler for Taiwan International Trade Administration (國貿署) announcements and trade news."""

    RSS_URLS = [
        "https://www.trade.gov.tw/RSS/RSS.aspx?nodeID=45",  # 即時商情 / 新聞
        "https://www.trade.gov.tw/RSS/RSS.aspx?nodeID=22",  # 經貿新聞
    ]
    NEWS_URL = "https://www.trade.gov.tw/Pages/List.aspx?nodeID=45"

    def __init__(self):
        super().__init__(name="Taiwan_Trade")

    def fetch(self) -> List[Article]:
        articles: List[Article] = []
        seen_urls = set()

        # 1. Try RSS Feeds
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

                        # Format date
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
                            source="台灣經濟部國際貿易署",
                            url=link,
                            published_date=formatted_date,
                            content=desc or title,
                            summary=desc[:200] if desc else title,
                        ))
            except Exception as e:
                self.logger.warning(f"Failed to parse Taiwan Trade RSS {rss_url}: {e}")

        # 2. If RSS returned empty, fallback to HTML list
        if not articles:
            try:
                html = self.get_html(self.NEWS_URL)
                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    # Find news links
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag["href"]
                        if "Detail.aspx" in href and a_tag.get_text(strip=True):
                            title = a_tag.get_text(strip=True)
                            if not href.startswith("http"):
                                full_url = f"https://www.trade.gov.tw/Pages/{href}"
                            else:
                                full_url = href
                            if full_url not in seen_urls:
                                seen_urls.add(full_url)
                                articles.append(Article(
                                    title=title,
                                    source="台灣經濟部國際貿易署",
                                    url=full_url,
                                    published_date=datetime.now().strftime("%Y-%m-%d"),
                                    content=title,
                                    summary=title,
                                ))
            except Exception as e:
                self.logger.warning(f"Failed to parse Taiwan Trade HTML: {e}")

        self.logger.info(f"Fetched {len(articles)} articles from Taiwan Trade Administration")
        return articles
