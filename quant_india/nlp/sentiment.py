from __future__ import annotations

import math
from typing import Tuple


POSITIVE_WORDS = {
    "growth",
    "beat",
    "surge",
    "upgrade",
    "strong",
    "robust",
    "outperform",
    "positive",
    "gain",
    "record",
}

NEGATIVE_WORDS = {
    "loss",
    "downgrade",
    "fraud",
    "decline",
    "drop",
    "weak",
    "negative",
    "default",
    "penalty",
    "probe",
}


class SentimentAnalyzer:
    """
    Lightweight lexicon-based sentiment scorer suitable for initial pipelines.
    Replace with transformer-backed scorer in production.
    """

    def score(self, text: str) -> Tuple[float, float]:
        tokens = [token.lower() for token in text.split()]
        pos_count = sum(token in POSITIVE_WORDS for token in tokens)
        neg_count = sum(token in NEGATIVE_WORDS for token in tokens)
        total = pos_count + neg_count
        if total == 0:
            return 0.0, 0.2
        score = (pos_count - neg_count) / total
        confidence = min(1.0, math.log1p(total) / 2)
        return score, confidence
