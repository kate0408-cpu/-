"""
Tests for RuleFilter and AIClassifier modules.
"""
import pytest
from crawler.base import Article
from filter.rule_filter import RuleFilter
from filter.ai_classifier import AIClassifier


def test_rule_filter_relevant_article():
    filter = RuleFilter()
    
    # Relevant US-TW tariff article
    art1 = Article(
        title="台美經貿會議聚焦關稅調降與半導體供應鏈合作",
        source="台灣經濟部國際貿易署",
        url="https://example.com/1",
        published_date="2026-08-19",
        content="美方與台灣代表討論關於鋼鐵與電子零組件關稅豁免議題。"
    )
    passed, pair = filter.is_relevant(art1)
    assert passed is True
    assert pair == "US-TW"

    # Relevant US-CN tariff article
    art2 = Article(
        title="US imposes 25% tariffs on Chinese EV batteries and solar cells",
        source="Reuters",
        url="https://example.com/2",
        published_date="2026-08-19",
        content="The United States announced new tariffs targeting Chinese green tech imports."
    )
    passed, pair = filter.is_relevant(art2)
    assert passed is True
    assert pair == "US-CN"


def test_rule_filter_irrelevant_and_exclusion():
    filter = RuleFilter()
    
    # Irrelevant general news
    art_irrelevant = Article(
        title="歐洲央行宣布維持基準利率不變",
        source="CNBC",
        url="https://example.com/3",
        published_date="2026-08-19",
        content="歐洲央行今日決議不調整利率水準。"
    )
    passed, pair = filter.is_relevant(art_irrelevant)
    assert passed is False

    # Exclusion: pure speculation
    art_speculation = Article(
        title="分析師預測美中關稅可能在下半年出現變化",
        source="Reuters",
        url="https://example.com/4",
        published_date="2026-08-19",
        content="民間猜測若國際局勢變更，關稅或將調整，純屬學者個人觀點。"
    )
    passed, pair = filter.is_relevant(art_speculation)
    assert passed is False


def test_ai_classifier_heuristic():
    classifier = AIClassifier()
    art = Article(
        title="美國商務部宣布對中國鋼鐵產品反制關稅正式生效施行",
        source="U.S. Department of Commerce",
        url="https://example.com/5",
        published_date="2026-08-19",
        content="自今日起對特定鋼鐵加徵 30% 關稅正式生效。"
    )
    res = classifier.classify_and_match(art, "US-CN", [])
    assert res.is_tariff_event is True
    assert res.event_type == "已正式生效的關稅政策"
    assert "Steel" in res.affected_products
    assert res.tariff_rate == "30%"
    assert res.country_pair == "US-CN"
