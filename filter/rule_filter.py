"""
Rule-based keyword and entity filter for tariff monitoring.
"""
import re
from typing import Optional, Tuple
from crawler.base import Article


class RuleFilter:
    """Stage 1 Rule-based Filter: Pre-screens articles based on keywords and country pairs."""

    # Keywords for Tariffs
    TARIFF_KEYWORDS_ZH = [
        "關稅", "反傾銷", "平衡稅", "貿易制裁", "貿易協議", "貿易協定", 
        "加徵", "豁免", "清單", "301條款", "232條款", "貿易談判"
    ]
    TARIFF_KEYWORDS_EN = [
        "tariff", "tariffs", "customs duty", "duties", "anti-dumping", 
        "countervailing", "section 301", "section 232", "trade agreement", 
        "trade dispute", "trade sanction", "trade pact", "trade barrier"
    ]

    # Country Entities
    US_KEYWORDS = ["美國", "美方", "華府", "白宮", "拜登", "川普", "商務部", "ustr", "u.s.", "united states", "america", "biden", "trump", "washington"]
    TW_KEYWORDS = ["台灣", "臺灣", "台北", "台美", "國貿署", "taiwan", "taipei", "taiwanese"]
    CN_KEYWORDS = ["中國", "中共", "北京", "中方", "華", "china", "chinese", "beijing", "prc"]

    # Exclusions (unverified rumors, purely hypothetical discussions)
    EXCLUSION_PATTERNS = [
        r"(純屬學者|專家個人觀點|分析師預測|民間猜測)",
        r"(analyst predicts|speculation mounts|unconfirmed rumor|hypothetical scenario)",
    ]

    def __init__(self):
        # Compile regexes
        self.tariff_pattern = re.compile(
            "|".join(self.TARIFF_KEYWORDS_ZH + [rf"\b{k}\b" for k in self.TARIFF_KEYWORDS_EN]),
            re.IGNORECASE
        )
        self.us_pattern = re.compile("|".join(self.US_KEYWORDS), re.IGNORECASE)
        self.tw_pattern = re.compile("|".join(self.TW_KEYWORDS), re.IGNORECASE)
        self.cn_pattern = re.compile("|".join(self.CN_KEYWORDS), re.IGNORECASE)

    def is_relevant(self, article: Article) -> Tuple[bool, Optional[str]]:
        """
        Check if the article passes the rule filter.
        Returns (is_passed, country_pair) where country_pair is 'US-TW', 'US-CN', or None.
        """
        text = f"{article.title} {article.content} {article.summary}"

        # 1. Check exclusion patterns
        for pattern in self.EXCLUSION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, None

        # 2. Check tariff keywords
        if not self.tariff_pattern.search(text):
            return False, None

        # 3. Check country pairs
        has_us = bool(self.us_pattern.search(text))
        has_tw = bool(self.tw_pattern.search(text))
        has_cn = bool(self.cn_pattern.search(text))

        # Special case: Taiwan Trade Administration articles are inherently TW-related
        if article.source == "台灣經濟部國際貿易署":
            has_tw = True
            # If mentions US or global tariffs affecting US-TW
            if has_us:
                return True, "US-TW"

        # Special case: US Commerce articles are inherently US-related
        if article.source == "U.S. Department of Commerce":
            has_us = True
            if has_tw:
                return True, "US-TW"
            if has_cn:
                return True, "US-CN"

        if has_us and has_tw:
            return True, "US-TW"
        elif has_us and has_cn:
            return True, "US-CN"

        return False, None
