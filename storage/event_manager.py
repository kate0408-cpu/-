"""
Event Manager module for JSON storage, Timeline merging, and CSV export.
"""
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd
from crawler.base import Article
from filter.ai_classifier import ClassificationResult

logger = logging.getLogger("Storage.EventManager")


class EventManager:
    """Manages the lifecycle, deduplication merging, and dual-format (JSON + CSV) storage."""

    def __init__(self, json_path: str = "data/events.json", csv_path: str = "data/events.csv"):
        self.json_path = json_path
        self.csv_path = csv_path
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        self.events: List[Dict[str, Any]] = self._load_json()

    def _load_json(self) -> List[Dict[str, Any]]:
        """Load events from JSON file."""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                logger.error(f"Failed to load JSON from {self.json_path}: {e}")
        return []

    def save(self):
        """Save events to JSON and export to CSV."""
        # 1. Save JSON
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.events, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(self.events)} events to {self.json_path}")

        # 2. Export CSV
        self.export_csv()

    def export_csv(self):
        """Export flat summary of events to CSV (utf-8-sig for Excel compatibility)."""
        rows = []
        for ev in self.events:
            # Get latest source and timeline count
            timeline = ev.get("timeline", [])
            sources = ", ".join(list(set(ev.get("sources", []))))
            products = ", ".join(ev.get("affected_products", []))
            
            rows.append({
                "事件ID (event_id)": ev.get("event_id"),
                "國家/區域 (country_pair)": ev.get("country_pair"),
                "事件類型 (event_type)": ev.get("event_type"),
                "事件標題 (title)": ev.get("title"),
                "受影響產品 (affected_products)": products,
                "關稅稅率 (tariff_rate)": ev.get("tariff_rate") or "未提及",
                "生效/公布日期 (effective_date)": ev.get("effective_date"),
                "首次建立時間 (created_at)": ev.get("created_at"),
                "最後更新時間 (last_updated)": ev.get("last_updated"),
                "資訊來源 (sources)": sources,
                "歷程筆數 (timeline_count)": len(timeline),
                "分類信心度 (classification_confidence)": ev.get("classification_confidence", 1.0),
            })

        df = pd.DataFrame(rows)
        # Ensure utf-8-sig encoding for seamless Excel opening on Windows
        df.to_csv(self.csv_path, index=False, encoding="utf-8-sig")
        logger.info(f"Exported {len(rows)} rows to {self.csv_path}")

    def generate_event_id(self, country_pair: str) -> str:
        """Generate unique event ID (e.g. EV-USTW-20260819-001)."""
        prefix = "USTW" if "TW" in country_pair else "USCN"
        date_str = datetime.now().strftime("%Y%m%d")
        existing_today = [
            e for e in self.events 
            if e.get("event_id", "").startswith(f"EV-{prefix}-{date_str}")
        ]
        seq = len(existing_today) + 1
        return f"EV-{prefix}-{date_str}-{seq:03d}"

    def process_article(self, article: Article, result: ClassificationResult) -> str:
        """
        Processes a classified article: creates new event or updates existing event timeline.
        Returns the event_id.
        """
        # Check if URL already exists in sources to prevent duplicate updates from identical articles
        for ev in self.events:
            for item in ev.get("timeline", []):
                if item.get("url") == article.url:
                    logger.info(f"Article URL {article.url} already in event {ev['event_id']}, skipping duplicate timeline item.")
                    return ev["event_id"]

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Update Existing Event
        if result.is_existing_event and result.matched_event_id:
            for ev in self.events:
                if ev["event_id"] == result.matched_event_id:
                    # Update event details
                    if result.event_type and result.event_type != ev["event_type"]:
                        ev["event_type"] = result.event_type
                    if result.tariff_rate:
                        ev["tariff_rate"] = result.tariff_rate
                    for p in result.affected_products:
                        if p not in ev["affected_products"]:
                            ev["affected_products"].append(p)
                    if article.source not in ev["sources"]:
                        ev["sources"].append(article.source)
                    ev["last_updated"] = now_str

                    # Append timeline record
                    ev["timeline"].append({
                        "date": article.published_date,
                        "recorded_at": now_str,
                        "source": article.source,
                        "url": article.url,
                        "title": article.title,
                        "event_type": result.event_type,
                        "tariff_rate": result.tariff_rate,
                        "summary": article.summary,
                    })
                    logger.info(f"Updated existing event {ev['event_id']} with article from {article.source}")
                    return ev["event_id"]

        # 2. Create New Event
        event_id = self.generate_event_id(result.country_pair)
        new_event = {
            "event_id": event_id,
            "country_pair": result.country_pair,
            "event_type": result.event_type,
            "title": result.event_title,
            "affected_products": result.affected_products,
            "tariff_rate": result.tariff_rate,
            "effective_date": result.effective_date,
            "created_at": now_str,
            "last_updated": now_str,
            "sources": [article.source],
            "classification_confidence": result.classification_confidence,
            "timeline": [
                {
                    "date": article.published_date,
                    "recorded_at": now_str,
                    "source": article.source,
                    "url": article.url,
                    "title": article.title,
                    "event_type": result.event_type,
                    "tariff_rate": result.tariff_rate,
                    "summary": article.summary,
                }
            ],
        }
        self.events.insert(0, new_event)
        logger.info(f"Created new event {event_id}: {result.event_title}")
        return event_id
