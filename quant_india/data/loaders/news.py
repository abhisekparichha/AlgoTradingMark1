from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional

import pandas as pd
import requests

from quant_india.common import get_settings
from quant_india.common.time import ist_now
from quant_india.data.loaders.base import BaseIngestionJob
from quant_india.data.writer import write_partitioned

PLACEHOLDER = "<<"


class NewsAPIIngestion(BaseIngestionJob):
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(source="news_api")
        self.settings = get_settings()
        self.api_key = api_key or self.settings.data_sources.nse_api_key  # reuse if configured
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "quant-india-system"})

    def _can_call_api(self) -> bool:
        return self.api_key and PLACEHOLDER not in self.api_key

    def fetch(
        self,
        symbols: Iterable[str],
        start: datetime,
        end: datetime,
        interval: str = "realtime",
        language: str = "en",
        page_size: int = 50,
        max_pages: int = 3,
        **kwargs,
    ) -> pd.DataFrame:
        keywords = kwargs.get("keywords") or list(symbols)
        if not keywords:
            keywords = ["NIFTY", "SENSEX"]
        if self._can_call_api():
            return self._fetch_from_api(
                keywords=keywords,
                start=start,
                end=end,
                language=language,
                page_size=page_size,
                max_pages=max_pages,
            )
        return self._simulate(keywords=keywords, start=start, end=end)

    def _fetch_from_api(
        self,
        keywords: list[str],
        start: datetime,
        end: datetime,
        language: str,
        page_size: int,
        max_pages: int,
    ) -> pd.DataFrame:
        query = " OR ".join(keywords)
        params = {
            "q": query,
            "from": pd.Timestamp(start).isoformat(),
            "to": pd.Timestamp(end).isoformat(),
            "apiKey": self.api_key,
            "language": language,
            "pageSize": page_size,
            "sortBy": "publishedAt",
        }
        articles = []
        for page in range(1, max_pages + 1):
            params["page"] = page
            response = self.session.get("https://newsapi.org/v2/everything", params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            batch = payload.get("articles", [])
            if not batch:
                break
            articles.extend(batch)
            if len(batch) < page_size:
                break
        return self._to_dataframe(articles)

    def _simulate(self, keywords: list[str], start: datetime, end: datetime) -> pd.DataFrame:
        timestamp_range = pd.date_range(
            start=start, end=end, freq="2H", inclusive="left", tz="Asia/Kolkata"
        ).tz_convert("UTC")
        rows = []
        for ts in timestamp_range:
            for keyword in keywords[:3]:
                rows.append(
                    {
                        "source": "Simulated Times",
                        "title": f"{keyword} updates drive market sentiment",
                        "description": f"Simulated story for {keyword} at {ts.isoformat()}",
                        "content": "Placeholder content for unit testing and demos.",
                        "url": "https://example.com/news",
                        "language": "en",
                        "publishedAt": ts,
                    }
                )
        return self._to_dataframe(rows)

    def _to_dataframe(self, articles: list[dict]) -> pd.DataFrame:
        if not articles:
            return pd.DataFrame()
        df = pd.DataFrame(articles)
        if "publishedAt" in df.columns:
            df["publishedAt"] = pd.to_datetime(df["publishedAt"], utc=True)
        else:
            df["publishedAt"] = ist_now().tz_convert("UTC")
        df["received_at"] = ist_now().tz_convert("UTC")
        df["source_name"] = df.get("source").apply(lambda x: x.get("name") if isinstance(x, dict) else x)
        df["source"] = self.source
        df["interval"] = "news"
        df["sentiment_score"] = pd.NA
        df["symbols"] = [[] for _ in range(len(df))]
        df = df.rename(columns={"publishedAt": "timestamp"})
        return df

    def write(self, df: pd.DataFrame) -> None:
        df = df.copy()
        df["date"] = df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.strftime("%Y-%m-%d")
        source_name = df.get("source_name", pd.Series(["unknown"] * len(df)))
        df["source_name"] = source_name.fillna("unknown")
        write_partitioned(
            df,
            root=self.settings.storage.raw_root / f"source={self.source}",
            partition_cols=["date", "source_name"],
        )
