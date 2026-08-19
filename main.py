"""
Main Orchestrator for Tariff Policy News Monitoring System.
Runs crawlers, applies 2-stage filtering (Rule + AI), merges events, and updates JSON/CSV.
"""
import os
import sys
import logging
from typing import List
from crawler import (
    TaiwanTradeCrawler,
    USCommerceCrawler,
    CNBCCrawler,
    ReutersCrawler,
    Article,
)
from filter import RuleFilter, AIClassifier
from storage import EventManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TariffMonitor.Main")


def run_pipeline() -> int:
    """Executes the full data collection and monitoring pipeline."""
    logger.info("==================================================")
    logger.info("Starting Tariff Policy Monitoring Pipeline...")
    logger.info("==================================================")

    # 1. Initialize components
    crawlers = [
        TaiwanTradeCrawler(),
        USCommerceCrawler(),
        CNBCCrawler(),
        ReutersCrawler(),
    ]
    rule_filter = RuleFilter()
    ai_classifier = AIClassifier()
    event_manager = EventManager()

    # 2. Fetch raw articles from all sources
    raw_articles: List[Article] = []
    for crawler in crawlers:
        try:
            logger.info(f"Running crawler: {crawler.name}...")
            items = crawler.fetch()
            raw_articles.extend(items)
            logger.info(f"-> {crawler.name} returned {len(items)} raw articles.")
        except Exception as e:
            logger.error(f"Error executing crawler {crawler.name}: {e}")

    logger.info(f"Total raw articles fetched across all sources: {len(raw_articles)}")

    # 3. Stage 1: Rule-based keyword and entity filter
    passed_rule_articles = []
    for article in raw_articles:
        passed, country_pair = rule_filter.is_relevant(article)
        if passed and country_pair:
            passed_rule_articles.append((article, country_pair))

    logger.info(f"Stage 1 Filter: {len(passed_rule_articles)} / {len(raw_articles)} articles passed keyword/country rules.")

    # 4. Stage 2: AI / Semantic classification & deduplication matching
    processed_count = 0
    new_event_count = 0
    updated_event_count = 0

    for article, country_pair in passed_rule_articles:
        logger.info(f"Classifying: [{country_pair}] {article.title[:60]}...")
        result = ai_classifier.classify_and_match(
            article=article,
            country_pair=country_pair,
            existing_events=event_manager.events
        )

        if not result.is_tariff_event:
            logger.info(f"-> Excluded by AI classifier (Not a confirmed tariff event).")
            continue

        prev_count = len(event_manager.events)
        event_id = event_manager.process_article(article, result)
        processed_count += 1

        if len(event_manager.events) > prev_count:
            new_event_count += 1
            logger.info(f"-> [NEW EVENT] {event_id}: {result.event_title}")
        else:
            updated_event_count += 1
            logger.info(f"-> [UPDATED EVENT] {event_id}: timeline appended.")

    # 5. Persist updates to JSON and CSV
    event_manager.save()

    logger.info("==================================================")
    logger.info("Pipeline Execution Summary:")
    logger.info(f" - Raw Articles Crawled: {len(raw_articles)}")
    logger.info(f" - Passed Rule Filter:   {len(passed_rule_articles)}")
    logger.info(f" - Valid Tariff Events:  {processed_count}")
    logger.info(f"   * New Events Created: {new_event_count}")
    logger.info(f"   * Existing Updated:   {updated_event_count}")
    logger.info(f" - Total Database Records: {len(event_manager.events)}")
    logger.info("==================================================")

    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
