from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


EVENT_KEYWORDS = {
    "earnings": ["earnings", "profit", "revenue", "guidance", "quarter"],
    "regulatory": ["sebi", "penalty", "regulator", "fine", "ban", "probe"],
    "corporate_action": ["dividend", "split", "bonus", "buyback", "merger"],
    "macro": ["inflation", "cpi", "gdp", "policy", "rate", "budget"],
    "flow": ["fii", "dii", "inflow", "outflow", "stake", "block"],
}


@dataclass
class EventClassifier:
    def classify(self, text: str) -> Tuple[str, float]:
        text_lower = text.lower()
        for event_type, keywords in EVENT_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    severity = 0.8 if event_type in {"regulatory", "corporate_action"} else 0.6
                    return event_type, severity
        return "general", 0.3
