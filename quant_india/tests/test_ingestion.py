import pandas as pd

from quant_india.data import KiteHistoricalIngestion, NewsAPIIngestion


def test_kite_ingestion_simulated():
    job = KiteHistoricalIngestion(session=None)
    df = job.run(
        symbols=["TCS"],
        start=pd.Timestamp("2024-01-01 09:15", tz="Asia/Kolkata").to_pydatetime(),
        end=pd.Timestamp("2024-01-01 09:45", tz="Asia/Kolkata").to_pydatetime(),
    )
    assert not df.empty
    assert {"timestamp", "open", "close", "volume", "symbol"}.issubset(df.columns)


def test_news_ingestion_simulated():
    job = NewsAPIIngestion(api_key="<<placeholder>>")
    df = job.run(
        symbols=["Reliance"],
        start=pd.Timestamp("2024-01-01").to_pydatetime(),
        end=pd.Timestamp("2024-01-02").to_pydatetime(),
    )
    assert not df.empty
    assert "timestamp" in df.columns
