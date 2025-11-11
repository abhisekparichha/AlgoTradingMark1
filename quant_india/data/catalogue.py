from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List

import pandas as pd


@dataclass
class DataField:
    name: str
    datatype: str
    description: str


@dataclass
class DataSource:
    name: str
    category: str
    cadence: str
    endpoint: str
    method: str
    notes: str = ""
    fields: List[DataField] = field(default_factory=list)

    def to_records(self) -> Iterable[dict]:
        for field_info in self.fields:
            yield {
                "source": self.name,
                "category": self.category,
                "cadence": self.cadence,
                "endpoint": self.endpoint,
                "method": self.method,
                "field_name": field_info.name,
                "field_datatype": field_info.datatype,
                "field_description": field_info.description,
                "notes": self.notes,
            }


def build_catalogue() -> list[DataSource]:
    return [
        DataSource(
            name="Zerodha Kite Connect",
            category="Market - Live",
            cadence="Real-time streaming + historical",
            endpoint="https://api.kite.trade",
            method="REST (historical) + WebSocket (live ticks)",
            notes="Includes LTP, OHLCV, market depth. Historical data subject to subscription tier.",
            fields=[
                DataField("timestamp", "datetime", "Event timestamp in IST (store also UTC)"),
                DataField("instrument_token", "int", "Kite instrument identifier"),
                DataField("symbol", "string", "Trading symbol"),
                DataField("interval", "string", "Bar interval (tick/1m/5m/etc)"),
                DataField("open", "float", "Open price"),
                DataField("high", "float", "High price"),
                DataField("low", "float", "Low price"),
                DataField("close", "float", "Close price"),
                DataField("volume", "float", "Volume traded"),
                DataField("oi", "float", "Open interest for derivatives"),
                DataField("bid_depth", "json", "Top 5 bid levels (price, quantity)"),
                DataField("ask_depth", "json", "Top 5 ask levels (price, quantity)"),
            ],
        ),
        DataSource(
            name="NSE Bhavcopy",
            category="Market - Daily EOD",
            cadence="Daily",
            endpoint="https://www.nseindia.com/api/",
            method="HTTP Download/CSV",
            notes="Official end-of-day prices and corporate actions reference.",
            fields=[
                DataField("date", "date", "Trading date"),
                DataField("symbol", "string", "NSE symbol"),
                DataField("series", "string", "EQ / BE / etc"),
                DataField("open", "float", "Open price"),
                DataField("high", "float", "High price"),
                DataField("low", "float", "Low price"),
                DataField("close", "float", "Close price"),
                DataField("last", "float", "Last traded price"),
                DataField("prevclose", "float", "Previous close"),
                DataField("tottrdqty", "float", "Total traded quantity"),
                DataField("tottrdval", "float", "Turnover"),
                DataField("timestamp", "datetime", "End of day timestamp"),
            ],
        ),
        DataSource(
            name="NSE Option Chain",
            category="Derivatives",
            cadence="Intraday (5m) + end of day",
            endpoint="https://www.nseindia.com/api/option-chain-indices",
            method="HTTP JSON",
            notes="Provides IV, OI, Greeks for options. Requires headers to mimic browser.",
            fields=[
                DataField("timestamp", "datetime", "Snapshot timestamp"),
                DataField("underlying", "string", "Underlying symbol"),
                DataField("strikePrice", "float", "Strike price"),
                DataField("expiryDate", "date", "Expiry date"),
                DataField("CE_IV", "float", "Call implied volatility"),
                DataField("PE_IV", "float", "Put implied volatility"),
                DataField("CE_OI", "float", "Call open interest"),
                DataField("PE_OI", "float", "Put open interest"),
                DataField("CE_Volume", "float", "Call volume"),
                DataField("PE_Volume", "float", "Put volume"),
            ],
        ),
        DataSource(
            name="TrueData Tick Feed",
            category="Market Microstructure",
            cadence="Real-time + historical tick",
            endpoint="tcp://stream.truedata.in",
            method="Vendor API",
            notes="Paid feed for tick/level2 data. Use for slippage modelling.",
            fields=[
                DataField("timestamp", "datetime", "Tick timestamp"),
                DataField("symbol", "string", "Contract symbol"),
                DataField("last_price", "float", "Last traded price"),
                DataField("last_qty", "float", "Last traded quantity"),
                DataField("bid_price", "float", "Best bid price"),
                DataField("bid_qty", "float", "Best bid quantity"),
                DataField("ask_price", "float", "Best ask price"),
                DataField("ask_qty", "float", "Best ask quantity"),
            ],
        ),
        DataSource(
            name="Screener.in Fundamentals",
            category="Fundamental",
            cadence="Quarterly/Annual",
            endpoint="https://api.screener.in/company/{symbol}/",
            method="HTTP (requires authentication, scraping alternative)",
            notes="Provides financial statements and ratios.",
            fields=[
                DataField("reported_at", "date", "Reporting period date"),
                DataField("revenue", "float", "Revenue"),
                DataField("ebitda", "float", "EBITDA"),
                DataField("net_profit", "float", "Net profit"),
                DataField("eps", "float", "Earnings per share"),
                DataField("pe", "float", "Price to earnings"),
            ],
        ),
        DataSource(
            name="NSDL FII/DII Flows",
            category="Flows",
            cadence="Daily",
            endpoint="https://www.fpi.nsdl.co.in/web/Reports/Latest.aspx",
            method="HTTP Download",
            notes="Foreign institutional flows for equity cash.",
            fields=[
                DataField("date", "date", "Report date"),
                DataField("fii_buy", "float", "FII gross purchases"),
                DataField("fii_sell", "float", "FII gross sales"),
                DataField("fii_net", "float", "FII net flow"),
                DataField("dii_buy", "float", "DII gross purchases"),
                DataField("dii_sell", "float", "DII gross sales"),
                DataField("dii_net", "float", "DII net flow"),
            ],
        ),
        DataSource(
            name="NewsAPI Aggregator",
            category="News & Sentiment",
            cadence="Real-time + historical",
            endpoint="https://newsapi.org/v2/everything",
            method="HTTP JSON",
            notes="Use for Economic Times, Moneycontrol, Reuters etc via aggregator; respect rate limits.",
            fields=[
                DataField("publishedAt", "datetime", "Publication timestamp"),
                DataField("source", "string", "Source name"),
                DataField("author", "string", "Author"),
                DataField("title", "string", "Headline"),
                DataField("description", "string", "Summary"),
                DataField("content", "string", "Article content"),
                DataField("url", "string", "Original URL"),
            ],
        ),
        DataSource(
            name="GDELT Global News",
            category="News & Sentiment",
            cadence="Every 15 minutes",
            endpoint="http://api.gdeltproject.org/api/v2/",
            method="HTTP CSV/JSON",
            notes="Events and tone metrics for systemic event tagging.",
            fields=[
                DataField("SQLDATE", "datetime", "Event timestamp"),
                DataField("Actor1Name", "string", "Primary actor"),
                DataField("Actor2Name", "string", "Secondary actor"),
                DataField("AvgTone", "float", "Sentiment score"),
                DataField("GoldsteinScale", "float", "Event impact proxy"),
            ],
        ),
        DataSource(
            name="Google Trends",
            category="Alternative Data",
            cadence="Hourly/Daily",
            endpoint="https://trends.google.com/trends/api/explore",
            method="HTTP JSON",
            notes="Retail interest indicators.",
            fields=[
                DataField("time", "datetime", "Timestamp of interest score"),
                DataField("value", "float", "Interest score 0-100"),
                DataField("ticker", "string", "Mapped ticker keyword"),
            ],
        ),
        DataSource(
            name="SEBI Enforcement Actions",
            category="Regulatory",
            cadence="Ad-hoc (hourly polling)",
            endpoint="https://www.sebi.gov.in/sebiweb/home/list/1/7/0/0/Orders",
            method="HTTP scrape",
            notes="Regulatory updates impacting risk regime.",
            fields=[
                DataField("timestamp", "datetime", "Notice timestamp"),
                DataField("title", "string", "Notice headline"),
                DataField("summary", "string", "Summary text"),
                DataField("url", "string", "Document URL"),
            ],
        ),
    ]


def export_catalogue(path: Path) -> None:
    sources = build_catalogue()
    records = [record for source in sources for record in source.to_records()]
    df = pd.DataFrame(records)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
