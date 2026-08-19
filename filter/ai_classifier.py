"""
AI and Semantic Classification & Deduplication Module.
"""
import os
import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from crawler.base import Article

logger = logging.getLogger("Filter.AIClassifier")

VALID_EVENT_TYPES = [
    "新增關稅",
    "關稅調高",
    "關稅調降",
    "關稅取消／暫停",
    "關稅豁免",
    "反制關稅",
    "關稅談判／協議",
    "已正式生效的關稅政策",
]


@dataclass
class ClassificationResult:
    """Structured result from AI / Semantic classification."""
    is_tariff_event: bool
    event_type: str
    country_pair: str
    event_title: str
    affected_products: List[str] = field(default_factory=list)
    tariff_rate: Optional[str] = None
    effective_date: Optional[str] = None
    is_existing_event: bool = False
    matched_event_id: Optional[str] = None
    same_event_confidence: float = 0.0
    classification_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_tariff_event": self.is_tariff_event,
            "event_type": self.event_type,
            "country_pair": self.country_pair,
            "event_title": self.event_title,
            "affected_products": self.affected_products,
            "tariff_rate": self.tariff_rate,
            "effective_date": self.effective_date,
            "is_existing_event": self.is_existing_event,
            "matched_event_id": self.matched_event_id,
            "same_event_confidence": round(self.same_event_confidence, 2),
            "classification_confidence": round(self.classification_confidence, 2),
        }


class AIClassifier:
    """Classifier handling semantic categorization and deduplication matching."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.use_llm = False
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-1.5-flash")
                self.use_llm = True
                logger.info("Initialized Gemini LLM Classifier")
            except Exception as e:
                logger.warning(f"Could not initialize Gemini API ({e}); falling back to heuristic engine.")

    def classify_and_match(
        self,
        article: Article,
        country_pair: str,
        existing_events: List[Dict[str, Any]]
    ) -> ClassificationResult:
        """Classifies an article and matches it against existing events."""
        if self.use_llm:
            try:
                return self._classify_with_llm(article, country_pair, existing_events)
            except Exception as e:
                logger.warning(f"LLM classification failed ({e}); falling back to heuristic.")

        return self._classify_heuristic(article, country_pair, existing_events)

    def _classify_heuristic(
        self,
        article: Article,
        country_pair: str,
        existing_events: List[Dict[str, Any]]
    ) -> ClassificationResult:
        """Heuristic NLP classifier with high-precision pattern matching."""
        text = f"{article.title} {article.content} {article.summary}"

        # 1. Determine Event Type
        event_type = "新增關稅"
        confidence = 0.85

        if any(k in text for k in ["生效", "施行", "實施", "effective", "takes effect", "enacted"]):
            event_type = "已正式生效的關稅政策"
            confidence = 0.92
        elif any(k in text for k in ["反制", "報復", "retaliatory", "retaliation", "counter-tariff"]):
            event_type = "反制關稅"
            confidence = 0.90
        elif any(k in text for k in ["豁免", "排除", "exemption", "exclude", "waiver"]):
            event_type = "關稅豁免"
            confidence = 0.88
        elif any(k in text for k in ["調降", "降低", "減稅", "cut", "decrease", "reduce tariffs"]):
            event_type = "關稅調降"
            confidence = 0.86
        elif any(k in text for k in ["調高", "提高", "增至", "hike", "raise", "increase tariff"]):
            event_type = "關稅調高"
            confidence = 0.88
        elif any(k in text for k in ["取消", "暫停", "終止", "suspend", "cancel", "terminate tariff"]):
            event_type = "關稅取消／暫停"
            confidence = 0.88
        elif any(k in text for k in ["談判", "協商", "協議", "negotiation", "talks", "deal", "agreement"]):
            event_type = "關稅談判／協議"
            confidence = 0.85

        # 2. Extract Tariff Rate
        rate_match = re.search(r"(\d+(?:\.\d+)?\s*%)", text)
        tariff_rate = rate_match.group(1).replace(" ", "") if rate_match else None

        # 3. Extract Affected Products
        products = []
        product_keywords = [
            ("半導體", "Semiconductors / Chips"),
            ("晶片", "Semiconductors / Chips"),
            ("電動車", "Electric Vehicles (EV)"),
            ("鋼鐵", "Steel"),
            ("鋁", "Aluminum"),
            ("太陽能", "Solar Products"),
            ("鋰電池", "Lithium-ion Batteries"),
            ("農產品", "Agricultural Products"),
            ("醫療器材", "Medical Supplies"),
            ("工具機", "Machine Tools"),
            ("資通訊", "ICT Products"),
            ("semiconductor", "Semiconductors / Chips"),
            ("chip", "Semiconductors / Chips"),
            ("steel", "Steel"),
            ("aluminum", "Aluminum"),
            ("solar", "Solar Products"),
            ("battery", "Batteries"),
            ("electric vehicle", "Electric Vehicles (EV)"),
            ("ev", "Electric Vehicles (EV)"),
        ]
        for kw, prod in product_keywords:
            if re.search(rf"\b{kw}\b" if kw.isascii() else kw, text, re.IGNORECASE):
                if prod not in products:
                    products.append(prod)

        if not products:
            products = ["General Merchandise / 綜合商品"]

        # 4. Generate Clean Event Title
        clean_title = article.title
        for prefix in ["[即時]", "【快訊】", "Reuters - ", "CNBC - "]:
            clean_title = clean_title.replace(prefix, "")
        clean_title = clean_title.strip()

        # 5. Deduplication and Event Matching against existing events
        best_match_id = None
        highest_match_score = 0.0

        for ev in existing_events:
            if ev.get("country_pair") != country_pair:
                continue

            # Compare keywords and product overlap
            ev_title = ev.get("title", "")
            ev_products = ev.get("affected_products", [])

            # Product overlap
            prod_overlap = len(set(products) & set(ev_products)) > 0
            
            # Simple token similarity
            words_a = set(re.findall(r"\w+", clean_title.lower()))
            words_b = set(re.findall(r"\w+", ev_title.lower()))
            jaccard = len(words_a & words_b) / max(len(words_a | words_b), 1)

            score = jaccard * 0.7 + (0.3 if prod_overlap else 0.0)
            if score > highest_match_score:
                highest_match_score = score
                best_match_id = ev.get("event_id")

        is_existing = highest_match_score >= 0.45 and best_match_id is not None

        return ClassificationResult(
            is_tariff_event=True,
            event_type=event_type,
            country_pair=country_pair,
            event_title=clean_title,
            affected_products=products,
            tariff_rate=tariff_rate,
            effective_date=article.published_date,
            is_existing_event=is_existing,
            matched_event_id=best_match_id if is_existing else None,
            same_event_confidence=highest_match_score if is_existing else (1.0 - highest_match_score),
            classification_confidence=confidence,
        )

    def _classify_with_llm(
        self,
        article: Article,
        country_pair: str,
        existing_events: List[Dict[str, Any]]
    ) -> ClassificationResult:
        """Call Gemini LLM with structured prompt."""
        existing_summary = [
            {"event_id": e["event_id"], "title": e["title"], "type": e.get("event_type"), "products": e.get("affected_products")}
            for e in existing_events[-10:] # last 10 events
        ]

        prompt = f"""
You are a trade policy and tariff intelligence analyzer.
Analyze the following article regarding tariffs between {country_pair}.

Article Title: {article.title}
Article Source: {article.source}
Article Content: {article.content}

Candidate Event Types:
{json.dumps(VALID_EVENT_TYPES, ensure_ascii=False)}

Existing Events in Database:
{json.dumps(existing_summary, ensure_ascii=False)}

Task:
1. Confirm if it is a genuine tariff policy event (is_tariff_event). Exclude pure speculative rumors.
2. Identify the specific event_type from the candidates list.
3. Extract affected_products (list of strings).
4. Extract tariff_rate (e.g. "25%") or null.
5. Check if it matches an existing event from the list (is_existing_event & matched_event_id).
6. Give classification_confidence (0.0 to 1.0) and same_event_confidence (0.0 to 1.0).

Respond ONLY with valid JSON matching this schema:
{{
  "is_tariff_event": true,
  "event_type": "新增關稅",
  "event_title": "Concise headline in Chinese or English",
  "affected_products": ["Semiconductors"],
  "tariff_rate": "25%",
  "effective_date": "2026-08-19",
  "is_existing_event": false,
  "matched_event_id": null,
  "same_event_confidence": 0.95,
  "classification_confidence": 0.95
}}
"""
        response = self.model.generate_content(prompt)
        text = response.text.strip()
        # Clean JSON markdown fences if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        data = json.loads(text.strip())

        return ClassificationResult(
            is_tariff_event=data.get("is_tariff_event", True),
            event_type=data.get("event_type", "新增關稅"),
            country_pair=country_pair,
            event_title=data.get("event_title", article.title),
            affected_products=data.get("affected_products", []),
            tariff_rate=data.get("tariff_rate"),
            effective_date=data.get("effective_date", article.published_date),
            is_existing_event=data.get("is_existing_event", False),
            matched_event_id=data.get("matched_event_id"),
            same_event_confidence=float(data.get("same_event_confidence", 0.9)),
            classification_confidence=float(data.get("classification_confidence", 0.9)),
        )
