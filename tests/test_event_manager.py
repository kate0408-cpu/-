"""
Tests for EventManager JSON and CSV storage and event deduplication.
"""
import os
import json
import pytest
from crawler.base import Article
from filter.ai_classifier import ClassificationResult
from storage.event_manager import EventManager


def test_event_manager_create_and_merge(tmp_path):
    json_file = str(tmp_path / "events.json")
    csv_file = str(tmp_path / "events.csv")

    manager = EventManager(json_path=json_file, csv_path=csv_file)
    assert len(manager.events) == 0

    # 1. Create first event
    art1 = Article(
        title="美方擬對中國電動車加徵 25% 關稅",
        source="Reuters",
        url="https://example.com/ev1",
        published_date="2026-08-18",
        content="預計加徵 25% 關稅",
        summary="預計加徵 25% 關稅",
    )
    res1 = ClassificationResult(
        is_tariff_event=True,
        event_type="新增關稅",
        country_pair="US-CN",
        event_title="美方擬對中國電動車加徵關稅",
        affected_products=["Electric Vehicles (EV)"],
        tariff_rate="25%",
        effective_date="2026-08-18",
        is_existing_event=False,
    )
    ev_id1 = manager.process_article(art1, res1)
    assert ev_id1.startswith("EV-USCN-")
    assert len(manager.events) == 1
    assert len(manager.events[0]["timeline"]) == 1

    # 2. Update existing event
    art2 = Article(
        title="美國商務部宣布對中國電動車關稅調高至 30%",
        source="CNBC",
        url="https://example.com/ev2",
        published_date="2026-08-20",
        content="調整稅率至 30%",
        summary="調整稅率至 30%",
    )
    res2 = ClassificationResult(
        is_tariff_event=True,
        event_type="關稅調高",
        country_pair="US-CN",
        event_title="美國商務部宣布對中國電動車關稅調高至 30%",
        affected_products=["Electric Vehicles (EV)"],
        tariff_rate="30%",
        effective_date="2026-08-20",
        is_existing_event=True,
        matched_event_id=ev_id1,
    )
    ev_id2 = manager.process_article(art2, res2)
    assert ev_id2 == ev_id1
    assert len(manager.events) == 1
    assert len(manager.events[0]["timeline"]) == 2
    assert manager.events[0]["tariff_rate"] == "30%"
    assert "CNBC" in manager.events[0]["sources"]

    # 3. Save and Verify CSV / JSON
    manager.save()
    assert os.path.exists(json_file)
    assert os.path.exists(csv_file)

    with open(json_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)
        assert len(loaded) == 1
