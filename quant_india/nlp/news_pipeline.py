from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

import pandas as pd

from quant_india.nlp.entity_linking import EntityLinker
from quant_india.nlp.events import EventClassifier
from quant_india.nlp.sentiment import SentimentAnalyzer


@dataclass
class NewsPipeline:
    sentiment_analyzer: SentimentAnalyzer = field(default_factory=SentimentAnalyzer)
    event_classifier: EventClassifier = field(default_factory=EventClassifier)
    entity_linker: EntityLinker = field(default_factory=EntityLinker)

    def process(self, news_df: pd.DataFrame) -> pd.DataFrame:
        df = news_df.copy()
        text_series = df["title"].fillna("") + " " + df.get("description", "").fillna("")
        sentiments = text_series.apply(self.sentiment_analyzer.score)
        df["sentiment_score"] = sentiments.apply(lambda x: x[0])
        df["sentiment_confidence"] = sentiments.apply(lambda x: x[1])
        events = text_series.apply(self.event_classifier.classify)
        df["event_type"] = events.apply(lambda x: x[0])
        df["event_severity"] = events.apply(lambda x: x[1])
        df["symbols"] = (
            text_series.apply(self.entity_linker.link) if self.entity_linker.name_to_symbol else [[]] * len(df)
        )
        return df

    def with_entity_mapping(self, mappings: Iterable[tuple[str, str]]) -> "NewsPipeline":
        self.entity_linker = EntityLinker.from_mappings(mappings)
        return self
