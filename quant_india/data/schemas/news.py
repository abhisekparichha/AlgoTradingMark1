from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    source: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    url: Optional[str] = None
    language: str = "en"
    published_at: datetime
    received_at: datetime
    sentiment_score: Optional[float] = None
    sentiment_confidence: Optional[float] = None
    event_type: Optional[str] = None
    symbols: list[str] = Field(default_factory=list)
